import ast,csv,json,tempfile,types,unittest
from pathlib import Path
from selected_variant_runtime import publish_selected, select_records, normalize_records, formula_values, ROUTES
ROOT=Path(__file__).resolve().parent

class SelectedRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.dir=Path(self.tmp.name)
    def records(self,ids):return [{'molecule_id':i,'smiles':';'.join(['CCO','CCN']+['CCO']*23)} for i in ids]
    def calc(self,s):return {'CCO':'C2H6O','CCN':'C2H7N'}[s]
    def publish(self,variant='top1',ids=None,evidence=None,**kwargs):
        ids=['a','b'] if ids is None else ids
        evidence={str(i):['C2H7N'] for i in ids} if evidence is None else evidence
        providers=dict(legacy_provider=lambda:evidence,adduct_provider=lambda:evidence,
                       dedup_provider=lambda r:r,calc_formula=self.calc)
        providers.update(kwargs)
        return publish_selected(self.dir,variant,self.records(ids),ids,smiles_validator=lambda s:s in {'CCO','CCN'},**providers)
    def assert_no_final(self):
        self.assertFalse((self.dir/'submission.csv').exists());self.assertFalse((self.dir/'publication.json').exists())
    def test_97_percent_evidence_publishes_and_reports_missing(self):
        ids=[f'm{i}' for i in range(100)];e={i:(['C2H7N'] if j<97 else []) for j,i in enumerate(ids)}
        p=self.publish(ids=ids,evidence=e)
        self.assertEqual(p['formula_coverage'],.97);self.assertEqual(p['no_formula_count'],3)
        with (self.dir/'submission.csv').open() as stream:
            rows=list(csv.DictReader(stream))
        self.assertTrue(rows[0]['smiles'].startswith('CCN;'));self.assertEqual(rows[-1]['smiles'],self.records([ids[-1]])[0]['smiles'])
    def test_no_evidence_preserves_rows_but_records_zero(self):
        p=self.publish(evidence={'a':[],'b':[]});self.assertEqual(p['formula_coverage'],0);self.assertEqual(p['selected_vs_base_changed_rows'],0)
    def test_dataset_sizes_are_dynamic(self):
        for size in [1,7,401,803]:
            with self.subTest(size=size):self.assertEqual(self.publish(ids=[f'new_{i}' for i in range(size)])['rows'],size)
    def test_unsorted_ids_and_numeric_ids_normalize_and_reorder(self):
        rows,ids=normalize_records(self.records([7,'001','x']),['x','001','7'])
        self.assertEqual([r['molecule_id'] for r in rows],['x','001','7'])
    def test_missing_prediction_id_rejected(self):
        with self.assertRaisesRegex(ValueError,'PREDICTION_IDS'):normalize_records(self.records(['a']),['a','b'])
    def test_duplicate_id_rejected(self):
        with self.assertRaisesRegex(ValueError,'DUPLICATE'):normalize_records(self.records([1,'1']),['1'])
    def test_duplicate_sample_rejected(self):
        with self.assertRaisesRegex(ValueError,'SAMPLE_IDS'):normalize_records(self.records(['a']),['a','a'])
    def test_empty_sample_rejected(self):
        with self.assertRaisesRegex(ValueError,'SAMPLE_IDS'):normalize_records([],[])
    def test_all_routes_call_only_required_providers(self):
        for variant,(kind,topk,dedup) in ROUTES.items():
            seen=[]
            def legacy():seen.append('legacy');return {'a':['C2H7N'],'b':[]}
            def grouped():seen.append('adduct');return {'a':['C2H7N'],'b':[]}
            def refill(rows):seen.append('dedup');return rows
            self.publish(variant,legacy_provider=legacy,adduct_provider=grouped,dedup_provider=refill)
            self.assertEqual(seen,(['dedup'] if dedup else [])+[kind])
    def test_broken_unused_branches_do_not_run(self):
        def broken(*args):raise RuntimeError('UNUSED_BRANCH_MUST_NOT_RUN')
        self.publish('top1',adduct_provider=broken,dedup_provider=broken)
        self.publish('adduct',legacy_provider=broken,dedup_provider=broken)
    def test_needed_provider_error_remains_fatal_and_clears_stale_csv(self):
        (self.dir/'submission.csv').write_text('stale')
        def broken():raise RuntimeError('MODEL_LIBRARY_FAILURE')
        with self.assertRaisesRegex(RuntimeError,'MODEL_LIBRARY_FAILURE'):self.publish(legacy_provider=broken)
        self.assert_no_final();f=json.loads((self.dir/'selected_failure.json').read_text())
        self.assertEqual(f['stage'],'formula_legacy');self.assertIn('MODEL_LIBRARY_FAILURE',f['traceback'])
    def test_required_dedup_error_remains_fatal(self):
        def broken(rows):raise RuntimeError('DEDUP_FAILURE')
        with self.assertRaisesRegex(RuntimeError,'DEDUP_FAILURE'):self.publish('top1_dedup',dedup_provider=broken)
        self.assert_no_final()
    def test_malformed_formula_contract_does_not_become_missing_evidence(self):
        for evidence in [{'a':[]},{'a':[],'b':[],'c':[]},{'a':'C2H6O','b':[]},{'a':[123],'b':[]}]:
            with self.subTest(evidence=evidence):
                with self.assertRaises(ValueError):self.publish(evidence=evidence)
                self.assert_no_final()
    def test_missing_formula_sentinels(self):
        self.assertEqual(formula_values([None,float('nan'),'nan','None','','C2 H6 O+']),['C2H6O'])
    def test_invalid_final_candidate_is_fatal(self):
        with self.assertRaisesRegex(ValueError,'INVALID_SMILES'):
            publish_selected(self.dir,'top1',[{'molecule_id':'a','smiles':';'.join(['BAD']*25)}],['a'],
                smiles_validator=lambda s:False,legacy_provider=lambda:{'a':[]},calc_formula=self.calc)
        self.assert_no_final()
    def test_invalid_final_candidate_count_is_fatal(self):
        with self.assertRaisesRegex(ValueError,'CANDIDATE_COUNT'):
            publish_selected(self.dir,'top1',[{'molecule_id':'a','smiles':'CCO'}],['a'],
                smiles_validator=lambda s:True,legacy_provider=lambda:{'a':[]},calc_formula=self.calc)
        self.assert_no_final()
    def test_publication_fault_is_fatal_and_cleans(self):
        def fault(stage):
            if stage=='after_staging':raise OSError('disk fixture')
        with self.assertRaises(OSError):self.publish(publication_fault=fault)
        self.assert_no_final()
    def test_success_clears_failure_record_from_previous_run(self):
        def broken():raise RuntimeError('prior fixture failure')
        with self.assertRaises(RuntimeError):self.publish(legacy_provider=broken)
        self.assertTrue((self.dir/'selected_failure.json').exists())
        self.publish()
        self.assertFalse((self.dir/'selected_failure.json').exists())
    def test_unknown_variant_is_fatal(self):
        with self.assertRaisesRegex(ValueError,'UNKNOWN_VARIANT'):self.publish('unknown')
        self.assert_no_final()

class CachedGoldenTests(unittest.TestCase):
    def test_five_cached_public_predictions_unchanged(self):
        from rdkit import Chem
        from rdkit.Chem.rdMolDescriptors import CalcMolFormula
        def read(p):
            with p.open() as f:return list(csv.DictReader(f))
        base=read(ROOT/'probeout_w088/submission.csv');dedup=read(ROOT/'probeout_wave7_cpu/submission_dedup.csv')
        ids=[r['molecule_id'] for r in base]
        legacy=json.loads((ROOT/'regression_formula_assets/buddy_formulas.json').read_text())
        grouped=json.loads((ROOT/'probeout_wave8_extra/adduct/formula_adducts.json').read_text())
        cache={}
        def calc(s):
            if s not in cache:
                m=Chem.MolFromSmiles(s);cache[s]=CalcMolFormula(m).rstrip('+-') if m is not None else None
            return cache[s]
        results={}
        for variant in ROUTES:
            selected,report=select_records(variant,base,ids,legacy_provider=lambda:legacy,
                adduct_provider=lambda:grouped,dedup_provider=lambda rows:dedup,calc_formula=calc)
            p=ROOT/'probeout_wave8_atomic/submission.csv' if variant=='formula_dedup' else ROOT/'probeout_wave8_extra'/variant/'submission.csv'
            expected=read(p)
            self.assertEqual(selected,expected,variant)
            results[variant]={'rows':len(selected),'same_ordered_records_as_wave8_preview':True,'changed_rows':report['selected_vs_base_changed_rows']}
        out=ROOT/'casmi_repair_drafts';out.mkdir(exist_ok=True)
        (out/'cached_equivalence.json').write_text(json.dumps({'scope':'Postprocessing only. Cached base/dedup/formulas, not a full model rerun.','variants':results},indent=2))

class DraftIntegrationTests(unittest.TestCase):
    def test_generated_final_cells_use_only_selected_route(self):
        for variant,(kind,_,needs_dedup) in ROUTES.items():
            nb=json.loads((ROOT/'casmi_repair_drafts'/variant/'repair.ipynb').read_text())
            with tempfile.TemporaryDirectory() as td:
                directory=Path(td);(directory/'test.parquet').write_bytes(b'fixture');(directory/'sample_submission.csv').write_text('fixture')
                seen=[]
                rows=[{'molecule_id':'new-001','smiles':';'.join(['CCO']*25)}]
                class Frame:
                    def to_dict(self,orientation):return rows
                def legacy():seen.append('legacy');return {'new-001':[]}
                def grouped():seen.append('adduct');return {'new-001':[]}
                def dedup(records):seen.append('dedup');return records
                def publish_redirect(unused_path,*args,**kwargs):return publish_selected(directory,*args,**kwargs)
                ns=dict(hashlib=__import__('hashlib'),json=json,os=__import__('os'),COMP=str(directory),VARIANT=variant,
                    rdkit=types.SimpleNamespace(__version__='fixture'),publish_selected=publish_redirect,subs={'blend':Frame()},
                    sample_ids=['new-001'],legacy_formulas=legacy,grouped_formulas=grouped,selected_dedup=dedup,
                    _calc_f=lambda s:'C2H6O',Chem=types.SimpleNamespace(MolFromSmiles=lambda s:True))
                import contextlib,io
                with contextlib.redirect_stdout(io.StringIO()):exec(compile(''.join(nb['cells'][-1]['source']),'generated_final_cell','exec'),ns)
                self.assertEqual(seen,(['dedup'] if needs_dedup else [])+[kind])
                self.assertTrue((directory/'submission.csv').exists())
    def test_generated_core_only_builds_blend_csv(self):
        for variant in ROUTES:
            nb=json.loads((ROOT/'casmi_repair_drafts'/variant/'repair.ipynb').read_text())
            source=next(''.join(c['source']).split('\n',1)[1] for c in nb['cells'] if ''.join(c.get('source',[])).startswith('%%writefile casmi_engine.py'))
            tree=ast.parse(source);main=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
            call=next(n for n in ast.walk(main) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='make_submissions')
            self.assertEqual([k.value for k in call.args[2].keys],['blend'])

if __name__=='__main__':unittest.main(verbosity=2)

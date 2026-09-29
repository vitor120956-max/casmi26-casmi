"""Build LOCAL-ONLY CASMI repair drafts. No Kaggle API, push, inference or submission."""
from pathlib import Path
import ast,copy,hashlib,json
from safety_guards import validate_kernel,validate_publication_safety
ROOT=Path(__file__).resolve().parent
BASE=ROOT/'kpush_wave8_atomic_combo_cpu'

def cell(text):
    return {'cell_type':'code','metadata':{},'execution_count':None,'outputs':[],'source':text.splitlines(keepends=True)}

def build():
    original=json.loads((BASE/'wave8.ipynb').read_text())
    metadata=json.loads((BASE/'kernel-metadata.json').read_text())
    formula=''.join(original['cells'][18]['source'])
    tree=ast.parse(formula)
    setup_try=next(n for n in tree.body if isinstance(n,ast.Try))
    setup_nodes=[]
    for n in setup_try.body:
        if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='_eng' for t in n.targets):break
        setup_nodes.append(n)
    setup_text='\n'.join(ast.unparse(n) for n in setup_nodes)
    setup='def setup_msbuddy():\n'+''.join('    '+line+'\n' for line in setup_text.splitlines())+'    return Msbuddy, _cfg, MetaFeature, Spectrum\n'
    dedup=''.join(original['cells'][19]['source']);dedup_tree=ast.parse(dedup)
    helper_text='\n\n'.join(ast.unparse(n) for n in dedup_tree.body if isinstance(n,ast.FunctionDef))
    dedup_body=dedup[dedup.index('rec_by_mid ='):]
    dedup_body=dedup_body.replace("{r['mid']:r for r in recs}","{str(r['mid']):r for r in recs}")
    dedup_body=dedup_body.replace("dedup_sub = subs['blend'].copy()","dedup_sub = pd.DataFrame(records)")
    dedup_body=dedup_body.replace("rec = rec_by_mid[row.molecule_id]","rec = rec_by_mid[str(row.molecule_id)]")
    dedup_callback='def selected_dedup(records):\n'+''.join('    '+line+'\n' for line in dedup_body.splitlines())+"    return dedup_sub.to_dict('records')\n"
    common='''from pathlib import Path
from functools import lru_cache
from rdkit import Chem, RDLogger
from rdkit.Chem.rdMolDescriptors import CalcMolFormula
from selected_variant_runtime import formula_values, publish_selected
from formula_evidence import split_spectra, combine_formula_evidence
import hashlib,json
RDLogger.DisableLog('rdApp.*')
@lru_cache(maxsize=None)
def _calc_f(smi):
    mol=Chem.MolFromSmiles(smi)
    return CalcMolFormula(mol).rstrip('+-') if mol is not None else None
te=E.pq.read_table(os.path.join(COMP,'test.parquet')).to_pandas()
if te['molecule_id'].isna().any():raise ValueError('NULL_TEST_MOLECULE_ID')
te['molecule_id']=te['molecule_id'].astype(str)
sample_ids=pd.read_csv(os.path.join(COMP,'sample_submission.csv'),dtype={'molecule_id':str}).molecule_id.tolist()
mols=list(te.groupby('molecule_id'))
_MPath=Path
'''
    providers='''
def legacy_formulas():
    Msbuddy,cfg,MetaFeature,Spectrum=setup_msbuddy()
    feats=[];ids=[]
    for i,(mid,sub) in enumerate(mols):
        mz=np.concatenate([np.asarray(r.ms2_mzs,float) for r in sub.itertuples()])
        ints=np.concatenate([np.asarray(r.ms2_normalized_intensities,float) for r in sub.itertuples()])
        order=np.argsort(mz);adduct=str(sub.adduct.iloc[0])
        feats.append(MetaFeature(identifier=i,mz=float(np.median(sub.precursor_mz)),
                    charge=1 if adduct.endswith('+') else -1,adduct=adduct,
                    ms2=Spectrum(mz_array=mz[order],int_array=ints[order])))
        ids.append(str(mid))
    eng=Msbuddy(cfg);eng.add_data(feats);eng.annotate_formula();summary=eng.get_summary()
    if len(summary)!=len(ids):raise ValueError('FORMULA_SUMMARY_COUNT_MISMATCH')
    return {mid:formula_values([res.get(f'formula_rank_{k}') for k in range(1,6)]) for mid,res in zip(ids,summary)}

def grouped_formulas():
    Msbuddy,cfg,MetaFeature,Spectrum=setup_msbuddy()
    groups=split_spectra(te.to_dict('records'));features=[]
    for i,g in enumerate(groups):
        features.append(MetaFeature(identifier=i,mz=g['precursor_mz'],charge=g['charge'],adduct=g['adduct'],
            ms2=Spectrum(mz_array=np.asarray(g['ms2_mzs'],float),int_array=np.asarray(g['ms2_normalized_intensities'],float))))
    eng=Msbuddy(cfg);eng.add_data(features);eng.annotate_formula();summary=eng.get_summary()
    if len(summary)!=len(groups):raise ValueError('ADDUCT_SUMMARY_COUNT')
    evidence=[]
    for g,res in zip(groups,summary):
        evidence.append(dict(molecule_id=g['molecule_id'],adduct=g['adduct'],mode=g['mode'],
            formulas=formula_values([res.get(f'formula_rank_{k}') for k in range(1,6)])))
    return combine_formula_evidence(evidence)
'''
    final='''def file_sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
    return h.hexdigest()
proof={'cpu_only':True,'full_pipeline':True,'own_dataset_inputs':False,
       'test_sha256':file_sha(os.path.join(COMP,'test.parquet')),
       'sample_sha256':file_sha(os.path.join(COMP,'sample_submission.csv')),
       'rdkit_version':rdkit.__version__}
publication=publish_selected('/kaggle/working',VARIANT,subs['blend'].to_dict('records'),sample_ids,
    smiles_validator=lambda s:Chem.MolFromSmiles(s) is not None,
    legacy_provider=legacy_formulas,adduct_provider=grouped_formulas,
    dedup_provider=selected_dedup,calc_formula=_calc_f,extra_proof=proof)
print('SELECTED_PUBLICATION_COMPLETE',json.dumps(publication),flush=True)
'''
    plans=[]
    for variant in ['formula_dedup','top1','top1_dedup','adduct','adduct_dedup']:
        nb=copy.deepcopy(original);nb['cells']=copy.deepcopy(original['cells'][:18])
        nb['cells'][0]['source']=[f'# LOCAL REPAIR DRAFT — {variant}\n','Not uploaded. Full CPU preview and publication review still required.\n','Repairs E031; does not establish hidden root cause E029.\n']
        for c in nb['cells']:
            if c['cell_type']!='code':continue
            c['execution_count']=None;c['outputs']=[]
            s=''.join(c['source']).replace("VARIANT='formula_dedup'",f'VARIANT={variant!r}')
            if s.startswith('%%writefile casmi_engine.py'):
                old='{"blend": blend_scores(s_pv, s_ours, w_pv), "pv": s_pv, "ours": s_ours}'
                assert s.count(old)==1
                s=s.replace(old,'{"blend": blend_scores(s_pv, s_ours, w_pv)}')
                assert s.count('samp = pd.read_csv(sample_path)')==1
                s=s.replace('samp = pd.read_csv(sample_path)',"samp = pd.read_csv(sample_path, dtype={'molecule_id':str})")
                line='te = pq.read_table(test_path).to_pandas()'
                assert s.count(line)==1
                s=s.replace(line,line+"\n    if te['molecule_id'].isna().any(): raise ValueError('NULL_TEST_MOLECULE_ID')\n    te['molecule_id']=te['molecule_id'].astype(str)")
            c['source']=s.splitlines(keepends=True)
        # Instrument the core without swallowing failures or publishing fallback output.
        for c in nb['cells']:
            s=''.join(c.get('source',[]))
            if c.get('cell_type')=='code' and 'import casmi_engine as E' in s:
                c['source']=("import json,traceback\nfrom pathlib import Path\nPath('core_stage.json').write_text(json.dumps({'stage':'core_inference'}))\ntry:\n"+''.join('    '+l+'\n' for l in s.splitlines())+"except BaseException as e:\n    publisher.begin()\n    Path('core_failure.json').write_text(json.dumps({'stage':'core_inference','type':type(e).__name__,'message':str(e),'traceback':traceback.format_exc()},indent=2))\n    raise\nPath('core_stage.json').write_text(json.dumps({'stage':'core_complete'}))\n").splitlines(keepends=True)
        nb['cells'] += [cell('%%writefile selected_variant_runtime.py\n'+(ROOT/'selected_variant_runtime.py').read_text()),
                         cell('%%writefile formula_evidence.py\n'+(ROOT/'formula_evidence.py').read_text()),
                         cell(common),cell(setup+'\n'+providers),cell(helper_text+'\n\n'+dedup_callback),cell(final)]
        meta=copy.deepcopy(metadata);slug='casmi26-repair-v1-'+variant.replace('_','-')+'-cpu'
        meta.update(id='victor120956/'+slug,title=slug.replace('-',' '),code_file='repair.ipynb',enable_gpu=False,enable_tpu=False)
        validate_kernel(meta,nb);validate_publication_safety(nb)
        text='\n'.join(''.join(c.get('source',[])) for c in nb['cells'])
        assert 'coverage < 0.975' not in text and 'adduct_coverage<0.975' not in text
        assert 'for name,sub in variants.items()' not in text
        dest=ROOT/'casmi_repair_drafts'/variant;dest.mkdir(parents=True,exist_ok=True)
        raw=json.dumps(nb,ensure_ascii=False,indent=1).encode();(dest/'repair.ipynb').write_bytes(raw)
        (dest/'kernel-metadata.json').write_text(json.dumps(meta,indent=2))
        plans.append({'variant':variant,'source_sha256':hashlib.sha256(raw).hexdigest(),'folder':str(dest),
                      'static_check':'PASS','full_cpu_preview':False,'remote_version':None,'submission_allowed':False})
    (ROOT/'casmi_repair_drafts/manifest.json').write_text(json.dumps({'status':'LOCAL_ONLY_NOT_READY_FOR_SUBMISSION','drafts':plans},indent=2))
    print('Built',len(plans),'LOCAL drafts. Static checks PASS; no remote execution or submission.')

if __name__=='__main__':build()

import copy,csv,hashlib,io,json,unittest
from batch_release_checks import check_artifact,semantic_hash,release_gate

class BatchCheckTests(unittest.TestCase):
    def setUp(self):
        self.ids=['a','b'];self.rows=[{'molecule_id':x,'smiles':';'.join(['CCO']*25)} for x in self.ids]
        s=io.StringIO();w=csv.DictWriter(s,fieldnames=['molecule_id','smiles'],lineterminator='\n');w.writeheader();w.writerows(self.rows);self.raw=s.getvalue().encode()
        self.proof={'publication_contract':'atomic-final-only-v1','variant':'top1','cpu_only':True,'full_pipeline':True,'own_dataset_inputs':False,
                    'sha256':hashlib.sha256(self.raw).hexdigest(),'bytes':len(self.raw),'rows':2,'expected_rows':2,'degraded':[],'msbuddy_available':True,
                    'formula_coverage':1.,'selected_vs_blend_changed_rows':1}
    def check(self,proof=None,history=()):return check_artifact(self.raw,self.proof if proof is None else proof,'top1',self.ids,lambda s:s=='CCO',history)
    def test_valid_artifact_is_not_automatic_release(self):
        self.assertTrue(self.check()['artifact_verified'])
        self.assertFalse(release_gate(artifact_verified=True,version_confirmed=True,source_reviewed=False,canary_reviewed=False,is_canary=True,send_authorized=True))
    def test_corrupt_hash_blocked(self):
        self.proof['sha256']='0'*64;self.assertIn('FILE_HASH_OR_SIZE',self.check()['blockers'])
    def test_wrong_variant_blocked(self):
        self.proof['variant']='adduct';self.assertIn('VARIANT_MISMATCH',self.check()['blockers'])
    def test_dependency_failure_blocked(self):
        self.proof['degraded']=[['MSBUDDY_UNAVAILABLE','fixture']];self.assertIn('DEGRADED_RUNTIME_OR_MECHANISM',self.check()['blockers'])
    def test_97_percent_not_rejected_by_old_cutoff(self):
        self.proof['formula_coverage']=.97;self.proof['degraded']=[['FORMULA_ROWS_WITHOUT_EVIDENCE',1]];self.assertTrue(self.check()['artifact_verified'])
    def test_zero_coverage_is_not_useful_public_experiment(self):
        self.proof['formula_coverage']=0.;self.assertIn('NO_VALID_FORMULA_EVIDENCE',self.check()['blockers'])
    def test_missing_health_manifest_blocked(self):
        del self.proof['degraded'];self.assertIn('DEGRADATION_STATUS_UNKNOWN',self.check()['blockers'])
    def test_no_effect_is_blocked(self):
        self.proof['selected_vs_blend_changed_rows']=0;self.assertIn('NO_EFFECT_ON_PUBLIC_PREVIEW',self.check()['blockers'])
    def test_historical_duplicate_blocked(self):
        self.assertIn('DUPLICATE_HISTORICAL_PREDICTIONS',self.check(history={semantic_hash(self.rows)})['blockers'])
    def test_wrong_row_count_blocked(self):
        self.proof['rows']=7;self.assertIn('CSV_ROW_COUNT',self.check()['blockers'])
    def test_wrong_ids_blocked(self):
        self.ids=['b','a'];self.assertIn('CSV_IDS_OR_ORDER',self.check()['blockers'])
    def test_invalid_structure_blocked(self):
        d=check_artifact(self.raw,self.proof,'top1',self.ids,lambda s:False)
        self.assertIn('INVALID_SMILES',d['blockers'])
    def test_all_authorization_gates_required(self):
        args=dict(artifact_verified=True,version_confirmed=True,source_reviewed=True,canary_reviewed=True,is_canary=False,send_authorized=True)
        self.assertTrue(release_gate(**args))
        for key in ['artifact_verified','version_confirmed','source_reviewed','canary_reviewed','send_authorized']:
            with self.subTest(key=key):self.assertFalse(release_gate(**dict(args,**{key:False})))
    def test_canary_does_not_need_prior_canary_but_requires_authorization(self):
        args=dict(artifact_verified=True,version_confirmed=True,source_reviewed=True,canary_reviewed=False,is_canary=True,send_authorized=True)
        self.assertTrue(release_gate(**args));args['send_authorized']=False;self.assertFalse(release_gate(**args))

if __name__=='__main__':unittest.main()

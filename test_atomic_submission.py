import csv,hashlib,json,pathlib,tempfile,unittest
from unittest import mock
from atomic_submission import AtomicSubmission

class AtomicPublisherTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.p=AtomicSubmission(self.tmp.name)
    def data(self,n=2):
        return [{'molecule_id':f'id_{i}','smiles':';'.join(['CCO']*25)} for i in range(n)]
    def ids(self,n=2):return [f'id_{i}' for i in range(n)]
    def pub(self,rows=None,ids=None,fault=None,proof=None):
        return self.p.publish(self.data() if rows is None else rows,self.ids() if ids is None else ids,
                              lambda s:s=='CCO',{'variant':'test'} if proof is None else proof,fault)
    def absent(self):
        for x in [self.p.final,self.p.staging,self.p.manifest]:self.assertFalse(x.exists(),str(x))
    def test_success_and_hash(self):
        r=self.pub();self.assertEqual(r['rows'],2)
        self.assertEqual(hashlib.sha256(self.p.final.read_bytes()).hexdigest(),r['sha256'])
        self.assertEqual(json.loads(self.p.manifest.read_text()),r);self.assertFalse(self.p.staging.exists())
    def test_dynamic_row_counts_no_fixed_400(self):
        for n in [1,3,401]:
            with self.subTest(n=n):self.assertEqual(self.pub(self.data(n),self.ids(n))['rows'],n)
    def test_each_injected_failure_leaves_no_final(self):
        for stage in ['before_validation','after_validation','after_staging','after_manifest','before_publish']:
            with self.subTest(stage=stage):
                def fail(s):
                    if s==stage:raise RuntimeError('INJECTED')
                with self.assertRaises(RuntimeError):self.pub(fault=fail)
                self.absent()
    def test_final_absent_at_all_prepublication_checkpoints(self):
        visits=[]
        def inspect(stage):visits.append(stage);self.assertFalse(self.p.final.exists())
        self.pub(fault=inspect);self.assertEqual(len(visits),5);self.assertTrue(self.p.final.exists())
    def test_stale_final_removed_when_compute_aborts(self):
        self.pub();self.p.begin();self.absent()
    def test_stale_final_removed_on_bad_input(self):
        self.pub()
        with self.assertRaises(ValueError):self.pub(self.data(1))
        self.absent()
    def test_wrong_row_count(self):
        with self.assertRaisesRegex(ValueError,'LENGTH'):self.pub(self.data(1))
        self.absent()
    def test_wrong_order(self):
        with self.assertRaises(ValueError):self.pub(list(reversed(self.data())))
        self.absent()
    def test_duplicate_sample_id(self):
        with self.assertRaisesRegex(ValueError,'SAMPLE_IDS'):self.pub(ids=['id_0','id_0'])
        self.absent()
    def test_invalid_smiles(self):
        d=self.data();d[0]['smiles']=';'.join(['INVALID']*25)
        with self.assertRaisesRegex(ValueError,'INVALID_SMILES'):self.pub(d)
        self.absent()
    def test_candidate_count(self):
        d=self.data();d[0]['smiles']='CCO'
        with self.assertRaisesRegex(ValueError,'CANDIDATE_COUNT'):self.pub(d)
        self.absent()
    def test_manifest_serialization_failure(self):
        with self.assertRaises(TypeError):self.pub(proof={'bad':object()})
        self.absent()
    def test_atomic_rename_failure(self):
        with mock.patch('atomic_submission.os.replace',side_effect=OSError('INJECTED')):
            with self.assertRaises(OSError):self.pub()
        self.absent()
    def test_exactly_one_atomic_publish(self):
        import os
        original=os.replace
        with mock.patch('atomic_submission.os.replace',wraps=original) as replace:
            self.pub();self.assertEqual(replace.call_count,1)
    def test_no_fallback_to_other_variant(self):
        self.p.final.write_text('old baseline')
        with self.assertRaises(ValueError):self.pub(rows=[])
        self.absent()

if __name__=='__main__':unittest.main(verbosity=2)

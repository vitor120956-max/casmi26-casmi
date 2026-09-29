import copy,json,pathlib,tempfile,unittest
from safety_guards import *
ROOT=pathlib.Path(__file__).resolve().parent
class GuardsTest(unittest.TestCase):
 def setUp(self):
  self.plan={'file':'submission.csv','kernel':'victor120956/casmi26-wave7-w088-pv-submit-cpu','version':1,'sha256':'a'*64}
  self.meta={'enable_gpu':False,'enable_tpu':False,'competition_sources':[COMP],'dataset_sources':list(ALLOWED_ASSETS),'kernel_sources':[]}
  self.nb={'metadata':{'kernelspec':{'name':'python3','language':'python'}},'cells':[{'cell_type':'code','source':['x = 1\n']}]}
 def test_literal_filename_accepts(self):validate_submission_plan(self.plan)
 def test_rejects_alternate_filenames(self):
  for name in ['submission_ours.csv','submission_pv.csv','submission_formula.csv','submission_dedup.csv','dir/submission.csv','']:
   with self.subTest(name=name),self.assertRaisesRegex(ValueError,'E001'):validate_submission_plan(dict(self.plan,file=name))
 def test_rejects_unknown_hash(self):
  with self.assertRaises(ValueError):validate_submission_plan(dict(self.plan,sha256=''))
 def test_rejects_wrong_owner(self):
  with self.assertRaises(ValueError):validate_submission_plan(dict(self.plan,kernel='other/test'))
 def test_rejects_unpinned_version(self):
  for v in [None,0,'1',True]:
   with self.subTest(v=v),self.assertRaises(ValueError):validate_submission_plan(dict(self.plan,version=v))
 def test_cpu_contract(self):validate_kernel(self.meta,self.nb)
 def test_blocks_gpu(self):
  with self.assertRaisesRegex(ValueError,'CPU_ONLY'):validate_kernel(dict(self.meta,enable_gpu=True),self.nb)
 def test_blocks_tpu(self):
  with self.assertRaises(ValueError):validate_kernel(dict(self.meta,enable_tpu=True),self.nb)
 def test_blocks_missing_kernelspec(self):
  with self.assertRaisesRegex(ValueError,'KERNELSPEC'):validate_kernel(self.meta,{'metadata':{},'cells':[]})
 def test_blocks_competition_typo(self):
  with self.assertRaises(ValueError):validate_kernel(dict(self.meta,competition_sources=['envida-CASMI26']),self.nb)
 def test_blocks_own_dataset(self):
  with self.assertRaises(ValueError):validate_kernel(dict(self.meta,dataset_sources=['victor120956/oursubs']),self.nb)
 def test_blocks_tier2_asset(self):
  with self.assertRaises(ValueError):validate_kernel(dict(self.meta,dataset_sources=['ngdminh31/casmi26-pubchem-tier2-fp-public']),self.nb)
 def test_blocks_upstream_outputs(self):
  with self.assertRaises(ValueError):validate_kernel(dict(self.meta,kernel_sources=['victor120956/old']),self.nb)
 def test_blocks_tier2_code(self):
  n=copy.deepcopy(self.nb);n['cells'][0]['source']=['tier2_mass = []']
  with self.assertRaises(ValueError):validate_kernel(self.meta,n)
 def test_detects_syntax_error(self):
  n=copy.deepcopy(self.nb);n['cells'][0]['source']=['if broken']
  with self.assertRaises(SyntaxError):validate_kernel(self.meta,n)
 def test_official_oauth_id(self):validate_oauth(GITHUB_CLI_CLIENT_ID,{'public_repo'})
 def test_wrong_oauth_id_blocked(self):
  with self.assertRaisesRegex(ValueError,'WRONG_OAUTH'):validate_oauth('unverified-app')
 def test_missing_scope_blocked(self):
  for scopes in [set(),{'read:org'},{'gist'}]:
   with self.subTest(scopes=scopes),self.assertRaises(ValueError):validate_oauth(GITHUB_CLI_CLIENT_ID,scopes)
 def test_complete_without_score_not_ranked(self):self.assertEqual(classify_submission({'status':'COMPLETE','publicScore':None}),'AGUARDANDO_NOTA')
 def test_zero_score_is_ranked(self):self.assertEqual(classify_submission({'status':'COMPLETE','publicScore':'0.000'}),'RANQUEADA')
 def test_error_overrides_complete(self):self.assertEqual(classify_submission({'status':'COMPLETE','publicScore':'0.332','errorDescription':'bad format'}),'REJEITADA')
 def test_pending_not_ranked(self):self.assertEqual(classify_submission({'status':'PENDING','publicScore':'0.332'}),'AGUARDANDO_NOTA')
 def test_invalid_score_not_ranked(self):
  for x in ['nan','inf','bad','']:
   with self.subTest(x=x):self.assertEqual(classify_submission({'status':'COMPLETE','publicScore':x}),'AGUARDANDO_NOTA')
 def test_actual_four_plans(self):
  plans=json.loads((ROOT/'wave7_named_plan.json').read_text())
  self.assertEqual(len(plans),4)
  self.assertEqual(len({p['sha256'] for p in plans}),4)
  for p in plans:validate_submission_plan(p)
 def test_actual_four_notebooks(self):
  for tag in ['formula','dedup','ours','pv']:
   p=ROOT/f'kpush_wave7_submit_{tag}';m=json.loads((p/'kernel-metadata.json').read_text());n=json.loads((p/m['code_file']).read_text())
   validate_kernel(m,n)
 def test_incident_persisted(self):
  with tempfile.TemporaryDirectory() as td:
   p=pathlib.Path(td)/'incidents.jsonl';record_failure('E001','test',{'stage':'local'},str(p))
   row=json.loads(p.read_text());self.assertEqual(row['code'],'E001');self.assertEqual(row['state'],'OPEN_REQUIRES_DIAGNOSIS')
class AttributionTest(unittest.TestCase):
 def case(self):
  tags=['a','b','c']
  subs=[{'status':'COMPLETE','publicScore':'0.341','totalBytes':500,'description':'PROBE-WAVE7:'+t+' VERIFY PASS'} for t in tags]
  fp={t:{'sha256':t*64,'local_bytes':100+i} for i,t in enumerate(tags)}
  return subs,fp
 def test_identical_metadata_distinct_files_warns(self):
  s,p=self.case();self.assertIn('E018_IDENTICAL_SCORE_METADATA_FOR_DISTINCT_OUTPUTS',score_attribution_warnings(s,p))
 def test_distinct_scores_do_not_trigger_tie_alarm(self):
  s,p=self.case();s[1]['publicScore']='0.300';self.assertEqual(score_attribution_warnings(s,p),[])
 def test_same_sizes_do_not_prove_anomaly(self):
  s,p=self.case()
  for v in p.values():v['local_bytes']=500
  self.assertEqual(score_attribution_warnings(s,p),[])
 def test_missing_lineage_blocks_interpretation(self):
  s,p=self.case();p.pop('a');self.assertEqual(score_attribution_warnings(s,p),['SCORING_LINEAGE_UNVERIFIED'])
class PublicationTest(unittest.TestCase):
 def nb(self,code):return {'cells':[{'cell_type':'code','source':code.splitlines(keepends=True)}]}
 def test_rejects_multiple_final_writes(self):
  with self.assertRaisesRegex(ValueError,'E020'):
   validate_publication_safety(self.nb("base.to_csv('submission.csv')\nPath('submission.csv').write_bytes(other)"))
 def test_rejects_hash_assert_after_publication(self):
  with self.assertRaisesRegex(ValueError,'E020'):
   validate_publication_safety(self.nb("base.to_csv('submission.csv')\nassert ok, 'BASELINE_CHANGED'"))
 def test_rejects_preview_hash_in_production(self):
  with self.assertRaisesRegex(ValueError,'E021'):
   validate_publication_safety(self.nb("assert ok, 'W088_REPRODUCTION_FAILED'\nfinal.to_csv('submission.csv')"))
 def test_accepts_simple_single_final_publish(self):
  validate_publication_safety(self.nb("assert valid_rows\nfinal.to_csv('submission.csv')"))
 def test_all_four_submitted_variants_now_blocked_for_reuse(self):
  for tag in ['formula','dedup','ours','pv']:
   n=json.loads((ROOT/f'kpush_wave7_submit_{tag}'/'wave7.ipynb').read_text())
   with self.subTest(tag=tag),self.assertRaisesRegex(ValueError,'E020'):
    validate_publication_safety(n)
if __name__=='__main__':unittest.main(verbosity=2)



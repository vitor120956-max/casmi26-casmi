#!/usr/bin/env python3
"""One-shot, read-only verifier of four new Wave8 mechanisms; no polling/submit."""
import concurrent.futures,hashlib,json,pathlib
from kaggle.api.kaggle_api_extended import KaggleApi
from safety_guards import validate_kernel,validate_publication_safety,record_failure
import wave7_run as w
R=pathlib.Path('/home/user');plans=json.loads((R/'wave8_extra_plan.json').read_text())
history=json.loads((R/'historical_hashes.json').read_text())
for tag,e in json.loads((R/'wave7_submit_state.json').read_text()).items():
 if e.get('phase')=='accepted':history[e['plan']['semantic_sha256']]=['Wave7 '+tag]
combo=json.loads((R/'wave8_ready.json').read_text());history[combo['semantic_sha256']]=['Wave8 formula_dedup']
profile=json.loads((R/'wave8_mechanism_profile.json').read_text())
references={
 'blend':R/'probeout_w088/submission.csv','ours':R/'probeout_w088/submission_ours.csv','pv':R/'probeout_w088/submission_pv.csv',
 'formula':R/'probeout_wave7_cpu/submission_formula.csv','dedup':R/'probeout_wave7_cpu/submission_dedup.csv',
 'formula_dedup':R/'wave8_local_expectations/formula_dedup.csv','top1':R/'wave8_local_expectations/top1.csv',
 'top1_dedup':R/'wave8_local_expectations/top1_dedup.csv'}
def verify(p):
 a=KaggleApi();a.authenticate();s=json.loads(str(a.kernels_status(p['kernel'])));w.log('WAVE8_EXTRA_CHECK_ONCE '+p['tag']+' '+json.dumps(s))
 if s.get('status')!='COMPLETE':return None
 d=R/'probeout_wave8_extra'/p['tag']
 a.kernels_output(p['kernel'],str(d),file_pattern=r'^(submission\.csv|audit_.*\.csv|publication\.json|formula_adducts\.json)$',force=True,quiet=True)
 mdir=R/'remote_wave8_extra_final'/p['tag'];a.kernels_pull(p['kernel'],str(mdir),metadata=True,quiet=True)
 m=json.loads((mdir/'kernel-metadata.json').read_text());n=json.loads((mdir/m['code_file']).read_text());local=json.loads((pathlib.Path(p['folder'])/'wave8.ipynb').read_text())
 validate_kernel(m,n);validate_publication_safety(n)
 assert m['id']==p['kernel'] and [''.join(c['source']) for c in n['cells']]==[''.join(c['source']) for c in local['cells']]
 proof=json.loads((d/'publication.json').read_text());raw=(d/'submission.csv').read_bytes()
 assert proof['variant']==p['tag'] and proof['publication_contract']=='atomic-final-only-v1'
 assert proof['cpu_only'] and proof['full_pipeline'] and not proof['own_dataset_inputs']
 assert proof['sha256']==hashlib.sha256(raw).hexdigest() and proof['bytes']==len(raw)
 assert raw==(d/f"audit_{p['tag']}.csv").read_bytes()
 assert proof['test_sha256']==hashlib.sha256((R/'harness_data/test.parquet').read_bytes()).hexdigest()
 for name,reference in references.items():
  data=(d/f'audit_{name}.csv').read_bytes()
  assert data==reference.read_bytes(),('CONTROL_REGRESSION',p['tag'],name)
  assert hashlib.sha256(data).hexdigest()==proof['artifacts'][name]['sha256']
 if p['tag'].startswith('adduct'):
  assert proof['adduct_group_count']==profile['adduct_groups'] and proof['adduct_formula_coverage']>=0.975
 else:assert proof['sha256']==profile['top1_expected'][p['tag']]['sha256']
 sig,_=w.verify(d/'submission.csv',proof['sha256'],history)
 for artifact in d.glob('audit_*.csv'):artifact.unlink()  # identical controls remain in golden fixtures
 return dict(p,path=str(d/'submission.csv'),sha256=proof['sha256'],semantic_sha256=sig,preview_verified=True,controls_regression_pass=True)
ready=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
 tasks=[pool.submit(verify,p) for p in plans]
 for p,task in zip(plans,tasks):
  try:
   result=task.result()
   if result:ready.append(result)
  except Exception as e:
   record_failure('WAVE8_EXTRA_VERIFY',repr(e),{'tag':p['tag']})
   w.log('WAVE8_EXTRA_VERIFY_FAIL '+p['tag']+' '+repr(e))
# Fail closed: never offer two identical artifacts as distinct probes.
seen={combo['semantic_sha256']};unique=[]
for p in ready:
 if p['semantic_sha256'] in seen:
  record_failure('E003','Duplicate Wave8 artifact blocked',{'tag':p['tag']});continue
 seen.add(p['semantic_sha256']);unique.append(p)
(R/'wave8_extra_ready.json').write_text(json.dumps(unique,ensure_ascii=False,indent=2))
print('VERIFIED_EXTRA',len(unique),[p['tag'] for p in unique]);print('NO_SUBMISSIONS_MADE')

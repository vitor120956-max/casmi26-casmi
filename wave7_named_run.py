#!/usr/bin/env python3
"""Wave7 transport-fixed runner: one readiness check per kernel, no polling/retry."""
import concurrent.futures,datetime as dt,fcntl,json,pathlib,sys
import wave7_run as w
from safety_guards import validate_submission_plan,record_failure

def run(dry=False):
 api=w.connect()
 now=dt.datetime.now(dt.timezone.utc)
 assert w.RESET<=now<w.END,'OUTSIDE_AUTHORIZED_RESET_WINDOW'
 quota=w.obj(api.competition_get_submission_limits(w.COMP));w.log('NAMED_LIMITS '+json.dumps(quota))
 subs=[w.obj(x) for x in api.competition_submissions(w.COMP,page_size=100)]
 w.dump('submissions_named_before.json',subs)
 if int(quota['numAllowedNow'])==0:w.log('STOP_NO_SLOTS');return
 statepath=w.ROOT/'wave7_submit_state.json'
 state=json.loads(statepath.read_text()) if statepath.exists() else {}
 plans=json.loads((w.ROOT/'wave7_named_plan.json').read_text())
 baseline=w.old_plans()[0]
 baseline['output_dir']=str(w.ROOT/'probeout_w088')
 # Baseline first only when it is genuinely missing; mechanism priority otherwise.
 if not any(s.get('description')=='PROBE-WAVE7:w088-blend VERIFY PASS' for s in subs):plans.insert(0,baseline)
 todo=[]
 for p in plans:
  p['message']='PROBE-WAVE7:'+p['tag']+' VERIFY PASS'
  validate_submission_plan(p)
  already=[s for s in subs if s.get('description')==p['message']]
  if already:w.log('SKIP_ALREADY_SUBMITTED '+p['tag']+' '+str([s['ref'] for s in already]));continue
  if p['tag'] in state:w.log('SKIP_JOURNALED '+p['tag']+'; reconcile manually');continue
  todo.append(p)
 if dry:
  w.log('DRY_RUN_NAMED_PLAN '+json.dumps(todo));return
 history=json.loads((w.ROOT/'historical_hashes.json').read_text())
 for entry in state.values():
  if entry.get('phase')=='accepted':
   sig=entry.get('plan',{}).get('semantic_sha256')
   if sig:history[sig]=['already accepted in Wave7']
 def collect(p):
  from kaggle.api.kaggle_api_extended import KaggleApi
  a=KaggleApi();a.authenticate()
  status=w.obj(a.kernels_status(p['kernel']))
  w.log('NAMED_CHECK_ONCE '+p['tag']+' '+json.dumps(status))
  if status.get('status')!='COMPLETE':return None
  if p['tag']!='w088-blend':
   directory=pathlib.Path(p['output_dir'])
   a.kernels_output(p['kernel'],str(directory),file_pattern=r'^(submission\.csv|wave7_ready\.json)$',force=True,quiet=True)
   proof=json.loads((directory/'wave7_ready.json').read_text())
   assert proof['tag']==p['tag'] and proof['file']=='submission.csv'
   assert proof['cpu_only'] and proof['full_pipeline'] and proof['transport_only_change']
   assert proof['sha256']==p['sha256']==proof['expected_sha256']
   p['path']=str(directory/'submission.csv')
  sig,_=w.verify(pathlib.Path(p['path']),p['sha256'],history)
  p['semantic_sha256']=sig
  return p
 ready=[]
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
  tasks=[pool.submit(collect,p) for p in todo]
  for p,task in zip(todo,tasks):
   try:
    result=task.result()
    if result:ready.append(result)
   except Exception as e:
    record_failure('E003',repr(e),{'tag':p['tag'],'stage':'verification'})
    w.log('NAMED_VERIFY_FAIL '+p['tag']+' '+repr(e))
 w.dump('wave7_named_ready.json',ready)
 assert len({p['semantic_sha256'] for p in ready})==len(ready),'DUPLICATE_READY_OUTPUT'
 capacity=int(quota['numAllowedNow']);accepted=0
 for p in ready:
  if accepted>=capacity:break
  tag=p['tag'];state[tag]={'phase':'intent','plan':p,'at':dt.datetime.now(w.BRT).isoformat()}
  w.dump('wave7_submit_state.json',state)
  try:
   response=w.obj(api.competition_submit_code(file_name='submission.csv',message=p['message'],competition=w.COMP,kernel=p['kernel'],kernel_version=p['version'],quiet=True))
   assert response.get('ref'),('MISSING_SUBMISSION_REF',response)
   state[tag].update(phase='accepted',response=response)
   w.dump('wave7_submit_state.json',state);accepted+=1
   w.log('SUBMITTED '+tag+' '+json.dumps(response))
  except Exception as e:
   resp=getattr(e,'response',None)
   info=dict(error=repr(e),http_status=None if resp is None else resp.status_code,response_body=None if resp is None else resp.text)
   record_failure('SUBMIT_REJECTED_OR_AMBIGUOUS',repr(e),{'tag':tag,'http_status':info['http_status'],'details_file':'wave7_submit_state.json'})
   state[tag].update(phase='ambiguous_or_failed',**info)
   w.dump('wave7_submit_state.json',state);w.log('STOP_NAMED_SUBMIT_ERROR '+json.dumps(info));break
 w.log('NAMED_LIMITS_AFTER '+str(api.competition_get_submission_limits(w.COMP)))
 w.log('NAMED_DONE accepted_now='+str(accepted)+'; no retry or polling scheduled by this script')

if __name__=='__main__':
 lock=(w.ROOT/'wave7.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 run('--dry-run' in sys.argv)

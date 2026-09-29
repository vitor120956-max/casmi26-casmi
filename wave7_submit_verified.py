#!/usr/bin/env python3
# One-shot send of explicitly selected, verified Wave7 artifacts. No retries.
import sys,json,pathlib,datetime as dt,fcntl
import wave7_run as w
from kaggle.api.kaggle_api_extended import KaggleApi
root=w.ROOT
lock=(root/'wave7.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
assert w.RESET<=dt.datetime.now(dt.timezone.utc)<w.END,'OUTSIDE_RESET_WINDOW'
api=KaggleApi();api.authenticate()
plans={p['tag']:p for p in w.old_plans()+json.loads((root/'wave7_cpu_ready.json').read_text())}
statepath=root/'wave7_submit_state.json'
state=json.loads(statepath.read_text()) if statepath.exists() else {}
subs=[w.obj(s) for s in api.competition_submissions(w.COMP,page_size=100)]
quota=w.obj(api.competition_get_submission_limits(w.COMP));w.log('ONE_SHOT_LIMITS '+json.dumps(quota))
history=json.loads((root/'historical_hashes.json').read_text())
chosen=[]
for tag in sys.argv[1:]:
 p=plans[tag];assert p['file']=='submission.csv','DEPRECATED_PLAN: use wave7_run.py with named kernels';p['message']='PROBE-WAVE7:'+tag+' VERIFY PASS'
 if tag in state or any(s.get('description')==p['message'] for s in subs):
  w.log('SKIP_JOURNALED_OR_SUBMITTED '+tag);continue
 sig,_=w.verify(pathlib.Path(p['path']),p['sha256'],history)
 p['semantic_sha256']=sig;chosen.append(p)
assert len(chosen)<=quota['numAllowedNow'],'NOT_ENOUGH_SLOTS'
assert len({p['semantic_sha256'] for p in chosen})==len(chosen)
for p in chosen:
 tag=p['tag'];state[tag]={'phase':'intent','plan':p,'at':dt.datetime.now(w.BRT).isoformat()}
 w.dump('wave7_submit_state.json',state)
 try:
  r=w.obj(api.competition_submit_code(file_name=p['file'],message=p['message'],competition=w.COMP,kernel=p['kernel'],kernel_version=1,quiet=True))
  assert r.get('ref'),('NO_REF',r)
  state[tag].update(phase='accepted',response=r)
  w.dump('wave7_submit_state.json',state);w.log('SUBMITTED '+tag+' '+json.dumps(r))
 except Exception as e:
  response=getattr(e,'response',None)
  detail={'error':repr(e),'http_status':None if response is None else response.status_code,'response_body':None if response is None else response.text}
  state[tag].update(phase='ambiguous_or_failed',**detail)
  w.dump('wave7_submit_state.json',state);w.log('SUBMIT_ERROR '+tag+' '+json.dumps(detail));break
w.log('LIMITS_AFTER '+str(api.competition_get_submission_limits(w.COMP)))

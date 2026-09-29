#!/usr/bin/env python3
"""Explicit Wave8 send after reset. Default is dry-run; no timers or retry loops."""
import argparse,datetime as dt,fcntl,json,pathlib,sys
import wave7_run as w
from safety_guards import validate_submission_plan,record_failure
R=w.ROOT;BEGIN=dt.datetime(2026,9,28,0,0,tzinfo=dt.timezone.utc);END=BEGIN+dt.timedelta(days=1)
parser=argparse.ArgumentParser();parser.add_argument('--execute',action='store_true');args=parser.parse_args()
lock=(R/'wave8.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
if args.execute and not BEGIN<=dt.datetime.now(dt.timezone.utc)<END:raise SystemExit('OUTSIDE_WAVE8_AUTHORIZED_RESET_WINDOW')
a=w.connect();quota=w.obj(a.competition_get_submission_limits(w.COMP));subs=[w.obj(s) for s in a.competition_submissions(w.COMP,page_size=100)]
w.log('WAVE8_QUOTA '+json.dumps(quota));w.dump('wave8_before_send.json',{'quota':quota,'submissions':subs})
combo=json.loads((R/'wave8_ready.json').read_text());combo['tag']='formula_dedup'
extra=R/'wave8_extra_ready.json';plans=[combo]+(json.loads(extra.read_text()) if extra.exists() else [])
priority={'adduct':0,'adduct_dedup':1,'formula_dedup':2,'top1':3,'top1_dedup':4};plans.sort(key=lambda p:priority[p['tag']])
statepath=R/'wave8_submit_state.json';state=json.loads(statepath.read_text()) if statepath.exists() else {}
history=json.loads((R/'historical_hashes.json').read_text())
for entry in json.loads((R/'wave7_submit_state.json').read_text()).values():
 if entry.get('phase')=='accepted':history[entry['plan']['semantic_sha256']]=['Wave7 accepted']
seen=set();valid=[]
for p in plans:
 assert p.get('preview_verified') and p.get('controls_regression_pass')
 validate_submission_plan(p);p['message']='PROBE-WAVE8:'+p['tag']+' VERIFY PASS'
 if p['tag'] in state or any(s.get('description')==p['message'] for s in subs):
  w.log('WAVE8_SKIP_JOURNAL_OR_API '+p['tag']);continue
 sig,_=w.verify(pathlib.Path(p['path']),p['sha256'],history)
 if sig in seen:raise ValueError('DUPLICATE_IN_WAVE8')
 seen.add(sig);p['semantic_sha256']=sig;valid.append(p)
if not args.execute:
 w.log('WAVE8_DRY_RUN '+str([p['tag'] for p in valid])+'; no submission called');sys.exit(0)
capacity=int(quota['numAllowedNow']);count=0
for p in valid:
 if count>=capacity:break
 tag=p['tag'];state[tag]={'phase':'intent','at':dt.datetime.now(w.BRT).isoformat(),'plan':p};w.dump('wave8_submit_state.json',state)
 try:
  response=w.obj(a.competition_submit_code(file_name='submission.csv',message=p['message'],competition=w.COMP,kernel=p['kernel'],kernel_version=p['version'],quiet=True))
  if not response.get('ref'):raise ValueError('MISSING_SUBMISSION_REF')
  state[tag].update(phase='accepted',response=response);w.dump('wave8_submit_state.json',state);count+=1
  w.log('WAVE8_SUBMITTED '+tag+' '+json.dumps(response))
 except Exception as e:
  resp=getattr(e,'response',None);info={'error':repr(e),'http_status':None if resp is None else resp.status_code,'response_body':None if resp is None else resp.text}
  state[tag].update(phase='ambiguous_or_failed',**info);w.dump('wave8_submit_state.json',state)
  record_failure('WAVE8_SUBMIT_ERROR',repr(e),{'tag':tag,'details':'wave8_submit_state.json'})
  w.log('WAVE8_STOP '+json.dumps(info));break
w.log('WAVE8_LIMITS_AFTER '+str(a.competition_get_submission_limits(w.COMP)))
w.log('WAVE8_DONE '+str(count)+' accepted now; no score implied')

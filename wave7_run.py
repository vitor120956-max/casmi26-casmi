#!/usr/bin/env python3
"""One-shot Wave7: no sleep, no status polling, no automatic retry of submissions."""
import argparse,csv,datetime as dt,fcntl,hashlib,json,pathlib,subprocess,sys,traceback
ROOT=pathlib.Path('/home/user')
COMP='enveda-CASMI26-molecule-id-mass-spectra'
ORIGINAL='victor120956/casmi26-w088-replica-llccqq624-apache-2-0'
CPU='victor120956/casmi26-wave7-w088-formula-dedup-cpu'
RESET=dt.datetime(2026,9,27,0,0,tzinfo=dt.timezone.utc)
END=RESET+dt.timedelta(days=1)
BRT=dt.timezone(dt.timedelta(hours=-3))

def log(msg):
 line=dt.datetime.now(BRT).isoformat(timespec='seconds')+' '+str(msg)
 print(line,flush=True)
 with (ROOT/'day_watch.log').open('a') as f:f.write(line+'\n')

def dump(name,data):
 p=ROOT/name;t=p.with_suffix(p.suffix+'.tmp');t.write_text(json.dumps(data,ensure_ascii=False,indent=2,default=str));t.replace(p)

def obj(x):return json.loads(str(x))

def semantic(rows):
 return hashlib.sha256(json.dumps(sorted((r['molecule_id'],r['smiles']) for r in rows),separators=(',',':')).encode()).hexdigest()

def verify(path,expected_sha,history):
 from rdkit import Chem,RDLogger
 RDLogger.DisableLog('rdApp.*')
 raw=path.read_bytes(); assert hashlib.sha256(raw).hexdigest()==expected_sha, ('HASH_MISMATCH',path)
 with path.open() as f:rows=list(csv.DictReader(f))
 with (ROOT/'harness_data/sample_submission.csv').open() as f:sample=list(csv.DictReader(f))
 assert len(rows)==400 and list(rows[0])==['molecule_id','smiles']
 assert [r['molecule_id'] for r in rows]==[r['molecule_id'] for r in sample]
 assert len({r['molecule_id'] for r in rows})==400
 lists=[r['smiles'].split(';') for r in rows]
 assert all(len(x)==25 and all(x) for x in lists)
 assert all(Chem.MolFromSmiles(s) is not None for x in lists for s in x)
 sig=semantic(rows);assert sig not in history, ('DUPLICATE_OUTPUT',path,history.get(sig))
 return sig,rows

def connect():
 subprocess.run(['bash',str(ROOT/'arm.sh')],cwd=ROOT,check=True,timeout=120)
 from kaggle.api.kaggle_api_extended import KaggleApi
 api=KaggleApi();api.authenticate();return api

def old_plans():
 report=json.loads((ROOT/'verify_wave7.json').read_text())
 return [dict(tag=tag,kernel=ORIGINAL,version=1,file=name,path=str(ROOT/'probeout_w088'/name),sha256=report[name]['sha256']) for tag,name in [('w088-blend','submission.csv'),('w088-ours','submission_ours.csv'),('w088-pv','submission_pv.csv')]]

def gather_cpu(api):
 status=obj(api.kernels_status(CPU));log('CPU_CHECK_ONCE '+json.dumps(status))
 if status.get('status')!='COMPLETE':return []
 directory=ROOT/'probeout_wave7_cpu'
 api.kernels_output(CPU,str(directory),file_pattern=r'^(submission.*\.csv|wave7_verify\.json)$',force=True,quiet=True)
 proof=json.loads((directory/'wave7_verify.json').read_text())
 assert proof['gpu'] is False and proof['own_dataset_inputs'] is False
 original=json.loads((ROOT/'verify_wave7.json').read_text())
 for name,value in proof['baseline_md5'].items():
  assert value==original[name]['md5']
  assert hashlib.md5((directory/name).read_bytes()).hexdigest()==value
 assert proof['formula_changed_rows']>0 and proof['dedup_changed_rows']>0
 history=json.loads((ROOT/'historical_hashes.json').read_text())
 plans=[]
 for tag,name in [('w088-formula','submission_formula.csv'),('w088-dedup','submission_dedup.csv')]:
  p=dict(tag=tag,kernel=CPU,version=1,file=name,path=str(directory/name),sha256=proof['files'][name]['sha256'])
  _,rows=verify(directory/name,p['sha256'],history)
  with (directory/'submission.csv').open() as f:base=list(csv.DictReader(f))
  assert any(a['smiles']!=b['smiles'] for a,b in zip(rows,base))
  if tag=='w088-formula':assert all(sorted(a['smiles'].split(';'))==sorted(b['smiles'].split(';')) for a,b in zip(rows,base))
  else:assert all('CCO' not in r['smiles'].split(';') for r in rows)
  plans.append(p)
 dump('wave7_cpu_ready.json',plans)
 return plans

def execute(dry=False):
 api=connect()
 limits=obj(api.competition_get_submission_limits(COMP));log('LIMITS '+json.dumps(limits))
 if not dry:
  now=dt.datetime.now(dt.timezone.utc)
  assert RESET<=now<END, 'OUTSIDE_AUTHORIZED_RESET_WINDOW'
  if int(limits['numAllowedNow'])==0:log('STOP: quota zero; no retry, no orphan replacement');return
 plans=old_plans()
 if not dry:
  try:plans=gather_cpu(api)+plans
  except Exception as e:log('CPU_NOT_VERIFIED: '+repr(e)+'; keep its two slots unused')
 else:log('DRY_RUN: CPU output not fetched while job runs; submission API will NOT be called')
 history=json.loads((ROOT/'historical_hashes.json').read_text())
 seen={};valid=[]
 # All local validation before the first remote submission.
 for p in plans:
  sig,_=verify(pathlib.Path(p['path']),p['sha256'],history)
  assert sig not in seen, ('DUPLICATE_IN_WAVE',p['tag'])
  seen[sig]=p['tag'];p['semantic_sha256']=sig
  p['message']='PROBE-WAVE7:'+p['tag']+' VERIFY PASS'
  valid.append(p)
 if dry:
  dump('wave7_dry_run.json',valid);log('DRY_RUN_PASS '+str([p['tag'] for p in valid]));return
 submissions=[obj(x) for x in api.competition_submissions(COMP,page_size=100)]
 dump('submissions_at_reset.json',submissions)
 statepath=ROOT/'wave7_submit_state.json'
 state=json.loads(statepath.read_text()) if statepath.exists() else {}
 capacity=int(limits['numAllowedNow']);count=0
 needed=[p for p in valid if p['tag'] not in state and not any(s.get('description')==p['message'] for s in submissions)]
 if capacity < len(needed):
  log('STOP: quota insufficient for the verified batch; no partial orphan allocation');return
 for p in valid:
  tag=p['tag']
  already=[s for s in submissions if s.get('description')==p['message']]
  if already:
   log('SKIP_ALREADY_SUBMITTED '+tag+' refs='+str([s['ref'] for s in already]));continue
  if tag in state:
   log('SKIP_JOURNALED '+tag+' (resolve ambiguous intent manually; never retry blindly)');continue
  if count>=capacity:log('STOP_CAPACITY '+str(capacity));break
  state[tag]={'phase':'intent','plan':p,'at':dt.datetime.now(BRT).isoformat()}
  dump('wave7_submit_state.json',state)  # write-ahead: crash cannot silently cause retry
  try:
   response=obj(api.competition_submit_code(file_name=p['file'],message=p['message'],competition=COMP,kernel=p['kernel'],kernel_version=1,quiet=True))
   assert response.get('ref'), ('NO_SUBMISSION_REF',response)
   state[tag].update(phase='accepted',response=response)
   dump('wave7_submit_state.json',state);count+=1
   log('SUBMITTED '+tag+' '+json.dumps(response))
  except Exception as e:
   state[tag].update(phase='ambiguous_or_failed',error=repr(e))
   dump('wave7_submit_state.json',state);log('STOP_SUBMIT_ERROR '+repr(e));break
 log('LIMITS_AFTER '+str(api.competition_get_submission_limits(COMP)))
 log('DONE accepted_now='+str(count)+'; acceptance is NOT a ranked score')

def report():
 api=connect();subs=[obj(s) for s in api.competition_submissions(COMP,page_size=100)]
 dump('submissions_score_check.json',subs)
 wave=[s for s in subs if (s.get('description') or '').startswith('PROBE-WAVE7:')]
 scores={s['description'].split(':',1)[1].split(' ')[0]:float(s['publicScore']) for s in wave if s.get('publicScore') not in [None,'']}
 lines=['# Wave7 — leitura única de notas', '', 'Aceito/COMPLETE sem nota não é ranqueado.', '',f'Notas confirmadas: {len(scores)}/5', '',json.dumps(scores,ensure_ascii=False,indent=2),'']
 if all(t in scores for t in ['w088-blend','w088-ours','w088-pv']):
  tags=['w088-blend','w088-ours','w088-pv'];winner=max(tags,key=lambda t:scores[t]);ties=[t for t in tags if scores[t]==scores[winner]]
  lines += ['Próximo build: '+('empate; preferir ramo mais simples, sem caça a pesos/seeds.' if len(ties)>1 else 'ramo '+winner+' como referência provisória, não ganho definitivo.')]
 if 'w088-blend' in scores:
  for tag in ['w088-formula','w088-dedup']:
   if tag in scores:
    delta=scores[tag]-scores['w088-blend'];lines.append(f'{tag}: delta {delta:+.3f}; '+('levar mecanismo ao próximo build.' if delta>0 else 'não promover mecanismo; empate/perda.'))
 if len(scores)<5:lines.append('Ainda faltam notas/probes. Sem decisão por ausência, sem resubmit automático.')
 (ROOT/'WAVE7_RESULTADO.md').write_text('\n'.join(lines)+'\n')
 log('SCORE_CHECK_ONCE '+json.dumps(scores)+'; no repeat scheduled')

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--dry-run',action='store_true');parser.add_argument('--report',action='store_true');args=parser.parse_args()
 lock=(ROOT/'wave7.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 try:report() if args.report else execute(args.dry_run)
 except Exception as e:log('FATAL '+repr(e));traceback.print_exc();sys.exit(1)

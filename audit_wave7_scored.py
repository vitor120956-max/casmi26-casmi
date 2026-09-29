#!/usr/bin/env python3
"""Read-only audit via official Kaggle download_submission; never submit or retry."""
import concurrent.futures,csv,gzip,hashlib,io,json,pathlib,zipfile
import requests
from kaggle.api.kaggle_api_extended import KaggleApi
from kagglesdk.competitions.types.competition_api_service import ApiDownloadSubmissionRequest
R=pathlib.Path('/home/user');D=R/'wave7_scored_audit';D.mkdir(exist_ok=True)
subs=json.loads((R/'submissions_score_check.json').read_text())
state=json.loads((R/'wave7_submit_state.json').read_text())
wave=[s for s in subs if (s.get('description') or '').startswith('PROBE-WAVE7:')]
def digest(b):return hashlib.sha256(b).hexdigest()
def rows(b):
 return list(csv.DictReader(io.StringIO(b.decode('utf-8-sig'))))
def run(s):
 tag=s['description'].split(':',1)[1].split()[0]
 local=pathlib.Path(state[tag]['plan']['path']).read_bytes()
 a=KaggleApi();a.authenticate();req=ApiDownloadSubmissionRequest();req.submission_id=s['ref']
 with a.build_kaggle_client() as client:
  response=client.competitions.competition_api_client.download_submission(req)
 if hasattr(response,'raise_for_status'):response.raise_for_status()
 if hasattr(response,'content'):raw=response.content
 else:
  response=requests.get(response.url,timeout=60);response.raise_for_status();raw=response.content
 if raw[:2]==b'PK':
  with zipfile.ZipFile(io.BytesIO(raw)) as z:
   names=[n for n in z.namelist() if n.endswith('.csv')];assert len(names)==1,'Ambiguous submission archive';raw=z.read(names[0])
 elif raw[:2]==b'\x1f\x8b':raw=gzip.decompress(raw)
 scored_rows=rows(raw);local_rows=rows(local)
 assert scored_rows and set(scored_rows[0])=={'molecule_id','smiles'},'Unexpected download format'
 p=D/f'{s["ref"]}_{tag}.csv';p.write_bytes(raw)
 A={x['molecule_id']:x['smiles'] for x in scored_rows};B={x['molecule_id']:x['smiles'] for x in local_rows};shared=set(A)&set(B)
 return dict(tag=tag,ref=s['ref'],publicScore=s['publicScore'],reported_bytes=s['totalBytes'],downloaded_bytes=len(raw),local_bytes=len(local),
             downloaded_sha256=digest(raw),local_sha256=digest(local),exact_match=raw==local,
             scored_rows=len(scored_rows),local_rows=len(local_rows),shared_ids=len(shared),
             same_predictions_on_shared_ids=sum(A[k]==B[k] for k in shared),download_path=str(p))
results=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
 tasks={pool.submit(run,s):s for s in wave}
 for task,s in tasks.items():
  try:results.append(task.result())
  except Exception as e:
   # Never expose signed download URLs.
   status=getattr(getattr(e,'response',None),'status_code',None)
   results.append(dict(ref=s['ref'],error_type=type(e).__name__,http_status=status))
(D/'audit.json').write_text(json.dumps(results,indent=2));print(json.dumps(results,indent=2))

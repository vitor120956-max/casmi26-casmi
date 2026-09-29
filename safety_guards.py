"""Travas locais auditáveis. Nenhuma chamada de rede ou submissão neste módulo."""
import ast,datetime as dt,json,math,pathlib,re
COMP='enveda-CASMI26-molecule-id-mass-spectra'
GITHUB_CLI_CLIENT_ID='178c6fc778ccc68e1d6a'
GITHUB_CLI_ID_SOURCE='https://github.com/cli/cli/blob/trunk/internal/authflow/flow.go'
ALLOWED_ASSETS={
 'prvsiyan/casmi26-fp-models-v2','aidensong123/casmi26-offline-rdkit-2026033',
 'prvsiyan/casmi26-ranker-features','megayak/casmi26-simulated-ranker-rows',
 'prvsiyan/chebi-lipidmaps-casmi26','prvsiyan/coconut-casmi26-candidates',
 'thedevastator/open-source-natural-product-annotations','franciscoangulo/casmi26-mist-msbuddy-assets'}
def require(condition,code):
 if not condition:raise ValueError(code)
def validate_submission_plan(p):
 require(p.get('file')=='submission.csv','E001_LITERAL_SUBMISSION_FILENAME')
 require(bool(re.fullmatch(r'victor120956/[a-z0-9-]+',p.get('kernel',''))),'E002_REAL_KERNEL_SLUG_REQUIRED')
 require(type(p.get('version')) is int and p['version']>0,'E002_PINNED_VERSION_REQUIRED')
 require(bool(re.fullmatch(r'[0-9a-f]{64}',p.get('sha256',''))),'E003_KNOWN_FILE_HASH_REQUIRED')
def validate_oauth(client_id,scopes=None):
 require(client_id==GITHUB_CLI_CLIENT_ID,'E009_WRONG_OAUTH_APPLICATION')
 if scopes is not None:
  require(bool(set(scopes)&{'public_repo','repo'}),'E010_OAUTH_WRITE_SCOPE_MISSING')
def classify_submission(s):
 if s.get('errorDescription'):return 'REJEITADA'
 status=str(s.get('status','')).split('.')[-1].upper()
 score=s.get('publicScore')
 if status=='COMPLETE' and score is not None and str(score).strip():
  try:
   if math.isfinite(float(score)):return 'RANQUEADA'
  except (ValueError,TypeError):pass
 return 'AGUARDANDO_NOTA'
def validate_kernel(m,n):
 require(m.get('enable_gpu') is False and m.get('enable_tpu',False) is False,'E004_CPU_ONLY')
 require(m.get('competition_sources')==[COMP],'E002_COMPETITION_SOURCE')
 require(not m.get('kernel_sources'),'E005_NO_UPSTREAM_OUTPUTS')
 require(set(m.get('dataset_sources',[]))<=ALLOWED_ASSETS,'E005_NO_OWN_DATASET_OR_TIER2')
 spec=n.get('metadata',{}).get('kernelspec',{})
 require(spec.get('name')=='python3' and spec.get('language')=='python','E006_KERNELSPEC_REQUIRED')
 for i,c in enumerate(n.get('cells',[])):
  if c.get('cell_type')!='code':continue
  s=''.join(c.get('source',[]))
  if s.startswith('%%writefile '):s=s.split('\n',1)[1]
  ast.parse(s,filename=f'cell_{i}')
  require('tier2_' not in s.lower(),'E005_TIER2_FORBIDDEN')
def record_failure(code,summary,context=None,path='/home/user/incidents.jsonl'):
 # Do not pass secrets, headers, tokens or raw OAuth responses into this function.
 row={'at':dt.datetime.now(dt.timezone(dt.timedelta(hours=-3))).isoformat(timespec='seconds'),
      'code':code,'summary':str(summary),'context':context or {},'state':'OPEN_REQUIRES_DIAGNOSIS'}
 with pathlib.Path(path).open('a') as f:f.write(json.dumps(row,ensure_ascii=False)+'\n')

def score_attribution_warnings(submissions,footprints):
 """Heuristic alarm only: metadata cannot prove which predictions were scored."""
 ranked=[s for s in submissions if classify_submission(s)=='RANQUEADA']
 if len(ranked)<3:return []
 known=[]
 for s in ranked:
  desc=s.get('description') or ''
  tag=desc.split(':',1)[-1].split(' ')[0]
  if tag in footprints:known.append((s,footprints[tag]))
 if len(known)!=len(ranked):return ['SCORING_LINEAGE_UNVERIFIED']
 scores={str(s.get('publicScore')) for s,_ in known}
 remote_sizes={s.get('totalBytes') for s,_ in known}
 local_sizes={p['local_bytes'] for _,p in known}
 hashes={p['sha256'] for _,p in known}
 if len(scores)==1 and len(remote_sizes)==1 and next(iter(remote_sizes)) not in (None,0) and len(local_sizes)>1 and len(hashes)>1:
  return ['E018_IDENTICAL_SCORE_METADATA_FOR_DISTINCT_OUTPUTS']
 return []

def validate_publication_safety(notebook):
 """Static guard for known unsafe patterns; not a proof for arbitrary Python I/O."""
 lines=[]
 for c in notebook.get('cells',[]):
  if c.get('cell_type')=='code':lines.extend(''.join(c.get('source',[])).splitlines())
 text='\n'.join(lines)
 writes=[]
 for i,line in enumerate(lines):
  if re.search(r'''\.to_csv\(\s*['"]submission\.csv['"]''',line) or re.search(r'''Path\(\s*['"]submission\.csv['"]\s*\)\.(?:write_bytes|write_text)\(''',line):writes.append(i)
 require(len(writes)<=1,'E020_MULTIPLE_PUBLISHES_TO_SUBMISSION_CSV')
 markers=['W088_REPRODUCTION_FAILED','BASELINE_CHANGED','VARIANT_CHANGED_DO_NOT_SUBMIT']
 if writes:
  tail='\n'.join(lines[writes[0]+1:])
  require(not any(m in tail for m in markers),'E020_BASELINE_PUBLISHED_BEFORE_VALIDATION')
 require(not any(m in text for m in markers),'E021_PREVIEW_HASH_GUARD_IN_PRODUCTION')

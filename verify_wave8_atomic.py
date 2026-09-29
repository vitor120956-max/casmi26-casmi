#!/usr/bin/env python3
"""Single read-only verification; no submission, no polling, no scheduled retry."""
import hashlib,json,pathlib,sys
from kaggle.api.kaggle_api_extended import KaggleApi
from safety_guards import validate_kernel,validate_publication_safety
from atomic_submission import AtomicSubmission
from rdkit import Chem,RDLogger
from functools import lru_cache
import wave7_run as w
R=pathlib.Path('/home/user');slug='victor120956/casmi26-wave8-atomic-formula-dedup-cpu'
a=KaggleApi();a.authenticate();status=json.loads(str(a.kernels_status(slug)))
print('STATUS',status)
if status.get('status')!='COMPLETE':
 print('NOT_READY: no submission, no automatic retry');sys.exit(0)
D=R/'probeout_wave8_atomic';D.mkdir(exist_ok=True)
a.kernels_output(slug,str(D),file_pattern=r'^(submission\.csv|audit_.*\.csv|publication\.json|lineage_before_publish\.json)$',force=True,quiet=True)
M=R/'wave8_final_remote_check';a.kernels_pull(slug,str(M),metadata=True,quiet=True)
meta=json.loads((M/'kernel-metadata.json').read_text());remote=json.loads((M/meta['code_file']).read_text())
local=json.loads((R/'kpush_wave8_atomic_combo_cpu/wave8.ipynb').read_text())
validate_kernel(meta,remote);validate_publication_safety(remote)
assert meta['id']==slug
assert [''.join(c['source']) for c in local['cells']]==[''.join(c['source']) for c in remote['cells']]
proof=json.loads((D/'publication.json').read_text());data=(D/'submission.csv').read_bytes()
assert proof['publication_contract']=='atomic-final-only-v1' and proof['variant']=='formula_dedup'
assert proof['cpu_only'] and proof['full_pipeline'] and not proof['own_dataset_inputs']
assert hashlib.sha256(data).hexdigest()==proof['sha256'] and len(data)==proof['bytes']
expected=json.loads((R/'wave8_local_expectations/expected.json').read_text())
assert proof['sha256']==expected['combo_sha256'],'PREVIEW_REGRESSION_FAILED'
# These golden hashes are checked here, outside production notebook execution.
reference={
 'blend':R/'probeout_w088/submission.csv', 'ours':R/'probeout_w088/submission_ours.csv',
 'pv':R/'probeout_w088/submission_pv.csv', 'formula':R/'probeout_wave7_cpu/submission_formula.csv',
 'dedup':R/'probeout_wave7_cpu/submission_dedup.csv',
 'formula_dedup':R/'wave8_local_expectations/formula_dedup.csv'}
for name,baseline in reference.items():
 actual=(D/f'audit_{name}.csv').read_bytes()
 assert actual==baseline.read_bytes(),('CONTROL_REGRESSION',name)
 assert hashlib.sha256(actual).hexdigest()==proof['artifacts'][name]['sha256']
assert data==(D/'audit_formula_dedup.csv').read_bytes()
history=json.loads((R/'historical_hashes.json').read_text())
state=json.loads((R/'wave7_submit_state.json').read_text())
for tag,e in state.items():
 if e.get('phase')=='accepted':history[e['plan']['semantic_sha256']]=['Wave7 '+tag]
sig,rows=w.verify(D/'submission.csv',proof['sha256'],history)
result=dict(tag='w088-formula-dedup-atomic',kernel=slug,version=1,file='submission.csv',path=str(D/'submission.csv'),
            sha256=proof['sha256'],semantic_sha256=sig,preview_verified=True,controls_regression_pass=True,
            causal_scoring_audit_resolved=False,
            question='Fórmula top5 aplicada após dedup/refill melhora W088 blend 0.341?',
            decision='Promover combinação apenas com ganho medido e atribuição de arquivo confiável; caso contrário não promover.',
            no_automatic_submission=True)
(R/'wave8_ready.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
for artifact in D.glob('audit_*.csv'):artifact.unlink()  # keep final + proofs, not duplicate controls
print('WAVE8_PREVIEW_VERIFY_PASS',json.dumps(result))

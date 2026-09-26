#!/usr/bin/env bash
set -euo pipefail
python - "$1" <<'PY'
import json,pathlib,sys,re,ast
p=pathlib.Path(sys.argv[1]);m=json.loads((p/'kernel-metadata.json').read_text())
assert m['enable_gpu'] is False and m.get('enable_tpu',False) is False, 'CPU_ONLY'
assert m['competition_sources']==['enveda-CASMI26-molecule-id-mass-spectra']
assert not m.get('kernel_sources'), 'NO_UPSTREAM_OUTPUTS'
allowed={'prvsiyan/casmi26-fp-models-v2','aidensong123/casmi26-offline-rdkit-2026033','prvsiyan/casmi26-ranker-features','megayak/casmi26-simulated-ranker-rows','prvsiyan/chebi-lipidmaps-casmi26','prvsiyan/coconut-casmi26-candidates','thedevastator/open-source-natural-product-annotations','franciscoangulo/casmi26-mist-msbuddy-assets'}
assert set(m.get('dataset_sources',[])) <= allowed, 'NO_OWN_DATASET_OR_TIER2'
n=json.loads((p/m['code_file']).read_text())
assert n['metadata']['kernelspec']['name']=='python3', 'KERNELSPEC_REQUIRED'
assert n['metadata']['kernelspec']['language']=='python'
for i,c in enumerate(n['cells']):
 if c['cell_type']!='code':continue
 s=''.join(c['source'])
 if s.startswith('%%writefile '): s=s.split('\n',1)[1]
 ast.parse(s,filename=f'cell_{i}')
 assert 'tier2_' not in s.lower(), 'TIER2_FORBIDDEN'
print('PRECHECK PASS: CPU; kernelspec; syntax; full pipeline; no own datasets; no tier2')
PY

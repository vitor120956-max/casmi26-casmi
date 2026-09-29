#!/usr/bin/env python3
import json,copy,pathlib,hashlib
R=pathlib.Path('/home/user')
original=json.loads((R/'verify_wave7.json').read_text())
mechanisms=json.loads((R/'probeout_wave7_cpu/wave7_verify.json').read_text())
old=R/'kpush_w088_original';cpu=R/'kpush_wave7_cpu'
variants=[('formula',cpu,'submission_formula.csv',mechanisms['files']['submission_formula.csv']['sha256']),
          ('dedup',cpu,'submission_dedup.csv',mechanisms['files']['submission_dedup.csv']['sha256']),
          ('ours',old,'submission_ours.csv',original['submission_ours.csv']['sha256']),
          ('pv',old,'submission_pv.csv',original['submission_pv.csv']['sha256'])]
plans=[]
for name,source,source_file,expected in variants:
 metadata=json.loads((source/'kernel-metadata.json').read_text())
 nb=json.loads((source/metadata['code_file']).read_text())
 for c in nb['cells']:
  if c['cell_type']=='code':c.update(outputs=[],execution_count=None)
 slug=f'casmi26-wave7-w088-{name}-submit-cpu'
 folder=R/f'kpush_wave7_submit_{name}';folder.mkdir(exist_ok=True)
 nb['cells'].append({'cell_type':'markdown','metadata':{},'source':[
  '# Correção de transporte, sem mudança de previsão\n',
  'A competição exige o nome literal submission.csv. Regeneramos o pipeline inteiro em CPU; não lemos outputs/dataset próprio.\n',
  f'Este kernel envia somente W088 {name}. Hash deve coincidir com o arquivo já validado da mesma variante.\n']})
 code=f'''from pathlib import Path
import hashlib, json
EXPECTED_BASE = { {k:v['md5'] for k,v in original.items()}!r}
for filename, expected_md5 in EXPECTED_BASE.items():
    assert hashlib.md5(Path(filename).read_bytes()).hexdigest() == expected_md5, ('BASELINE_CHANGED', filename)
source_file = {source_file!r}
content = Path(source_file).read_bytes()
expected = {expected!r}
actual = hashlib.sha256(content).hexdigest()
assert actual == expected, ('VARIANT_CHANGED_DO_NOT_SUBMIT', actual, expected)
# Archive genuine regenerated blend, then publish the selected variant under the required name.
Path('submission_blend_control.csv').write_bytes(Path('submission.csv').read_bytes())
Path('submission.csv').write_bytes(content)
assert hashlib.sha256(Path('submission.csv').read_bytes()).hexdigest() == expected
proof = dict(tag={'w088-'+name!r}, source_file=source_file, file='submission.csv', sha256=actual,
             expected_sha256=expected, cpu_only=True, full_pipeline=True,
             original_baseline_md5=EXPECTED_BASE, transport_only_change=True)
Path('wave7_ready.json').write_text(json.dumps(proof, indent=2))
print('NAMED_SUBMISSION_VERIFY_PASS', json.dumps(proof), flush=True)
'''
 nb['cells'].append({'cell_type':'code','metadata':{},'execution_count':None,'outputs':[],'source':code.splitlines(keepends=True)})
 (folder/'wave7.ipynb').write_text(json.dumps(nb,ensure_ascii=False,indent=1))
 for k in ['id_no','machine_shape']:metadata.pop(k,None)
 metadata.update(id='victor120956/'+slug,title=slug.replace('-',' '),code_file='wave7.ipynb',enable_gpu=False,enable_tpu=False)
 (folder/'kernel-metadata.json').write_text(json.dumps(metadata,indent=2))
 plans.append(dict(tag='w088-'+name,kernel=metadata['id'],version=1,file='submission.csv',sha256=expected,
                   folder=str(folder),output_dir=str(R/f'probeout_wave7_submit_{name}'),source_file=source_file,
                   decision={'formula':'Promover fórmula só com delta positivo vs W088 blend.',
                             'dedup':'Promover refill só com delta positivo vs W088 blend.',
                             'ours':'Identificar se ranker simulado deve ser referência do próximo build.',
                             'pv':'Identificar se ranker público dispensa mistura no próximo build.'}[name]))
 print('BUILT',metadata['id'],expected)
(R/'wave7_named_plan.json').write_text(json.dumps(plans,ensure_ascii=False,indent=2))

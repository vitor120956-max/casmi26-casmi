#!/usr/bin/env python3
"""Build CPU validation kernel: no early final CSV, no preview fixture assertions."""
import json,pathlib,copy,ast
R=pathlib.Path('/home/user')
base=json.loads((R/'kpush_wave7_cpu/wave7.ipynb').read_text())
meta=json.loads((R/'kpush_wave7_cpu/kernel-metadata.json').read_text())
def code(text):return {'cell_type':'code','metadata':{},'execution_count':None,'outputs':[],'source':text.splitlines(keepends=True)}
nb=copy.deepcopy(base);nb['cells']=[]
nb['cells'].append({'cell_type':'markdown','metadata':{},'source':[
 '# Wave8 — CPU, publicação final única\n',
 'Validação do conserto E020/E021. Regenera train/test; nenhum output upstream ou dataset próprio.\n',
 'Candidato novo: dedup/refill seguido de promoção estável por fórmula (msbuddy top5).\n',
 'Controles antigos são artefatos de regressão local, não autorização para reenvio.\n',
 'Sem hashes fixos do preview ou contagem 400 em produção. O sample desta execução define os IDs.\n']})
nb['cells'].append(code('%%writefile atomic_submission.py\n'+(R/'atomic_submission.py').read_text()))
nb['cells'].append(code('''import os
os.environ['CUDA_VISIBLE_DEVICES']=''
from atomic_submission import AtomicSubmission
publisher=AtomicSubmission('/kaggle/working')
publisher.begin()  # before imports/inference that may fail: no stale fallback remains
VARIANT='formula_dedup'
'''))
# Keep tested scientific engine and attribution/credits; do not keep its publication steps.
for i,c in enumerate(base['cells'][:16]):
 c=copy.deepcopy(c)
 if c['cell_type']=='code':
  c['outputs']=[];c['execution_count']=None
  s=''.join(c['source'])
  if i==13:
   s='\n'.join(line for line in s.splitlines() if '.to_csv(' not in line)+'\n'
  c['source']=s.splitlines(keepends=True)
 if i==0:continue  # obsolete title with hash assertions
 nb['cells'].append(c)
# Exact msbuddy setup/method previously used; only runtime contracts and publication change.
formula=''.join(base['cells'][17]['source'])
formula=formula[:formula.index('assert len(buddy_formulas) == 400')]
nb['cells'].append(code(formula+'''
samp=pd.read_csv(os.path.join(COMP,'sample_submission.csv'), dtype={'molecule_id':str})
sample_ids=samp.molecule_id.tolist()
if len(buddy_formulas)!=len(mols):raise ValueError('FORMULA_ID_COUNT_MISMATCH')
if {str(k) for k in buddy_formulas}!=set(sample_ids):raise ValueError('FORMULA_IDS_DIFFER_FROM_SAMPLE')
coverage=sum(bool(x) for x in buddy_formulas.values()) / max(1,len(mols))
if coverage < 0.975:raise ValueError(('MSBUDDY_COVERAGE_FAILED',coverage))
def formula_order(sub):
    result=sub.copy(); changed=0
    for idx,row in result.iterrows():
        base=row.smiles.split(';')
        formulas=set(buddy_formulas.get(row.molecule_id,[])[:5])
        order=sorted(range(len(base)),key=lambda j:(_calc_f(base[j]) not in formulas,j)) if formulas else list(range(len(base)))
        out=[base[j] for j in order]
        if sorted(out)!=sorted(base):raise ValueError('FORMULA_CHANGED_MEMBERSHIP')
        changed+=out!=base
        result.at[idx,'smiles']=';'.join(out)
    return result,changed
formula_sub,f_changed=formula_order(subs['blend'])
'''))
dedup=''.join(base['cells'][18]['source'])
dedup=dedup.replace("assert d_changed > 0, 'DEDUP_NOOP_DO_NOT_SUBMIT'", "# Zero change is legitimate for other inputs; preview no-op is checked outside runtime.")
dedup='\n'.join(l for l in dedup.splitlines() if '.to_csv(' not in l)+'\n'
nb['cells'].append(code(dedup))
nb['cells'].append(code('''import hashlib,json
from pathlib import Path
combo_sub,combo_formula_changed=formula_order(dedup_sub)
variants=dict(blend=subs['blend'],ours=subs['ours'],pv=subs['pv'],formula=formula_sub,dedup=dedup_sub,formula_dedup=combo_sub)
@lru_cache(maxsize=None)
def valid_smiles(s):return Chem.MolFromSmiles(s) is not None

def file_sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()

proof=dict(variant=VARIANT,cpu_only=True,full_pipeline=True,own_dataset_inputs=False,
           expected_rows=len(sample_ids),formula_coverage=coverage,
           formula_changed_rows=int(f_changed),dedup_changed_rows=int(d_changed),
           dedup_replaced_slots=int(d_replaced),combo_formula_changed_rows=int(combo_formula_changed),
           test_sha256=file_sha(os.path.join(COMP,'test.parquet')),
           sample_sha256=file_sha(os.path.join(COMP,'sample_submission.csv')),
           rdkit_version=rdkit.__version__,artifacts={})
records={}
for name,sub in variants.items():
    raw_records=sub.to_dict('records')
    clean,_=AtomicSubmission.validate(raw_records,sample_ids,valid_smiles)
    records[name]=clean
    # Diagnostic/preview artifacts, never the eligible final name.
    data=sub.to_csv(index=False).encode('utf-8')
    artifact='audit_'+name+'.csv'
    Path(artifact).write_bytes(data)
    proof['artifacts'][name]=dict(file=artifact,sha256=hashlib.sha256(data).hexdigest(),bytes=len(data),rows=len(clean))
proof['combo_vs_blend_changed_rows']=int(sum(a['smiles']!=b['smiles'] for a,b in zip(records[VARIANT],records['blend'])))
Path('lineage_before_publish.json').write_text(json.dumps(proof,indent=2))
print('PREPUBLICATION_VALIDATED', json.dumps(proof),flush=True)
'''))
nb['cells'].append(code('''# Last computational cell. No baseline ever written under the eligible filename.
publication=publisher.publish(records[VARIANT],sample_ids,valid_smiles,proof)
print('ATOMIC_PUBLICATION_COMPLETE',json.dumps(publication),flush=True)
'''))
# Reject any accidental regression before writing kernel files.
text='\n'.join(''.join(c['source']) for c in nb['cells'] if c['cell_type']=='code')
for token in ['W088_REPRODUCTION_FAILED','BASELINE_CHANGED','VARIANT_CHANGED_DO_NOT_SUBMIT','== 400','>= 390']:
 if token in text:raise ValueError(('FORBIDDEN_PREVIEW_CONTRACT',token))
for c in nb['cells']:
 if c['cell_type']=='code':
  s=''.join(c['source']);s=s.split('\n',1)[1] if s.startswith('%%writefile ') else s;ast.parse(s)
folder=R/'kpush_wave8_atomic_combo_cpu';folder.mkdir(exist_ok=True)
meta.update(id='victor120956/casmi26-wave8-atomic-formula-dedup-cpu',title='casmi26 wave8 atomic formula dedup cpu',code_file='wave8.ipynb',enable_gpu=False,enable_tpu=False)
for k in ['id_no','machine_shape']:meta.pop(k,None)
(folder/'wave8.ipynb').write_text(json.dumps(nb,ensure_ascii=False,indent=1))
(folder/'kernel-metadata.json').write_text(json.dumps(meta,indent=2))
print('BUILT',meta['id'],'variant=formula_dedup; no automatic submission')

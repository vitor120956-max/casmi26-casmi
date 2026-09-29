#!/usr/bin/env python3
import copy,json,pathlib
R=pathlib.Path('/home/user');source=R/'kpush_wave8_atomic_combo_cpu'
original=json.loads((source/'wave8.ipynb').read_text());meta0=json.loads((source/'kernel-metadata.json').read_text())
def cell(s):return {'cell_type':'code','metadata':{},'execution_count':None,'outputs':[],'source':s.splitlines(keepends=True)}
settings={
 'top1':('top1','Top1 msbuddy reduz promoções espúrias em relação à evidência top5?','Comparar ao W088 blend e ao top1+dedup; promover somente ganho confiável.'),
 'top1_dedup':('top1-dedup','Top1 aplicado após refill supera o combinado top5+dedup?','Escolher política top1/top5 após notas atribuíveis, sem varrer pesos.'),
 'adduct':('adduct','Separar espectros por aduto/polaridade melhora a fórmula e o ranking?','Se ganhar, adotar evidência por grupo; sem ganho, não promover.'),
 'adduct_dedup':('adduct-dedup','Evidência por aduto também melhora a combinação com refill?','Comparar com adduct sem refill e combinado top5 legado; escolher mecanismo demonstrado.')}
plans=[]
for variant,(suffix,question,decision) in settings.items():
 nb=copy.deepcopy(original)
 for c in nb['cells']:
  if c['cell_type']!='code':continue
  c['outputs']=[];c['execution_count']=None;s=''.join(c['source'])
  s=s.replace("VARIANT='formula_dedup'",f'VARIANT={variant!r}')
  s=s.replace('def formula_order(sub):','def formula_order(sub, formulas_by_id=None, topk=5):\n    if formulas_by_id is None: formulas_by_id=buddy_formulas')
  s=s.replace("formulas=set(buddy_formulas.get(row.molecule_id,[])[:5])", "formulas=set(formulas_by_id.get(row.molecule_id,formulas_by_id.get(str(row.molecule_id),[]))[:topk])")
  if 'variants=dict(' in s:
   marker='@lru_cache(maxsize=None)\ndef valid_smiles'
   extra="top1_sub,top1_changed=formula_order(subs['blend'],topk=1)\ntop1_dedup_sub,top1_dedup_changed=formula_order(dedup_sub,topk=1)\nvariants.update(top1=top1_sub,top1_dedup=top1_dedup_sub)\n"
   if variant.startswith('adduct'):
    extra+="adduct_sub,adduct_changed=formula_order(subs['blend'],adduct_formulas)\nadduct_dedup_sub,adduct_dedup_changed=formula_order(dedup_sub,adduct_formulas)\nvariants.update(adduct=adduct_sub,adduct_dedup=adduct_dedup_sub)\n"
   s=s.replace(marker,extra+marker)
   if variant.startswith('adduct'):
    s=s.replace('records={}',"proof.update(adduct_group_count=len(adduct_groups),adduct_formula_coverage=adduct_coverage,adduct_changed_rows=int(adduct_changed),adduct_dedup_changed_rows=int(adduct_dedup_changed))\nrecords={}")
   s=s.replace("'combo_vs_blend_changed_rows'","'selected_vs_blend_changed_rows'")
  c['source']=s.splitlines(keepends=True)
 if variant.startswith('adduct'):
  nb['cells'].insert(2,cell('%%writefile formula_evidence.py\n'+(R/'formula_evidence.py').read_text()))
  nb['cells'].insert(-2,cell('''from formula_evidence import split_spectra,combine_formula_evidence
adduct_groups=split_spectra(te.to_dict('records'))
adduct_features=[]
for i,g in enumerate(adduct_groups):
    adduct_features.append(MetaFeature(identifier=i,mz=g['precursor_mz'],charge=g['charge'],adduct=g['adduct'],
                          ms2=Spectrum(mz_array=np.asarray(g['ms2_mzs'],float),int_array=np.asarray(g['ms2_normalized_intensities'],float))))
del _eng
adduct_engine=Msbuddy(_cfg)
adduct_engine.add_data(adduct_features);adduct_engine.annotate_formula()
adduct_summary=adduct_engine.get_summary()
if len(adduct_summary)!=len(adduct_groups):raise ValueError('ADDUCT_SUMMARY_COUNT')
formula_groups=[]
for g,res in zip(adduct_groups,adduct_summary):
    values=[res.get(f'formula_rank_{k}') for k in range(1,6)]
    formula_groups.append(dict(molecule_id=g['molecule_id'],adduct=g['adduct'],mode=g['mode'],
                               formulas=[str(f).replace(' ','').rstrip('+-') for f in values if f]))
adduct_formulas=combine_formula_evidence(formula_groups)
if set(adduct_formulas)!=set(sample_ids):raise ValueError('ADDUCT_FORMULA_IDS')
adduct_coverage=sum(bool(x) for x in adduct_formulas.values())/max(1,len(sample_ids))
if adduct_coverage<0.975:raise ValueError(('ADDUCT_FORMULA_COVERAGE',adduct_coverage))
from pathlib import Path
import json
Path('formula_adducts.json').write_text(json.dumps(adduct_formulas,indent=2))
print('ADDUCT_EVIDENCE_READY',len(adduct_groups),adduct_coverage,flush=True)
'''))
 nb['cells'][0]['source']=[f'# Wave8 atomic CPU: {variant}\n',question+'\n',decision+'\n','Um único arquivo final após toda validação; controles auxiliares não são novos submits.\n']
 folder=R/f'kpush_wave8_{variant}';folder.mkdir(exist_ok=True)
 m=copy.deepcopy(meta0);slug=f'casmi26-wave8-atomic-{suffix}-cpu'
 m.update(id='victor120956/'+slug,title=slug.replace('-',' '))
 (folder/'wave8.ipynb').write_text(json.dumps(nb,ensure_ascii=False,indent=1));(folder/'kernel-metadata.json').write_text(json.dumps(m,indent=2))
 plans.append(dict(tag=variant,kernel=m['id'],version=1,file='submission.csv',folder=str(folder),question=question,decision=decision,preview_verified=False,no_automatic_submission=True))
 print('BUILT',m['id'])
(R/'wave8_extra_plan.json').write_text(json.dumps(plans,ensure_ascii=False,indent=2))

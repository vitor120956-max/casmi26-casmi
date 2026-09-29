#!/usr/bin/env python3
"""One-shot official results check for Wave8. No polling or submissions."""
import datetime as dt,json,pathlib,argparse
from wave8_report_logic import next_step
import wave7_run as w
from safety_guards import classify_submission,score_attribution_warnings
parser=argparse.ArgumentParser()
parser.add_argument('--snapshot', help='Render saved evidence only; no API call')
parser.add_argument('--baseline',type=float,help='Previously confirmed baseline for cached rendering')
args=parser.parse_args()
R=w.ROOT
if args.snapshot:
 snapshot=json.loads(pathlib.Path(args.snapshot).read_text())
 subs=snapshot['submissions'];quota=snapshot['quota']
else:
 api=w.connect()
 subs=[w.obj(s) for s in api.competition_submissions(w.COMP,page_size=100)]
 quota=w.obj(api.competition_get_submission_limits(w.COMP))
 snapshot={'at':dt.datetime.now(w.BRT).isoformat(),'quota':quota}
wave=[s for s in subs if (s.get('description') or '').startswith('PROBE-WAVE8:')]
if not args.snapshot:
 snapshot['submissions']=wave
 w.dump('wave8_after_send.json',snapshot)
state=json.loads((R/'wave8_submit_state.json').read_text()) if (R/'wave8_submit_state.json').exists() else {}
footprints={}
for tag,e in state.items():
 p=e.get('plan',{});file=pathlib.Path(p.get('path',''))
 if file.is_file():footprints[tag]={'local_bytes':file.stat().st_size,'sha256':p.get('sha256')}
warning=score_attribution_warnings(wave,footprints)
scores={s['description'].split(':',1)[1].split(' ')[0]:float(s['publicScore']) for s in wave if classify_submission(s)=='RANQUEADA'}
base=args.baseline if args.snapshot else next((float(s['publicScore']) for s in subs if s['ref']==56592387 and classify_submission(s)=='RANQUEADA'),None)
lines=['# Wave8 — consulta pontual', '', 'Evidência consultada em: '+snapshot['at']+(' (renderização offline)' if args.snapshot else ''), '', f"Quota disponível: {quota['numAllowedNow']}; usados hoje: {quota['numToday']}; total: {quota['numTotal']}.",f'Notas confirmadas: {len(scores)}/5. W088 blend de referência: {base}.','', '| Variante | Ref | Estado | Nota |','|---|---:|---|---:|']
errors=[]
for s in wave:
 tag=s['description'].split(':',1)[1].split(' ')[0]
 lines.append(f"| {tag} | {s['ref']} | {classify_submission(s)} ({s['status']}) | {s.get('publicScore') or '—'} |")
 if s.get('errorDescription'):errors.append(f"Erro ref {s['ref']}: {s['errorDescription']}")
lines+=['']+errors
if warning:lines+=['','ALERTA DE ATRIBUIÇÃO: '+', '.join(warning),'Não promover/eliminar mecanismos pelo aparente empate. Metadados não provam duplicação nem bug do avaliador.']
elif len(scores)==5 and base is not None:
 winner=max(scores,key=scores.get);delta=scores[winner]-base
 lines+=['',f'Melhor Wave8: {winner} = {scores[winner]:.3f}; delta vs W088 {delta:+.3f}.', 'Promover provisoriamente a configuração vencedora, sem alegar significância estatística.' if delta>0 else 'Nenhum ganho demonstrado sobre W088; manter referência.']
 for a,b,label in [('top1_dedup','formula_dedup','seletividade top1 vs top5 com refill constante'),('adduct_dedup','formula_dedup','agrupamento por aduto com refill constante'),('adduct_dedup','adduct','efeito do refill sob evidência por aduto'),('top1_dedup','top1','efeito do refill sob fórmula top1')]:
  lines.append(f'{label}: {scores[a]-scores[b]:+.3f} ({a} menos {b}).')
else:lines+=['',next_step(wave)]
(R/'WAVE8_RESULTADO.md').write_text('\n'.join(lines)+'\n')
w.log(('WAVE8_RENDER_CACHED ' if args.snapshot else 'WAVE8_SCORE_CHECK_ONCE ')+json.dumps({'scores':scores,'quota':quota,'attribution_warnings':warning}))
print('\n'.join(lines))

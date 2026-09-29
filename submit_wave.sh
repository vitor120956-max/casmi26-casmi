#!/bin/bash
# submit_wave.sh — submete as 5 probes automaticamente às 00:00:30 UTC (21:00 BRT) + vigia scores.
# IDEMPOTENTE: wave_submitted.txt = fonte de verdade (nunca double-submit). Auto-cura: re-baixa output ausente.
# Uso: bash submit_wave.sh        (espera o reset das 00:00 UTC)
#      bash submit_wave.sh now    (submete já — usar se religado DEPOIS das 00:00 UTC)
export PATH="$HOME/.local/bin:$PATH"
cd /home/user
LOG=/home/user/day_watch.log
SUBBED=/home/user/wave_submitted.txt
touch $SUBBED
log(){ echo "[$(date -u +%FT%TZ)] $1" >> $LOG; }
allowed_now(){
python3 - <<'PY' 2>/dev/null | tail -1
from kaggle.api.kaggle_api_extended import KaggleApi
api=KaggleApi(); api.authenticate()
r=api.competition_get_submission_limits('enveda-CASMI26-molecule-id-mass-spectra')
v=None
for a in ('numAllowedNow','num_allowed_now'):
    v=getattr(r,a,None)
    if v is not None: break
if v is None:
    for k in ('numAllowedNow','num_allowed_now'):
        try: v=r[k]; break
        except Exception: pass
print(int(v) if v is not None else -1)
PY
}
# dir|slug|kver|tag|msg   (ordem = prioridade)
PROBES=(
"probeout_haideptry|casmi26-haideptry-0339-probe|1|haideptry|PROBE-WAVE1:haideptry — replication of 0.339 claim (channel transformer analog ensemble)"
"probeout_berat|casmi26-berat-sota-probe|1|berat|PROBE-WAVE1:berat — replication of 0.341 claim (SOTA quad-channel GBM)"
"probeout_megayak2|casmi26-megayak-engine-probe2|3|megayak2|PROBE-WAVE1:megayak2 — two-rankers-one-engine as-is (0.337 blend claim)"
"probeout_seedswap2|casmi26-seedswap-probe2|3|seedswap2|PROBE-WAVE1:seedswap2 — 0.328 config with SEEDS 4-7 (seed sensitivity)"
"probeout_priors2|casmi26-priors-high-probe2|2|priors2|PROBE-WAVE1:priors2 — 0.328 config with priors 0.55/0.65/0.75"
)
log "wave: START ($(grep -c PROBE-WAVE1 $SUBBED) já submetidas)"
if [ "${1:-}" != "now" ] && [ "$(grep -c PROBE-WAVE1 $SUBBED)" -eq 0 ]; then
  while true; do
    now=$(date -u +%s); target=$(date -u -d "today 00:00:30" +%s)
    [ $now -ge $target ] && target=$(date -u -d "tomorrow 00:00:30" +%s)
    d=$((target-now)); [ $d -le 0 ] && break
    log "wave: aguardando reset — faltam $((d/60)) min"
    s=$((d<1800?d:1800)); sleep $s
  done
  log "wave: RESET ATINGIDO — iniciando submissões"
fi
# auto-cura pós-restart: kaggle pode ter sido limpo do sandbox durante a espera
python3 -c "import kaggle" 2>/dev/null || { log "wave: kaggle ausente — pip install"; pip install -q kaggle >> $LOG 2>&1; }
chmod 600 ~/.kaggle/kaggle.json 2>/dev/null
ls /home/user/verify_out.sh >/dev/null 2>&1 || log "wave: ALERTA — verify_out.sh sumiu do sandbox! Restaurar do git antes de submeter (ondas pulam tudo sem ele... na verdade sem verify as probes são PULADAS = onda vazia)"
for entry in "${PROBES[@]}"; do
  IFS='|' read -r dir slug kver tag msg <<< "$entry"
  if grep -q "PROBE-WAVE1:$tag" $SUBBED; then log "wave: $tag já submetida — skip"; continue; fi
  if [ ! -f "/home/user/$dir/submission.csv" ]; then
    mkdir -p "/home/user/$dir"
    timeout 300 kaggle kernels output victor120956/$slug -p "/home/user/$dir" >> $LOG 2>&1
    log "wave: $tag — output re-baixado (auto-cura)"
  fi
  if ! bash verify_out.sh "/home/user/$dir" > /tmp/v_$tag.txt 2>&1; then
    log "wave: $tag VERIFY FAIL — FORA DA ONDA. ($(tail -1 /tmp/v_$tag.txt))"; continue
  fi
  a=0; tries=0
  while true; do
    a=$(allowed_now)
    [ "${a:-0}" -ge 1 ] 2>/dev/null && break
    tries=$((tries+1)); [ $tries -ge 10 ] && break
    log "wave: slots indisponíveis ($a) — tentativa $tries/10, 60s"; sleep 60
  done
  if [ "${a:-0}" -lt 1 ] 2>/dev/null; then log "wave: SEM SLOTS após 10 tentativas — abortando onda"; break; fi
  res=$(python3 - "$dir" "$msg" "$slug" "$kver" <<'PY' 2>&1
import os, sys
d, msg, slug, kver = sys.argv[1:5]
from kaggle.api.kaggle_api_extended import KaggleApi
api = KaggleApi(); api.authenticate()
os.chdir('/home/user/'+d)
try:
    api.competition_submit_code('submission.csv', msg, 'enveda-CASMI26-molecule-id-mass-spectra', kernel='victor120956/'+slug, kernel_version=int(kver))
    print('SUBMIT-OK')
except Exception as e:
    print('SUBMIT-FAIL:', repr(e)[:300])
PY
)
  echo "$res" | tr '\n' ' ' | sed "s/^/wave: $tag → /" | while read -r l; do log "$l"; done
  if echo "$res" | grep -q "SUBMIT-OK"; then
    echo "PROBE-WAVE1:$tag|$(date -u +%FT%TZ)|$slug v$kver" >> $SUBBED
    log "wave: $tag SUBMETIDA ✓ (registrada em wave_submitted.txt)"
  else
    log "wave: $tag FALHOU na submissão (400 não consome slot)"
  fi
  sleep 45
done
log "wave: fase de submissão encerrada — polling de scores (máx 2h) em wave_scores.log"
end=$(( $(date -u +%s) + 7200 ))
while [ $(date -u +%s) -lt $end ]; do
  out=$(python3 - <<'PY' 2>/dev/null
from kaggle.api.kaggle_api_extended import KaggleApi
api=KaggleApi(); api.authenticate()
subs=api.competition_submissions('enveda-CASMI26-molecule-id-mass-spectra')
pend=0; lines=[]
for s in subs[:10]:
    d=(s.description or '')
    if 'PROBE-WAVE1' in d:
        sc=getattr(s,'public_score','') or ''
        st=str(getattr(s,'status','')).split('.')[-1]
        tag=d.split(':')[1].split(' ')[0]
        lines.append(f"{tag} | {s.ref} | {st} | {sc}")
        if st!='COMPLETE': pend+=1
print('\n'.join(lines)); print('PENDING='+str(pend))
PY
)
  { echo "[$(date -u +%FT%TZ)] === poll ==="; echo "$out"; } >> /home/user/wave_scores.log
  p=$(echo "$out" | grep -o "PENDING=[0-9]*" | cut -d= -f2)
  n=$(echo "$out" | grep -c " | ")
  log "wave: poll — $n submissões da onda vistas, pending=$p"
  if [ "${p:-9}" = "0" ] && [ "${n:-0}" -ge "$(grep -c PROBE-WAVE1 $SUBBED)" ] && [ "$(grep -c PROBE-WAVE1 $SUBBED)" -ge 1 ]; then
    log "wave: ★ SCORES COMPLETOS — ver wave_scores.log ★"; break
  fi
  sleep 300
done
log "wave: FIM"

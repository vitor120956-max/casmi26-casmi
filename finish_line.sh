#!/bin/bash
# finish_line.sh v2 — resumível + protocolo de verificação embutido.
# 1) aguarda PAR1 (seedswap2 v3 + megayak2 v3, pushados LIMPOS 16:23:45Z) -> baixa -> verify_out
# 2) precheck kpush_priors2 -> push v3 -> aguarda -> baixa -> verify_out
export PATH="$HOME/.local/bin:$PATH"
cd /home/user
LOG=/home/user/day_watch.log
K=victor120956
log(){ echo "[$(date -u +%FT%TZ)] $1" >> $LOG; }
wait_done(){
  while true; do
    st=$(timeout 45 kaggle kernels status $K/$1 2>&1 | tail -1)
    case "$st" in
      *omplete*) echo COMPLETE; return;;
      *rror*) echo ERROR; return;;
      *) sleep 120;;
    esac
  done
}
dl_verify(){ # slug outdir
  mkdir -p "/home/user/$2"
  (cd "/home/user/$2" && timeout 300 kaggle kernels output $K/$1 . >> $LOG 2>&1)
  v=$(bash /home/user/verify_out.sh "/home/user/$2" 2>&1 | tail -1)
  log "finish: $1 → $2 | $v"
}
log "finish v2: START (resume; protocolo precheck+verify embutido)"
s1=$(wait_done casmi26-seedswap-probe2); log "finish: seedswap2 → $s1"; dl_verify casmi26-seedswap-probe2 probeout_seedswap2
s2=$(wait_done casmi26-megayak-engine-probe2); log "finish: megayak2 → $s2"; dl_verify casmi26-megayak-engine-probe2 probeout_megayak2
sleep 120
if bash /home/user/precheck.sh kpush_priors2 >> $LOG 2>&1; then
  out=$(cd kpush_priors2 && timeout 300 kaggle kernels push -p . 2>&1 | tr '\n' ' ')
  if echo "$out" | grep -qi "not valid competition sources\|error"; then
    log "finish: priors2 push FALHOU (warning/erro no output): $out — NÃO re-pushar sem investigação"
  else
    log "finish: priors2 v3 PUSH LIMPO ✓ — $out"
    s3=$(wait_done casmi26-priors-high-probe2); log "finish: priors2 → $s3"; dl_verify casmi26-priors-high-probe2 probeout_priors2
  fi
else
  log "finish: priors2 PRECHECK FAIL — push abortado pelo protocolo"
fi
log "finish v2: FIM — prontas p/ 21:00 BRT (5 slots): haideptry, berat, megayak2, seedswap2, priors2"

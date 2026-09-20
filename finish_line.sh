#!/bin/bash
# finish_line.sh — aguarda PAR1 (seedswap2 v3 + megayak2 v3), baixa+verifica, pusha priors2 v3, baixa+verifica.
export PATH="$HOME/.local/bin:$PATH"
cd /home/user
LOG=/home/user/day_watch.log
K=victor120956
log(){ echo "[$(date -u +%FT%TZ)] $1" >> $LOG; }
wait_done(){
  while true; do
    st=$(timeout 45 kaggle kernels status $K/$1 2>&1 | head -1)
    case "$st" in
      *omplete*) echo COMPLETE; return;;
      *rror*) echo ERROR; return;;
      *) sleep 120;;
    esac
  done
}
dl(){
  mkdir -p "/home/user/$2"
  (cd "/home/user/$2" && timeout 300 kaggle kernels output $K/$1 . >> $LOG 2>&1)
  if [ -f "/home/user/$2/submission.csv" ]; then
    log "finish: $1 → $2 submission.csv $(wc -l < /home/user/$2/submission.csv) linhas"
    if grep -qi traceback /home/user/$2/*.log 2>/dev/null; then log "finish: $1 TEM Traceback no log!"; else log "finish: $1 log sem Traceback ✓"; fi
  else
    log "finish: $1 → $2 SEM submission.csv (run falhou)"
  fi
}
log "finish: START — PAR1 v3 pushado 16:23Z LIMPO (typo envida→enveda corrigido)"
s1=$(wait_done casmi26-seedswap-probe2); log "finish: seedswap2 → $s1"; dl casmi26-seedswap-probe2 probeout_seedswap2
s2=$(wait_done casmi26-megayak-engine-probe2); log "finish: megayak2 → $s2"; dl casmi26-megayak-engine-probe2 probeout_megayak2
sleep 120
log "finish: pushando priors2 v3"
(cd kpush_priors2 && timeout 300 kaggle kernels push -p . 2>&1 | tr '\n' ' ' | sed 's/^/finish: priors2 push → /' >> $LOG)
s3=$(wait_done casmi26-priors-high-probe2); log "finish: priors2 → $s3"; dl casmi26-priors-high-probe2 probeout_priors2
log "finish: FIM — prontas p/ 21:00 BRT: haideptry, berat, megayak2, seedswap2, priors2"

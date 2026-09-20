#!/bin/bash
# probe_factory.sh — TEORIA V2: push só com pool GPU 100% quiescente.
# Ordem: buffer quiescente -> PAR1 (seedswap2 v2 + megayak2 v2) -> espera ambos -> priors2 v2 -> downloads+verifica.
export PATH="$HOME/.local/bin:$PATH"
cd /home/user
LOG=/home/user/day_watch.log
K=victor120956
SLUGS="casmi26-seedswap-probe2 casmi26-megayak-engine-probe2 casmi26-priors-high-probe2 casmi26-hello-test casmi26-berat-sota-probe casmi26-haideptry-0339-probe casmi26-seedswap-probe casmi26-megayak-engine-probe casmi26-priors-high-probe"
log(){ echo "[$(date -u +%FT%TZ)] $1" >> $LOG; }
quiescent(){
  for s in $SLUGS; do
    st=$(timeout 45 kaggle kernels status $K/$s 2>/dev/null | head -1)
    case "$st" in *[Rr]unning*|*[Qq]ueue*|*[Ww]aiting*|*[Pp]ending*) return 1;; esac
  done
  return 0
}
wait_quiet(){
  while true; do
    if quiescent; then log "factory: pool QUIESCENTE — buffer 240s antes do push"; sleep 240; return 0; fi
    sleep 90
  done
}
push_one(){
  d=$1; s=$2
  out=$(cd "$d" && timeout 300 kaggle kernels push -p . 2>&1 | tr '\n' ' ')
  if echo "$out" | grep -qi "not valid competition sources"; then
    log "factory: $s v2 PUSH COM WARNING MESMO COM POOL LIVRE — TEORIA V2 REFUTADA. Raw: $out"; return 1
  elif echo "$out" | grep -qi "Maximum batch GPU"; then
    log "factory: $s bloqueado GPU-limit (pool não estava livre de verdade); retry em 300s"
    sleep 300; out=$(cd "$d" && timeout 300 kaggle kernels push -p . 2>&1 | tr '\n' ' ')
    if echo "$out" | grep -qi "not valid competition sources"; then log "factory: $s retry WARNING — TEORIA V2 REFUTADA"; return 1; fi
    log "factory: $s retry: $out"; return 0
  else
    log "factory: $s v2 PUSH LIMPO ✓ — $out"; return 0
  fi
}
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
    log "factory: $1 → $2 submission.csv $(wc -l < /home/user/$2/submission.csv) linhas"
    grep -qi traceback "/home/user/$2/"*.log 2>/dev/null && log "factory: $1 TEM Traceback no log!" || log "factory: $1 log sem Traceback ✓"
  else
    log "factory: $1 → $2 SEM submission.csv (run falhou)"
  fi
}
log "factory: START (teoria v2 = capacidade de sessão no momento do push)"
wait_quiet
push_one kpush_seedswap2 casmi26-seedswap-probe2; r1=$?
push_one kpush_megayak2 casmi26-megayak-engine-probe2; r2=$?
if [ $r1 -eq 1 ] && [ $r2 -eq 1 ]; then log "factory: PAR1 todo com warning — PARANDO p/ investigação manual"; exit 1; fi
s1=$(wait_done casmi26-seedswap-probe2); log "factory: seedswap2 → $s1"; dl casmi26-seedswap-probe2 probeout_seedswap2
s2=$(wait_done casmi26-megayak-engine-probe2); log "factory: megayak2 → $s2"; dl casmi26-megayak-engine-probe2 probeout_megayak2
wait_quiet
push_one kpush_priors2 casmi26-priors-high-probe2
s3=$(wait_done casmi26-priors-high-probe2); log "factory: priors2 → $s3"; dl casmi26-priors-high-probe2 probeout_priors2
log "factory: FIM — ver probeout_*2/ e submeter 21:00 BRT"

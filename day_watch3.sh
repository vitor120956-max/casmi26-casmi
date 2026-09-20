#!/bin/bash
# day_watch3.sh — vigia as 3 probes de slug novo
export PATH="$HOME/.local/bin:$PATH"
LOG=/home/user/day_watch.log
echo "[$(date -u +%FT%TZ)] watch3 armado" >> $LOG
declare -A DIRS
DIRS[casmi26-seedswap-probe2]=/home/user/probeout_seedswap2
DIRS[casmi26-megayak-engine-probe2]=/home/user/probeout_megayak2
DIRS[casmi26-priors-high-probe2]=/home/user/probeout_priors2
declare -A DONE
for s in "${!DIRS[@]}"; do DONE[$s]=0; done
verify() {
  python3 - "$1" <<'PYEOF' >> /home/user/day_watch.log 2>&1
import pandas as pd, glob, os, re, sys
d = sys.argv[1]
try:
    sub = pd.read_csv(os.path.join(d, 'submission.csv'))
    print(f'CSV {d}: {sub.shape[0]} linhas, nulls={int(sub.isnull().sum().sum())}, CCO={int((sub.iloc[:,1]=="CCO").sum())}')
except Exception as e:
    print(f'CSV {d}: FALHOU: {e}')
lg = glob.glob(os.path.join(d, '*.log'))
if lg:
    txt = open(lg[0], errors='ignore').read()
    if 'Traceback' in txt: print('ALERTA: Traceback!')
    for m in re.findall(r'(candidate pool[^\\"]{5,70}|fingerprint models?:[^\\"]{5,60}|ranker: [0-9]+ GBMs[^\\"]{0,40}|SEED-SWAP[^\\"]{0,50}|fp models:[^\\"]{0,60}|blend[^\\"]{5,70}|INPUTS:[^\\"]{0,80})', txt)[:8]:
        print('HOOK:', m.strip()[:110])
PYEOF
}
while true; do
  all=1
  for s in "${!DIRS[@]}"; do
    [ "${DONE[$s]}" = "1" ] && continue
    all=0
    st=$(kaggle kernels status victor120956/$s 2>&1)
    case "$st" in
      *404*|*"Not Found"*|*"Cannot access"*) echo "[$(date -u +%FT%TZ)] $s: ainda não pushado" >> $LOG; continue ;;
      *COMPLETE*) echo "[$(date -u +%FT%TZ)] $s: COMPLETE" >> $LOG; mkdir -p "${DIRS[$s]}"; kaggle kernels output victor120956/$s -p "${DIRS[$s]}" >> $LOG 2>&1; verify "${DIRS[$s]}"; DONE[$s]=1 ;;
      *ERROR*) echo "[$(date -u +%FT%TZ)] $s: ERROR" >> $LOG; mkdir -p "${DIRS[$s]}"; kaggle kernels output victor120956/$s -p "${DIRS[$s]}" >> $LOG 2>&1; verify "${DIRS[$s]}"; DONE[$s]=1 ;;
      *) echo "[$(date -u +%FT%TZ)] $s: $st" >> $LOG ;;
    esac
  done
  [ $all = 1 ] && { echo "[$(date -u +%FT%TZ)] watch3: tudo resolvido" >> $LOG; break; }
  sleep 300
done

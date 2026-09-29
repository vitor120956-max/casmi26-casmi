#!/bin/bash
# day_watch2.sh — vigia TODAS as 5 probes do dia; guarda 404 (kernel ainda não pushado)
export PATH="$HOME/.local/bin:$PATH"
LOG=/home/user/day_watch.log
echo "[$(date -u +%FT%TZ)] watch2 armado (5 kernels)" >> $LOG

declare -A DIRS
DIRS[casmi26-berat-sota-probe]=/home/user/probeout_berat
DIRS[casmi26-haideptry-0339-probe]=/home/user/probeout_haideptry
DIRS[casmi26-priors-high-probe]=/home/user/probeout_priors
DIRS[casmi26-megayak-engine-probe]=/home/user/probeout_megayak
DIRS[casmi26-seedswap-probe]=/home/user/probeout_seedswap
declare -A DONE
for s in "${!DIRS[@]}"; do DONE[$s]=0; done

verify() {
  python3 - "$1" <<'PYEOF' >> /home/user/day_watch.log 2>&1
import pandas as pd, glob, os, re, sys
d = sys.argv[1]
try:
    sub = pd.read_csv(os.path.join(d, 'submission.csv'))
    n = sub.shape[0]; cols = list(sub.columns)
    nulls = int(sub.isnull().sum().sum())
    cco = int((sub.iloc[:, 1] == 'CCO').sum()) if len(cols) > 1 else -1
    print(f'CSV {d}: {n} linhas cols={cols} nulls={nulls} CCO={cco}')
except Exception as e:
    print(f'CSV {d}: FALHOU: {e}')
lg = glob.glob(os.path.join(d, '*.log'))
if lg:
    txt = open(lg[0], errors='ignore').read()
    if 'Traceback' in txt: print('ALERTA: Traceback no log!')
    for m in re.findall(r'(candidate pool: [^\\"]{5,80}|fingerprint models?: [^\\"]{5,60}|ranker: [0-9]+ GBMs[^\\"]{0,40}|fp models: [^\\"]{0,60}|RRF[^\\"]{5,80}|SEED-SWAP[^\\"]{0,60}|submission written[^\\"]{0,60}|blend[^\\"]{5,80})', txt)[:8]:
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
      *404*|*"Not Found"*) echo "[$(date -u +%FT%TZ)] $s: ainda não existe (fila GPU)" >> $LOG; continue ;;
      *COMPLETE*)
        echo "[$(date -u +%FT%TZ)] $s: COMPLETE — baixando" >> $LOG
        mkdir -p "${DIRS[$s]}"
        kaggle kernels output victor120956/$s -p "${DIRS[$s]}" >> $LOG 2>&1
        verify "${DIRS[$s]}"
        DONE[$s]=1 ;;
      *ERROR*)
        echo "[$(date -u +%FT%TZ)] $s: ERROR — baixando log" >> $LOG
        mkdir -p "${DIRS[$s]}"
        kaggle kernels output victor120956/$s -p "${DIRS[$s]}" >> $LOG 2>&1
        verify "${DIRS[$s]}"
        DONE[$s]=1 ;;
      *) echo "[$(date -u +%FT%TZ)] $s: $st" >> $LOG ;;
    esac
  done
  if [ $all = 1 ]; then echo "[$(date -u +%FT%TZ)] watch2: tudo resolvido, encerrando" >> $LOG; break; fi
  sleep 300
done

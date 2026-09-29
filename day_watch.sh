#!/bin/bash
# day_watch.sh — vigia as probes do dia; baixa+verifica output quando COMPLETE; loga tudo
export PATH="$HOME/.local/bin:$PATH"
LOG=/home/user/day_watch.log
echo "[$(date -u +%FT%TZ)] watcher armado: berat + haideptry + priors" >> $LOG

declare -A DIRS
DIRS[casmi26-berat-sota-probe]=/home/user/probeout_berat
DIRS[casmi26-haideptry-0339-probe]=/home/user/probeout_haideptry
DIRS[casmi26-priors-high-probe]=/home/user/probeout_priors
declare -A DONE
for s in "${!DIRS[@]}"; do DONE[$s]=0; done

verify() {
  local d="$1"
  python3 - "$d" <<'PYEOF' >> /home/user/day_watch.log 2>&1
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
    for m in re.findall(r'(candidate pool: [^\\"]{5,80}|fingerprint models: [^\\"]{5,60}|ranker: [0-9]+ GBMs[^\\"]{0,40}|RRF[^\\"]{5,80}|submission written[^\\"]{0,60}|FUSE[^\\"]{5,80}|KNOB[^\\"]{5,80})', txt)[:8]:
        print('HOOK:', m.strip()[:110])
PYEOF
}

while true; do
  all=1
  for s in "${!DIRS[@]}"; do
    [ "${DONE[$s]}" = "1" ] && continue
    all=0
    st=$(kaggle kernels status victor120956/$s 2>&1)
    echo "[$(date -u +%FT%TZ)] $s: $st" >> $LOG
    case "$st" in
      *COMPLETE*)
        mkdir -p "${DIRS[$s]}"
        kaggle kernels output victor120956/$s -p "${DIRS[$s]}" >> $LOG 2>&1
        echo "[$(date -u +%FT%TZ)] $s output baixado; verificando" >> $LOG
        verify "${DIRS[$s]}"
        DONE[$s]=1 ;;
      *ERROR*|*error*)
        echo "[$(date -u +%FT%TZ)] $s ERROU — baixando log p/ diagnóstico" >> $LOG
        mkdir -p "${DIRS[$s]}"
        kaggle kernels output victor120956/$s -p "${DIRS[$s]}" >> $LOG 2>&1
        verify "${DIRS[$s]}"
        DONE[$s]=1 ;;
    esac
  done
  if [ $all = 1 ]; then echo "[$(date -u +%FT%TZ)] todos resolvidos — watcher encerrando" >> $LOG; break; fi
  sleep 300
done

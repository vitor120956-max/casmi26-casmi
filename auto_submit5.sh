#!/bin/bash
# Scheduler5: submete v12 REAL (kernel version 13, twin-sim rerank) quando completar.
# Verificação: log hook 'v12 twin-sim rerank' + validate_submission + rank1==twin do v3.
export PATH="/usr/local/bin:$HOME/.local/bin:$PATH"
export HOME=/home/user
LOG=/home/user/auto_submit5.log
OUT=/home/user/forkout_v12
SLUG=victor120956/casmi26-analog-ranker-fork
COMP=enveda-CASMI26-molecule-id-mass-spectra
V3FILE=/home/user/forkout_v3/submission.csv
chmod 600 /home/user/.kaggle/kaggle.json 2>/dev/null
command -v kaggle >/dev/null || pip install -q kaggle >> "$LOG" 2>&1
echo "$(date -u) === scheduler5 start (v12 real = version 13) ===" >> "$LOG"

for i in $(seq 1 90); do
  st=$(kaggle kernels status "$SLUG" 2>&1 | grep -v Warning)
  echo "$(date -u) kernel: $st" >> "$LOG"
  case "$st" in *COMPLETE*) break;; *ERROR*) echo "$(date -u) KERNEL ERROR -> abort" >> "$LOG"; exit 1;; esac
  sleep 120
done

mkdir -p "$OUT"
verified=no
for try in 1 2 3 4; do
  kaggle kernels output "$SLUG" -p "$OUT" >> "$LOG" 2>&1
  if grep -qa "v12 twin-sim rerank" "$OUT"/*.log 2>/dev/null; then
    v=$(python3 - "$OUT/submission.csv" "$V3FILE" <<'PYEOF'
import csv, sys
def load(fp):
    d = {}
    for r in csv.DictReader(open(fp)):
        d[r['molecule_id']] = [g for g in r['smiles'].split(';') if g]
    return d
new, v3 = load(sys.argv[1]), load(sys.argv[2])
if set(new) != set(v3):
    print('IDS_DIFFER'); raise SystemExit
r1_same = sum(1 for m in new if new[m] and v3[m] and new[m][0] == v3[m][0])
diff_tail = sum(1 for m in new if new[m][1:] != v3[m][1:])
print(f'R1_TWIN_{r1_same}_TAILDIFF_{diff_tail}')
PYEOF
    )
    echo "$(date -u) verify try$try: hook=OK rows: $v" >> "$LOG"
    case "$v" in R1_TWIN_400_*) verified=yes; break;; esac
  else
    echo "$(date -u) verify try$try: log hook absent (version 13 not done yet?)" >> "$LOG"
  fi
  sleep 480
done
if [ "$verified" != "yes" ]; then echo "$(date -u) NOT VERIFIED -> no submit" >> "$LOG"; exit 1; fi

python3 /home/user/casmi26/validate_submission.py "$OUT/submission.csv" >> "$LOG" 2>&1
grep -a -o '"data":"[^"]*"' "$OUT"/*.log | sed 's/"data":"//;s/"$//' | grep -E "v12 twin-sim|wrote submission" >> "$LOG"

for a in 1 2 3 4; do
  res=$(cd "$OUT" && kaggle competitions submit "$COMP" -f submission.csv -k "$SLUG" -v 13 -m "v12: twin@1 locked + ranks2-25 by Tanimoto-sim-to-twin (regioisomer-neighbor hypothesis)" 2>&1)
  echo "$(date -u) submit try$a: $res" >> "$LOG"
  case "$res" in *remaining*) echo "$(date -u) V12 SUBMITTED (or slots exhausted)" >> "$LOG"; break;;
                *[Ee]rror*) sleep 420;;
                *) echo "$(date -u) V12 SUBMITTED" >> "$LOG"; break;; esac
done

for i in $(seq 1 40); do
  echo "$(date -u) --- scores ---" >> "$LOG"
  kaggle competitions submissions "$COMP" -v 2>&1 | grep -v Warning | head -3 >> "$LOG"
  sleep 300
done
echo "$(date -u) === scheduler5 done ===" >> "$LOG"

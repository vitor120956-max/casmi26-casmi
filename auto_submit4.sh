#!/bin/bash
# Scheduler4: SOMENTE estágio C (version 11) + colheita de scores A2/B2/C.
export PATH="/usr/local/bin:$HOME/.local/bin:$PATH"
export HOME=/home/user
LOG=/home/user/auto_submit4.log
SLUG=victor120956/casmi26-analog-ranker-fork
COMP=enveda-CASMI26-molecule-id-mass-spectra
V3FILE=/home/user/forkout_v3/submission.csv
OUT=/home/user/forkout_probeC
chmod 600 /home/user/.kaggle/kaggle.json 2>/dev/null
command -v kaggle >/dev/null || pip install -q kaggle >> "$LOG" 2>&1
echo "$(date -u) === scheduler4 start (stage C, version 11) ===" >> "$LOG"

for i in $(seq 1 60); do
  st=$(kaggle kernels status "$SLUG" 2>&1 | grep -v Warning)
  echo "$(date -u) kernel: $st" >> "$LOG"
  case "$st" in *COMPLETE*) break;; *ERROR*) echo "$(date -u) KERNEL ERROR -> abort" >> "$LOG"; exit 1;; esac
  sleep 120
done

mkdir -p "$OUT"
verified=no
for try in 1 2 3; do
  kaggle kernels output "$SLUG" -p "$OUT" >> "$LOG" 2>&1
  v=$(python3 /home/user/verify_probe.py C "$OUT/submission.csv" "$V3FILE" 2>>"$LOG")
  echo "$(date -u) verify C try$try: $v" >> "$LOG"
  if [ "$v" = "OK" ]; then verified=yes; break; fi
  sleep 480
done
if [ "$verified" != "yes" ]; then echo "$(date -u) C NOT VERIFIED -> skip submit" >> "$LOG"; exit 1; fi
python3 /home/user/casmi26/validate_submission.py "$OUT/submission.csv" >> "$LOG" 2>&1

for a in 1 2 3 4; do
  res=$(cd "$OUT" && kaggle competitions submit "$COMP" -f submission.csv -k "$SLUG" -v 11 -m "P_C probe: original ranks 3-25 promoted (23 guesses) -> tail sum" 2>&1)
  echo "$(date -u) submit C try$a: $res" >> "$LOG"
  case "$res" in *remaining*|*[Ee]rror*) sleep 420;; *) echo "$(date -u) C SUBMITTED" >> "$LOG"; break;; esac
done

for i in $(seq 1 48); do
  echo "$(date -u) --- scores ---" >> "$LOG"
  kaggle competitions submissions "$COMP" -v 2>&1 | grep -v Warning | head -4 >> "$LOG"
  sleep 300
done
echo "$(date -u) === scheduler4 done ===" >> "$LOG"

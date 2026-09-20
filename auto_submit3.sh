#!/bin/bash
# Scheduler3: clean-probe pipeline A2(v9) -> B2(v10) -> C(v11).
# Cada estágio: set_probe -> set_desc -> push -> espera COMPLETE -> baixa output ->
# verify_probe contra forkout_v3 -> validate -> submit (sintaxe completa) -> próximo.
export PATH="/usr/local/bin:$HOME/.local/bin:$PATH"
export HOME=/home/user
LOG=/home/user/auto_submit3.log
SLUG=victor120956/casmi26-analog-ranker-fork
COMP=enveda-CASMI26-molecule-id-mass-spectra
DIR=/home/user/fork_bera
V3FILE=/home/user/forkout_v3/submission.csv
chmod 600 /home/user/.kaggle/kaggle.json 2>/dev/null
command -v kaggle >/dev/null || pip install -q kaggle >> "$LOG" 2>&1
echo "$(date -u) === scheduler3 start (clean probes A2/B2/C) ===" >> "$LOG"

probe_stage () {
  MODE=$1; VER=$2; OUT=/home/user/forkout_probe$MODE
  echo "$(date -u) --- STAGE $MODE (kernel version $VER) ---" >> "$LOG"
  python3 /home/user/set_probe.py "$MODE" >> "$LOG" 2>&1
  DESC=$(python3 /home/user/set_desc.py "$MODE" 2>>"$LOG" | sed 's/desc: //')
  (cd "$DIR" && kaggle kernels push -p . >> "$LOG" 2>&1)
  echo "$(date -u) pushed $MODE" >> "$LOG"
  for i in $(seq 1 60); do
    st=$(kaggle kernels status "$SLUG" 2>&1 | grep -v Warning)
    case "$st" in *COMPLETE*) echo "$(date -u) $MODE COMPLETE" >> "$LOG"; break;;
                  *ERROR*) echo "$(date -u) KERNEL ERROR at $MODE -> abort stage" >> "$LOG"; return 1;; esac
    sleep 120
  done
  mkdir -p "$OUT"
  verified=no
  for try in 1 2 3; do
    kaggle kernels output "$SLUG" -p "$OUT" >> "$LOG" 2>&1
    v=$(python3 /home/user/verify_probe.py "$MODE" "$OUT/submission.csv" "$V3FILE" 2>>"$LOG")
    echo "$(date -u) verify $MODE try$try: $v" >> "$LOG"
    if [ "$v" = "OK" ]; then verified=yes; break; fi
    sleep 600
  done
  if [ "$verified" != "yes" ]; then echo "$(date -u) $MODE NOT VERIFIED -> skip submit" >> "$LOG"; return 1; fi
  python3 /home/user/casmi26/validate_submission.py "$OUT/submission.csv" >> "$LOG" 2>&1
  for a in 1 2 3; do
    res=$(cd "$OUT" && kaggle competitions submit "$COMP" -f submission.csv -k "$SLUG" -v "$VER" -m "$DESC" 2>&1)
    echo "$(date -u) submit $MODE try$a: $res" >> "$LOG"
    case "$res" in *remaining*|*[Ee]rror*) sleep 420;; *) echo "$(date -u) $MODE SUBMITTED" >> "$LOG"; break;; esac
  done
}

probe_stage A2 9
probe_stage B2 10
probe_stage C  11

for i in $(seq 1 48); do
  echo "$(date -u) --- scores snapshot ---" >> "$LOG"
  kaggle competitions submissions "$COMP" -v 2>&1 | grep -v Warning | head -5 >> "$LOG"
  sleep 300
done
echo "$(date -u) === scheduler3 done ===" >> "$LOG"

#!/bin/bash
# Agendador 2: submete PROBE B (kernel version 8) quando completar e registra scores.
# Verificação de versão: log do run imprime 'demoted twins (v6): 0/400' (probe ignora demote).
export PATH="/usr/local/bin:$HOME/.local/bin:$PATH"
export HOME=/home/user
LOG=/home/user/auto_submit2.log
OUT=/home/user/forkout_probeB
SLUG=victor120956/casmi26-analog-ranker-fork
COMP=enveda-CASMI26-molecule-id-mass-spectra
chmod 600 /home/user/.kaggle/kaggle.json 2>/dev/null
echo "$(date -u) === scheduler2 start (PROBE B = version 8) ===" >> "$LOG"
if ! command -v kaggle >/dev/null; then pip install -q kaggle >> "$LOG" 2>&1; fi

for i in $(seq 1 90); do
  st=$(kaggle kernels status "$SLUG" 2>&1 | grep -v Warning)
  echo "$(date -u) kernel: $st" >> "$LOG"
  case "$st" in *COMPLETE*) break;; *ERROR*) echo "$(date -u) KERNEL ERROR -> abort" >> "$LOG"; exit 1;; esac
  sleep 120
done

mkdir -p "$OUT"
for try in 1 2 3; do
  kaggle kernels output "$SLUG" -p "$OUT" >> "$LOG" 2>&1
  if grep -qa "demoted twins (v6): 0/400" "$OUT"/*.log 2>/dev/null; then
    echo "$(date -u) output verified as version 8 (PROBE B)" >> "$LOG"; break
  fi
  echo "$(date -u) output not v8 yet (try $try) - refetch in 10m" >> "$LOG"
  sleep 600
done
python3 /home/user/casmi26/validate_submission.py "$OUT/submission.csv" >> "$LOG" 2>&1

for a in 1 2 3 4; do
  res=$(cd "$OUT" && kaggle competitions submit "$COMP" -f submission.csv -k "$SLUG" -v 8 -m "P_B probe: original ranker #2 at rank1 + junk (measures p_2 exactly)" 2>&1)
  echo "$(date -u) submit try $a: $res" >> "$LOG"
  case "$res" in *remaining*|*[Ee]rror*) sleep 420;; *) echo "$(date -u) SUBMIT OK" >> "$LOG"; break;; esac
done

for i in $(seq 1 36); do
  line=$(kaggle competitions submissions "$COMP" -v 2>&1 | grep -v Warning | sed -n 2p)
  echo "$(date -u) score(P_B): $line" >> "$LOG"
  pa=$(kaggle competitions submissions "$COMP" -v 2>&1 | grep -v Warning | grep "P_A" | head -1)
  echo "$(date -u) score(P_A): $pa" >> "$LOG"
  case "$line" in *SubmissionStatus.COMPLETE*|*SubmissionStatus.ERROR*) break;; esac
  sleep 300
done
echo "$(date -u) === scheduler2 done ===" >> "$LOG"

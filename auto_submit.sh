#!/bin/bash
# Agendador: submete v6 (kernel version 7, demote-twin) no reset dos slots diários
# (2026-09-18 00:02 UTC) e registra o score. Log: /home/user/auto_submit.log
export PATH="/usr/local/bin:$HOME/.local/bin:$PATH"
export HOME=/home/user
LOG=/home/user/auto_submit.log
OUT=/home/user/forkout_v6
SLUG=victor120956/casmi26-analog-ranker-fork
COMP=enveda-CASMI26-molecule-id-mass-spectra
chmod 600 /home/user/.kaggle/kaggle.json 2>/dev/null
echo "$(date -u) === scheduler start ===" >> "$LOG"

if ! command -v kaggle >/dev/null; then pip install -q kaggle >> "$LOG" 2>&1; fi

TARGET=$(date -u -d "2026-09-18 00:02:00" +%s)
while [ "$(date -u +%s)" -lt "$TARGET" ]; do sleep 60; done
echo "$(date -u) reset reached" >> "$LOG"

for a in 1 2 3 4 5 6; do
  res=$(cd "$OUT" && kaggle competitions submit "$COMP" -f submission.csv -k "$SLUG" -v 7 -m "v6: twin demotion - perfect library hit to rank25, ranks 2-25 promoted (tests f_t=0)" 2>&1)
  echo "$(date -u) submit try $a: $res" >> "$LOG"
  case "$res" in *remaining*|*[Ee]rror*) sleep 600;; *) echo "$(date -u) SUBMIT OK" >> "$LOG"; break;; esac
done

for i in $(seq 1 36); do
  line=$(kaggle competitions submissions "$COMP" -v 2>&1 | grep -v Warning | sed -n 2p)
  echo "$(date -u) score-check: $line" >> "$LOG"
  case "$line" in *SubmissionStatus.COMPLETE*|*SubmissionStatus.ERROR*) break;; esac
  sleep 300
done
echo "$(date -u) === scheduler done ===" >> "$LOG"

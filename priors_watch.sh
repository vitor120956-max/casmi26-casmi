#!/bin/bash
# priors_watch.sh — priors2 v2 (pushado LIMPO 19:52:32Z) → espera COMPLETE → baixa (-p) → verify.
export PATH="$HOME/.local/bin:$PATH"
cd /home/user
LOG=/home/user/day_watch.log
log(){ echo "[$(date -u +%FT%TZ)] $1" >> $LOG; }
log "priors-watch: START"
while true; do
  st=$(timeout 45 kaggle kernels status victor120956/casmi26-priors-high-probe2 2>&1 | tail -1)
  case "$st" in
    *omplete*) log "priors-watch: priors2 COMPLETE ✓"; break;;
    *rror*) log "priors-watch: priors2 ERROR — baixar log p/ forense"; break;;
    *) sleep 120;;
  esac
done
rm -f probeout_priors2/*
timeout 300 kaggle kernels output victor120956/casmi26-priors-high-probe2 -p probeout_priors2 >> $LOG 2>&1
log "priors-watch: $(bash verify_out.sh probeout_priors2 2>&1 | tail -1)"
cp probeout_priors2/submission.csv wave_backup/priors2.csv 2>/dev/null && log "priors-watch: backup copiado p/ wave_backup/"
log "priors-watch: FIM"

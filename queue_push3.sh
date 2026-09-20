#!/bin/bash
# queue_push3.sh — fila só p/ priors (megayak+seedswap já pushados manualmente)
export PATH="$HOME/.local/bin:$PATH"
LOG=/home/user/day_watch.log
for i in $(seq 1 150); do
  out=$(kaggle kernels push -p /home/user/kpush_priors 2>&1)
  echo "[$(date -u +%FT%TZ)] push priors #$i: $(echo "$out" | tr '\n' ' ' | cut -c1-150)" >> $LOG
  case "$out" in *"successfully pushed"*) echo "[$(date -u +%FT%TZ)] priors PUSHED" >> $LOG; exit 0;; esac
  sleep 300
done

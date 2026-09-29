#!/bin/bash
# queue_push2.sh — fila GPU (max 2 sessions): megayak → seedswap → priors
export PATH="$HOME/.local/bin:$PATH"
LOG=/home/user/day_watch.log
push_dir() {
  local dir="$1" name="$2"
  for i in $(seq 1 150); do
    out=$(kaggle kernels push -p "$dir" 2>&1)
    echo "[$(date -u +%FT%TZ)] push $name #$i: $(echo "$out" | tr '\n' ' ' | cut -c1-160)" >> $LOG
    case "$out" in *"successfully pushed"*) echo "[$(date -u +%FT%TZ)] $name PUSHED" >> $LOG; return 0;; esac
    sleep 300
  done
}
push_dir /home/user/kpush_megayak megayak
push_dir /home/user/kpush_seedswap seedswap
push_dir /home/user/kpush_priors priors
echo "[$(date -u +%FT%TZ)] queue_push2 encerrado" >> $LOG

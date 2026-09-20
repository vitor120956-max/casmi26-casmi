#!/bin/bash
# queue_push.sh — espera vaga de GPU session (max 2) e pusha kpush_priors; depois kpush_offset se existir
export PATH="$HOME/.local/bin:$PATH"
LOG=/home/user/day_watch.log

push_dir() {
  local dir="$1" name="$2"
  for i in $(seq 1 150); do
    [ -d "$dir" ] || { sleep 300; continue; }
    out=$(kaggle kernels push -p "$dir" 2>&1)
    echo "[$(date -u +%FT%TZ)] push $name tentativa $i: $(echo "$out" | head -1)" >> $LOG
    case "$out" in *"successfully pushed"*) echo "[$(date -u +%FT%TZ)] $name PUSHED OK" >> $LOG; return 0;; esac
    sleep 300
  done
  echo "[$(date -u +%FT%TZ)] $name: desisti após 150 tentativas" >> $LOG
}

push_dir /home/user/kpush_priors priors
push_dir /home/user/kpush_offset offset
echo "[$(date -u +%FT%TZ)] queue_push encerrado" >> $LOG

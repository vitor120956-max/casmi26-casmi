#!/bin/bash
# queue_push4.sh — fila tolerante: seedswap2 → megayak2 → priors2 (slugs novos, retry p/ limite GPU)
export PATH="$HOME/.local/bin:$PATH"
LOG=/home/user/day_watch.log
push_dir() {
  local dir="$1" name="$2"
  for i in $(seq 1 200); do
    out=$(kaggle kernels push -p "$dir" 2>&1)
    echo "[$(date -u +%FT%TZ)] push $name #$i: $(echo "$out" | tr '\n' ' ' | cut -c1-170)" >> $LOG
    if echo "$out" | grep -q "successfully pushed"; then
      if echo "$out" | grep -q "not valid competition sources"; then
        echo "[$(date -u +%FT%TZ)] $name PUSHED mas COM WARNING de competition — teoria tainted refutada p/ slug novo!" >> $LOG
      else
        echo "[$(date -u +%FT%TZ)] $name PUSHED LIMPO ✓" >> $LOG
      fi
      return 0
    fi
    sleep 240
  done
}
push_dir /home/user/kpush_seedswap2 seedswap2
push_dir /home/user/kpush_megayak2 megayak2
push_dir /home/user/kpush_priors2 priors2
echo "[$(date -u +%FT%TZ)] queue_push4 encerrado" >> $LOG

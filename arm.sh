#!/bin/bash
# arm.sh — REARME TOTAL pós-restart (rodar no início de turnos de trabalho). Idempotente, ~10s.
export PATH="$HOME/.local/bin:$PATH"
python3 -c "import kaggle" 2>/dev/null || pip install -q kaggle >/dev/null 2>&1
chmod 600 ~/.kaggle/kaggle.json 2>/dev/null
chmod +x /home/user/*.sh /home/user/.bin/gh 2>/dev/null
/home/user/.bin/gh auth setup-git 2>/dev/null
cd /home/user
git config user.name "Victor Alexandre" 2>/dev/null
git config user.email "victor120956@users.noreply.github.com" 2>/dev/null
git remote set-url origin https://github.com/vitor120956-max/casmi26-casmi.git 2>/dev/null || git remote add origin https://github.com/vitor120956-max/casmi26-casmi.git 2>/dev/null
git fetch -q origin 2>/dev/null && git rev-list --count HEAD..origin/main 2>/dev/null | xargs -I{} echo "git: {} commits atrás do remoto"
which kaggle >/dev/null && echo "arm: OK ✓" || echo "arm: FALHOU ✗"

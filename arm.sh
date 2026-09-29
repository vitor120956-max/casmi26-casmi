#!/usr/bin/env bash
set -euo pipefail
cd /home/user
if ! python -c 'import kaggle' >/dev/null 2>&1 && ! python -c 'import importlib.util; assert importlib.util.find_spec("kaggle")' >/dev/null 2>&1; then
  python -m pip install --quiet kaggle
fi
python - <<'PY'
import json, pathlib, os
files=list(pathlib.Path('/home/user/uploads').glob('kaggle*.json'))
if not files: raise SystemExit('Falta kaggle.json em uploads')
data=json.loads(files[0].read_text())
assert data.get('username') and data.get('key'), 'Credencial incompleta'
d=pathlib.Path.home()/'.kaggle'; d.mkdir(mode=0o700,exist_ok=True)
p=d/'kaggle.json'; p.write_text(json.dumps(data)); p.chmod(0o600)
print('Auth restaurada; segredo não exibido.')
PY
if ! python -c 'import importlib.util; assert importlib.util.find_spec("rdkit")' >/dev/null 2>&1; then
  python -m pip install --quiet rdkit
fi
# .git/config também é efêmero: restaurar metadados não secretos, sem simular auth.
if [ -d /home/user/recovered/.git ]; then
  git -C /home/user/recovered config user.name >/dev/null 2>&1 || git -C /home/user/recovered config user.name 'Victor Alexandre'
  git -C /home/user/recovered config user.email >/dev/null 2>&1 || git -C /home/user/recovered config user.email 'victor120956@users.noreply.github.com'
  git -C /home/user/recovered remote get-url origin >/dev/null 2>&1 || git -C /home/user/recovered remote add origin https://github.com/vitor120956-max/casmi26-casmi.git
fi
export PATH="$HOME/.local/bin:$PATH"
kaggle --version

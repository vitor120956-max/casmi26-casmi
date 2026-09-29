#!/usr/bin/env bash
set -euo pipefail
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}" python - "$1" <<'PY'
import json,pathlib,sys
from safety_guards import validate_kernel,validate_publication_safety
p=pathlib.Path(sys.argv[1]);m=json.loads((p/'kernel-metadata.json').read_text())
n=json.loads((p/m['code_file']).read_text())
validate_kernel(m,n)
validate_publication_safety(n)
print('PRECHECK PASS: CPU; kernelspec; syntax; competition; approved assets; no own dataset/tier2')
print('OBS: autorização para submit exige também plano com file=submission.csv + versão e hash conhecidos.')
PY

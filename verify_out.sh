#!/bin/bash
# verify_out.sh <probeout_dir> — valida output baixado. PASS = submisível; FAIL = NÃO submeter.
d=${1:?uso: verify_out.sh <probeout_dir>}
python3 - "$d" <<'PYEOF'
import csv, glob, os, sys
d = sys.argv[1]
p = os.path.join(d, "submission.csv")
ok = True
if not os.path.exists(p): print("VERIFY FAIL: submission.csv ausente"); sys.exit(1)
with open(p, newline="") as f:
    rows = list(csv.reader(f))
hdr, body = rows[0], rows[1:]
if hdr != ["molecule_id", "smiles"]: print(f"VERIFY FAIL: colunas {hdr}"); ok = False
if len(body) != 400: print(f"VERIFY FAIL: {len(body)} linhas (esperado 400)"); ok = False
nulls = sum(1 for r in body for c in r if not c or not c.strip())
if nulls: print(f"VERIFY FAIL: {nulls} células vazias"); ok = False
cco = sum(1 for r in body if len(r) > 1 and r[1].strip() == "CCO")
if cco: print(f"VERIFY FAIL: {cco} placeholders CCO"); ok = False
bad = [l for l in glob.glob(os.path.join(d, "*.log")) if "traceback" in open(l, errors="ignore").read().lower()]
if bad: print(f"VERIFY FAIL: Traceback em {[os.path.basename(b) for b in bad]}"); ok = False
print("VERIFY PASS ✓ (400 linhas, cols ok, 0 vazias, 0 CCO, sem Traceback)" if ok else "VERIFY FAIL — NÃO SUBMETER")
sys.exit(0 if ok else 1)
PYEOF

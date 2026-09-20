#!/bin/bash
# precheck.sh <kpush_dir> — VERIFICAÇÃO OBRIGATÓRIA ANTES DE QUALQUER PUSH.
# Nasceu do typo envida/enveda (20/09): metadata clonado SEM diff = erro silencioso.
# Exit 0 = PODE pushar. Exit 1 = NUNCA pushar.
GOLD_COMP="enveda-CASMI26-molecule-id-mass-spectra"
d=${1:?uso: precheck.sh <kpush_dir>}
m="$d/kernel-metadata.json"
[ -f "$m" ] || { echo "PRECHECK FAIL: $m não existe"; exit 1; }
python3 - "$d" "$m" "$GOLD_COMP" <<'PYEOF'
import json, os, re, sys
d, m, gold = sys.argv[1], sys.argv[2], sys.argv[3]
try: md = json.load(open(m))
except Exception as e: print(f"PRECHECK FAIL: metadata ilegível: {e}"); sys.exit(1)
errs = []
comp = md.get("competition_sources", [])
if comp != [gold]: errs.append(f"competition_sources != GOLDEN ({comp})")
if md.get("enable_gpu") is not True: errs.append(f"enable_gpu={md.get('enable_gpu')} (precisa true)")
if not re.match(r"^[a-z0-9-]+/[a-z0-9-]+$", md.get("id","")): errs.append(f"id suspeito: {md.get('id')}")
cf = md.get("code_file","")
p = os.path.join(d, cf) if cf else ""
if not cf or not os.path.exists(p): errs.append(f"code_file ausente: {cf}")
else:
    try:
        nb = json.load(open(p))
        n = len(nb.get("cells", []))
        if n < 3: errs.append(f"notebook com só {n} cells — conteúdo errado?")
    except Exception as e: errs.append(f"notebook ilegível: {e}")
ds = md.get("dataset_sources", [])
for s in ds:
    if not re.match(r"^[A-Za-z0-9_-]+/[A-Za-z0-9_.-]+$", s): errs.append(f"dataset slug malformado: {s}")
print(f"  id={md.get('id')} gpu={md.get('enable_gpu')} comp={comp} datasets={ds}")
if errs:
    print("PRECHECK FAIL:"); [print("  -", e) for e in errs]; sys.exit(1)
print("PRECHECK PASS ✓")
PYEOF

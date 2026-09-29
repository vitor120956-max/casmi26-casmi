#!/bin/bash
# recon_sweep.sh [label] — VASCULHADA NOTURNA (instrução permanente do usuário 20/09):
# varre kernels/datasets/models novos da competição → recon_log/sweep_<label>.txt + resume na tela.
export PATH="$HOME/.local/bin:$PATH"
cd /home/user
mkdir -p recon_log
L=${1:-$(date -u +%Y%m%d_%H%M)}
OUT=recon_log/sweep_$L.txt
{
echo "=== SWEEP $(date -u +%FT%TZ) ==="
echo "--- kernels por dateRun ---"
timeout 60 kaggle kernels list --competition enveda-CASMI26-molecule-id-mass-spectra --sort-by dateRun --page-size 20 2>/dev/null
echo "--- datasets por updated ---"
timeout 60 kaggle datasets list -s casmi26 --sort-by updated --page-size 15 2>/dev/null
echo "--- models busca casmi ---"
timeout 60 kaggle models list -s casmi 2>/dev/null | head -10
} > $OUT 2>&1
echo "salvo em $OUT ($(wc -l < $OUT) linhas)"
grep -E "2026-09-2[0-9]" $OUT | head -12

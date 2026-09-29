#!/usr/bin/env bash
# Reconstrói o repositório de exportação e deixa o commit limpo pronto para push.
# O espelho local é EFÊMERO: se não existir, clona do GitHub (branch export-clean).
# Uso: bash rebuild_export.sh "mensagem do commit"
set -euo pipefail
MSG="${1:-Clean export: reconciled state}"
ROOT=/home/user
R="$ROOT/recovered"
REPO=https://github.com/vitor120956-max/casmi26-casmi.git
if [ ! -d "$R/.git" ]; then
  rm -rf "$R"
  git clone -q -b export-clean "$REPO" "$R"
fi
# Sincroniza o estado mais recente do workspace sobre o espelho.
for f in WAVE7_HANDOFF.md WAVE7_RESULTADO.md WAVE8_PLAN.md WAVE8_RESULTADO.md WAVE9_PLAN.md \
         PROJECT_PRIORITY.md ERROR_REGISTRY.md PUBLIC_EXPORT_BLOCKED.md day_watch.log incidents.jsonl \
         atomic_submission.py formula_evidence.py safety_guards.py wave7_run.py arm.sh precheck.sh \
         wave9_runtime.py build_wave9.py test_wave9_isolation.py audit_wave9_failure_modes.py \
         verify_wave9.py submit_wave9.py github_device_export.py rebuild_export.sh \
         wave9_plan.json wave9_push_verify.json wave9_submit_state.json wave9_ready.json wave9_before_send.json \
         check_next_batch_once.py send_next_batch.py batch_release_checks.py selected_variant_runtime.py \
         build_selected_repair.py TRANSFERENCIA_ATUAL_CASMI.md GIT_PROVENIENCIA_TRANSFERENCIA.json \
         MANIFESTO_BACKUP.json TESTES_NA_TRANSFERENCIA.log COLE_NO_NOVO_AGENTE.txt; do
  [ -f "$ROOT/$f" ] && cp -f "$ROOT/$f" "$R/$f"
done
for d in kpush_wave9_adduct kpush_wave9_adduct_dedup kpush_wave9_formula_dedup kpush_wave9_top1 \
         kpush_wave9_top1_dedup wave9_failure_diagnosis next_batch_preparation casmi_repair_drafts \
         remote_wave9_reconciliation gemma decision_recon wave8_failure_diagnosis; do
  [ -d "$ROOT/$d" ] && { mkdir -p "$R/$d"; cp -rf "$ROOT/$d/." "$R/$d/"; }
done
# Sanitização de exportação (trava permanente): nunca publicar estes caminhos.
rm -rf "$R"/next_batch_preparation/outputs "$R"/gemma/official "$R"/harness_data "$R"/probeout_w088 \
       "$R"/probeout_wave9 "$R"/read_only_audits_27sep.tar.gz
cd "$R"
git add -A
if git diff --cached --quiet; then echo "NOTHING_TO_COMMIT $(git rev-parse HEAD)"; exit 0; fi
git -c user.name='Victor Alexandre' -c user.email='victor120956@users.noreply.github.com' \
    commit -q -m "$MSG"
git log --oneline -2
echo "REBUILD_READY $(git rev-parse HEAD)"

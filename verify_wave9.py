#!/usr/bin/env python3
"""Verificador one-shot Wave9: uma leitura de status por kernel, sem polling/submit.

Só gera wave9_ready.json para kernels COMPLETE com outputs íntegros, código remoto
idêntico ao local, prova coerente, engine de controle reproduzido (audit_blend) e
artefato distinto do histórico. Ausência de COMPLETE preserva o slot: sem retry.
"""
import concurrent.futures, hashlib, json, pathlib
import wave7_run as w
from safety_guards import record_failure, validate_kernel, validate_publication_safety

R = w.ROOT
plans = json.loads((R / 'wave9_plan.json').read_text())
history = json.loads((R / 'historical_hashes.json').read_text())
for tag, e in json.loads((R / 'wave7_submit_state.json').read_text()).items():
    if e.get('phase') == 'accepted':
        history[e['plan']['semantic_sha256']] = ['Wave7 ' + tag]
# Wave8 NÃO entra no histórico de bloqueio: seus artefatos nunca foram avaliados
# (rejeitados na reexecução, E029). A identidade do preview Wave9 com a expectativa
# local Wave8 é esperada — o mesmo mecanismo sobre os mesmos dados públicos produz
# o mesmo arquivo; o que mudou é o comportamento na reexecução oculta.
BLEND_REF = (R / 'probeout_w088/submission.csv').read_bytes()
TEST_SHA = hashlib.sha256((R / 'harness_data/test.parquet').read_bytes()).hexdigest()
EXPECT = {'top1': R / 'wave8_local_expectations/top1.csv',
          'formula_dedup': R / 'wave8_local_expectations/formula_dedup.csv',
          'top1_dedup': R / 'wave8_local_expectations/top1_dedup.csv'}
PROFILE = json.loads((R / 'wave8_mechanism_profile.json').read_text())
PATTERN = r'^(submission\.csv|audit_selected\.csv|audit_blend\.csv|publication\.json|lineage_before_publish\.json|formula_adducts\.json)$'


def verify(p):
    a = w.connect()
    s = w.obj(a.kernels_status(p['kernel']))
    w.log('WAVE9_CHECK_ONCE ' + p['tag'] + ' ' + json.dumps(s))
    if s.get('status') != 'COMPLETE':
        return None
    d = R / 'probeout_wave9' / p['tag']
    a.kernels_output(p['kernel'], str(d), file_pattern=PATTERN, force=True, quiet=True)
    mdir = R / 'remote_wave9_verify' / p['tag']
    a.kernels_pull(p['kernel'], str(mdir), metadata=True, quiet=True)
    m = json.loads((mdir / 'kernel-metadata.json').read_text())
    n = json.loads((mdir / m['code_file']).read_text())
    local = json.loads((pathlib.Path(p['folder']) / 'wave9.ipynb').read_text())
    validate_kernel(m, n)
    validate_publication_safety(n)
    assert m['id'] == p['kernel'], 'REMOTE_SLUG_MISMATCH'
    assert [''.join(c['source']) for c in n['cells']] == [''.join(c['source']) for c in local['cells']], 'REMOTE_CODE_DIFFERS'
    proof = json.loads((d / 'publication.json').read_text())
    raw = (d / 'submission.csv').read_bytes()
    assert proof['variant'] == p['tag'], 'VARIANT_MISMATCH'
    assert proof['publication_contract'] == 'atomic-final-only-v1'
    assert proof['cpu_only'] and proof['full_pipeline'] and not proof['own_dataset_inputs']
    assert proof['sha256'] == hashlib.sha256(raw).hexdigest() and proof['bytes'] == len(raw)
    assert raw == (d / 'audit_selected.csv').read_bytes(), 'SELECTED_ARTIFACT_MISMATCH'
    assert (d / 'audit_blend.csv').read_bytes() == BLEND_REF, 'ENGINE_BLEND_REGRESSION_FAILED'
    assert proof['test_sha256'] == TEST_SHA, 'TEST_PARQUET_MISMATCH'
    assert proof['degraded'] == [], ('PREVIEW_DEGRADED_UNEXPECTED', proof['degraded'])
    assert proof['selected_vs_blend_changed_rows'] > 0, 'MECHANISM_NOOP_ON_PREVIEW'
    assert proof['expected_rows'] == 400, 'PREVIEW_ROW_COUNT'
    if p['tag'] in EXPECT:
        assert raw == EXPECT[p['tag']].read_bytes(), ('MECHANISM_DIVERGES_FROM_LOCAL_EXPECTATION', p['tag'])
    if p['tag'].startswith('adduct'):
        assert proof['adduct_group_count'] == PROFILE['adduct_groups'], 'ADDUCT_GROUP_COUNT'
        assert proof['adduct_coverage'] > 0.9, 'ADDUCT_COVERAGE_COLLAPSED'
    sig, _ = w.verify(d / 'submission.csv', proof['sha256'], history)
    return dict(p, path=str(d / 'submission.csv'), sha256=proof['sha256'], semantic_sha256=sig,
                preview_verified=True, engine_blend_regression_pass=True, preview_degraded=[])


ready = []
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
    tasks = [pool.submit(verify, p) for p in plans]
for p, task in zip(plans, tasks):
    try:
        r = task.result()
        if r:
            ready.append(r)
    except Exception as e:
        record_failure('WAVE9_VERIFY', repr(e), {'tag': p['tag']})
        w.log('WAVE9_VERIFY_FAIL ' + p['tag'] + ' ' + repr(e))
# Fail closed: nunca oferecer dois artefatos idênticos como probes distintas.
seen = set()
unique = []
for p in ready:
    if p['semantic_sha256'] in seen:
        record_failure('E003', 'Artefato Wave9 duplicado bloqueado', {'tag': p['tag']})
        w.log('WAVE9_DUPLICATE_BLOCKED ' + p['tag'])
        continue
    seen.add(p['semantic_sha256'])
    unique.append(p)
(R / 'wave9_ready.json').write_text(json.dumps(unique, ensure_ascii=False, indent=2))
print('VERIFIED_WAVE9', len(unique), [p['tag'] for p in unique])
print('NO_SUBMISSIONS_MADE')

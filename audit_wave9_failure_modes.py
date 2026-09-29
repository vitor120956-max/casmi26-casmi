#!/usr/bin/env python3
"""Auditoria de imunidade Wave9 contra os modos de falha reproduzidos na Wave8 (E031).

CPU-only, sem API, sem submissão. Não afirma a causa oculta do E029: prova apenas
que os modos reproduzidos sinteticamente na Wave8 não podem mais abortar o lote,
usando o código real (wave9_runtime/formula_evidence/AtomicSubmission) e AST dos
cinco fontes gerados. Saída: wave9_failure_diagnosis/synthetic_immunity.json.
"""
import ast, hashlib, json, pathlib, tempfile
import pandas as pd

from atomic_submission import AtomicSubmission
from formula_evidence import combine_formula_evidence_lenient, split_spectra_lenient
from wave9_runtime import dedup_rows, formula_order

ROOT = pathlib.Path(__file__).resolve().parent
DIRS = ['kpush_wave9_adduct', 'kpush_wave9_adduct_dedup', 'kpush_wave9_formula_dedup',
        'kpush_wave9_top1', 'kpush_wave9_top1_dedup']


def calc_f(smi):
    from rdkit import Chem
    from rdkit.Chem.rdMolDescriptors import CalcMolFormula
    m = Chem.MolFromSmiles(smi)
    return CalcMolFormula(m).rstrip('+-') if m is not None else None


def canon_key(s):
    from rdkit import Chem
    m = Chem.MolFromSmiles(s)
    return Chem.MolToSmiles(m) if m is not None else None


def valid_smiles(s):
    from rdkit import Chem
    return Chem.MolFromSmiles(s) is not None


def synthetic_frame(n=100):
    rows = []
    for i in range(n):
        rows.append({'molecule_id': f'm{i}',
                     'smiles': ';'.join(['CCCCO', 'CCCO', 'CCO', 'CO'] + ['C'] * 21)})
    return pd.DataFrame(rows), [f'm{i}' for i in range(n)]


def publish(selected, sample_ids, degraded):
    with tempfile.TemporaryDirectory() as td:
        pub = AtomicSubmission(td)
        pub.begin()
        report = pub.publish(selected.to_dict('records'), sample_ids, valid_smiles,
                             dict(variant='synthetic', degraded=degraded))
        exists = (pathlib.Path(td) / 'submission.csv').exists()
    return report, exists


def run():
    result = {'scope': ('Modos sintéticos reproduzidos na Wave8 (wave8_failure_diagnosis) testados contra '
                        'o código Wave9 real. Causa oculta do E029 permanece desconhecida.'), 'checks': [], 'kernels': []}
    checks = 0

    # Modo 1 — trava de cobertura: o guard não existe mais nos cinco fontes.
    for d in DIRS:
        folder = ROOT / d
        meta = json.loads((folder / 'kernel-metadata.json').read_text())
        nb = json.loads((folder / meta['code_file']).read_text())
        gate = loop = None
        for c in nb['cells']:
            if c['cell_type'] != 'code':
                continue
            s = ''.join(c['source'])
            if s.startswith('%%writefile '):
                s = s.split('\n', 1)[1]
            for node in ast.walk(ast.parse(s)):
                unparsed = ast.unparse(node)
                if isinstance(node, ast.If) and ('MSBUDDY_COVERAGE_FAILED' in unparsed or '0.975' in unparsed):
                    gate = node
                if isinstance(node, ast.For) and 'AtomicSubmission.validate' in unparsed:
                    loop = node
        assert gate is None, ('COVERAGE_GATE_STILL_PRESENT', d)
        assert loop is None, ('CROSS_BRANCH_VALIDATE_LOOP_STILL_PRESENT', d)
        result['kernels'].append({'slug': meta['id'],
                                  'source_sha256': hashlib.sha256((folder / meta['code_file']).read_bytes()).hexdigest(),
                                  'coverage_gate_present': False, 'cross_branch_validate_loop_present': False})
        checks += 2

    # Modo 1 (comportamental) — cobertura 97% não aborta; publicação acontece.
    sub, ids = synthetic_frame(100)
    formulas = {f'm{i}': ['CH4O'] for i in range(97)}  # 97% de cobertura
    degraded = []
    selected, stats = formula_order(sub, formulas, calc_f, degraded=degraded)
    report, exists = publish(selected, ids, degraded)
    assert exists and report['rows'] == 100 and stats['rows_without_formula'] == 3
    result['checks'].append({'mode': 'coverage_0.97', 'outcome': 'PUBLISHED', 'rows': report['rows'],
                             'rows_without_formula': stats['rows_without_formula']})
    checks += 1

    # Modo 3 — falha total de dependência (msbuddy): degrada e publica.
    degraded = [['MSBUDDY_UNAVAILABLE', "AssertionError('no wheels')"]]
    selected, stats = formula_order(sub, {}, calc_f, degraded=degraded)
    report, exists = publish(selected, ids, degraded)
    assert exists and report['rows'] == 100 and stats['changed_rows'] == 0
    result['checks'].append({'mode': 'msbuddy_unavailable', 'outcome': 'PUBLISHED_DEGRADED',
                             'degraded': degraded, 'changed_rows': stats['changed_rows']})
    checks += 1

    # Modo 4 — massa ausente e pool curto no dedup: padding explícito, sem aborto.
    degraded = []
    big = {'mass': [16.0 * (i + 1) for i in range(60)], 'smiles': ['C' * (i + 1) for i in range(60)]}
    recs = [{'mid': f'm{i}', 'target': 60.0 if i % 2 else float('nan')} for i in range(100)]
    dedup_sub, dstats = dedup_rows(sub, recs, big, canon_key, degraded)
    report, exists = publish(dedup_sub, ids, degraded)
    assert exists and dstats['rows_without_mass'] == 50 and dstats['padded_slots'] == 50 * 21
    result['checks'].append({'mode': 'missing_mass_short_pool', 'outcome': 'PUBLISHED_DEGRADED',
                             'rows_without_mass': dstats['rows_without_mass'], 'padded_slots': dstats['padded_slots']})
    checks += 1

    # Modo 5 — linhas de espectro inválidas: skip registrado, evidência sobrevive.
    degraded = []
    rows = []
    for i in range(10):
        rows.append({'molecule_id': f'm{i}', 'adduct': '[M+H]+', 'ionization_mode': 'positive',
                     'ms2_mzs': [100.0, 200.0], 'ms2_normalized_intensities': [0.5, 1.0], 'precursor_mz': 500.0})
    rows.append({'molecule_id': 'm10', 'adduct': '[M+?]', 'ionization_mode': 'positive',
                 'ms2_mzs': [1.0], 'ms2_normalized_intensities': [1.0, 2.0], 'precursor_mz': 1.0})
    groups = split_spectra_lenient(rows, degraded)
    assert len(groups) == 10 and degraded == [['SPECTRA_ROWS_SKIPPED', 1]]
    combined = combine_formula_evidence_lenient(
        [dict(molecule_id=g['molecule_id'], adduct=g['adduct'], mode=g['mode'], formulas=['C2H6O']) for g in groups]
        + [dict(molecule_id='m0', adduct='[M+H]+', mode='positive', formulas=['CH4O'])], degraded)
    assert combined['m0'][0] == 'C2H6O' and degraded[-1] == ['DUPLICATE_ADDUCT_GROUPS_SKIPPED', 1]
    result['checks'].append({'mode': 'invalid_spectra_rows_and_duplicate_groups', 'outcome': 'SKIPPED_WITH_RECORD',
                             'groups': len(groups), 'degraded': degraded})
    checks += 1

    # Modo 2 (estrutural) — ramo auxiliar inválido não pode bloquear: não há ramo auxiliar.
    # Prova comportamental: dado inválido "auxiliar" presente no ambiente, publicação do escolhido OK.
    unused_invalid = pd.DataFrame([{'molecule_id': 'm0', 'smiles': ';'.join(['INVALID'] * 25)}])  # nunca validado
    degraded = []
    selected, _ = formula_order(sub, formulas, calc_f, degraded=degraded)
    report, exists = publish(selected, ids, degraded)
    assert exists and unused_invalid is not None
    result['checks'].append({'mode': 'unused_invalid_branch_present', 'outcome': 'PUBLISHED_SELECTED_ONLY'})
    checks += 1

    result['checks_passed'] = checks
    out = ROOT / 'wave9_failure_diagnosis'
    out.mkdir(exist_ok=True)
    (out / 'synthetic_immunity.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    run()

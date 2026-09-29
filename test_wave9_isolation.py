#!/usr/bin/env python3
"""Testes Wave9: runtime real + isolamento estático dos cinco kernels.

Importa wave9_runtime/formula_evidence (código de produção embutido nos kernels),
não uma reimplementação. CPU, sem rede, sem API, sem submissão.
"""
import ast, json, pathlib, tempfile, unittest

import pandas as pd

from atomic_submission import AtomicSubmission
from formula_evidence import (adduct_charge, combine_formula_evidence,
                              combine_formula_evidence_lenient, split_spectra,
                              split_spectra_lenient)
from safety_guards import validate_kernel, validate_publication_safety
from wave9_runtime import clean_existing, dedup_rows, formula_order, refill_by_pool_mass

R = pathlib.Path('/home/user')
TAGS = ['adduct', 'adduct_dedup', 'formula_dedup', 'top1', 'top1_dedup']
FORMULAS = {'C2H6O', 'CH4O', 'C3H8O'}


def calc_f(smi):
    from rdkit import Chem
    from rdkit.Chem.rdMolDescriptors import CalcMolFormula
    m = Chem.MolFromSmiles(smi)
    return CalcMolFormula(m).rstrip('+-') if m is not None else None


def canon_key(s):
    from rdkit import Chem
    m = Chem.MolFromSmiles(s)
    return Chem.MolToSmiles(m) if m is not None else None


def frame(rows):
    return pd.DataFrame(rows)


def base_rows():
    return [
        {'molecule_id': 'm1', 'smiles': ';'.join(['CCCCO', 'CCCO', 'CCO', 'CO'] + ['C'] * 21)},
        {'molecule_id': 'm2', 'smiles': ';'.join(['CCCCO', 'CCCO', 'CCO', 'CO'] + ['C'] * 21)},
    ]


def pool():
    return {'mass': [32.0, 46.0, 60.0, 74.0, 88.0, 102.0],
            'smiles': ['CO', 'CCO', 'CCCO', 'CCCCO', 'CCCCCO', 'CCCCCCO']}


def big_pool():
    return {'mass': [16.0 * (i + 1) for i in range(60)],
            'smiles': ['C' * (i + 1) for i in range(60)]}


class TestFormulaOrder(unittest.TestCase):
    def test_promotes_matching_formula(self):
        sub = frame(base_rows())
        out, stats = formula_order(sub, {'m1': ['CH4O'], 'm2': ['CH4O']}, calc_f)
        self.assertEqual(out.at[0, 'smiles'].split(';')[0], 'CO')  # metanol promovido ao topo
        self.assertEqual(stats['changed_rows'], 2)
        self.assertEqual(stats['rows_without_formula'], 0)

    def test_partial_coverage_never_aborts(self):
        sub = frame(base_rows())
        degraded = []
        out, stats = formula_order(sub, {'m1': ['CH4O']}, calc_f, degraded=degraded)
        self.assertEqual(out.at[1, 'smiles'], sub.at[1, 'smiles'])  # m2 sem fórmula: no-op
        self.assertEqual(stats['rows_without_formula'], 1)
        self.assertEqual(degraded, [['FORMULA_ROWS_WITHOUT_EVIDENCE', 1]])

    def test_zero_coverage_is_explicit_noop(self):
        sub = frame(base_rows())
        degraded = []
        out, stats = formula_order(sub, {}, calc_f, degraded=degraded)
        self.assertTrue(out.equals(sub))
        self.assertEqual(stats['changed_rows'], 0)
        self.assertEqual(stats['rows_without_formula'], 2)

    def test_membership_is_preserved(self):
        sub = frame(base_rows())
        out, _ = formula_order(sub, {'m1': ['C3H8O'], 'm2': ['C2H6O']}, calc_f)
        for i in out.index:
            self.assertEqual(sorted(out.at[i, 'smiles'].split(';')), sorted(sub.at[i, 'smiles'].split(';')))

    def test_str_key_lookup(self):
        sub = frame(base_rows())
        out, stats = formula_order(sub, {'1': [], 'm1': ['CH4O']}, calc_f)
        self.assertEqual(out.at[0, 'smiles'].split(';')[0], 'CO')


class TestFormulaSwapFirst(unittest.TestCase):
    def test_swap_promotes_first_match_only(self):
        from wave9_runtime import formula_swap_first
        sub = frame([{'molecule_id': 'm1', 'smiles': ';'.join(['CCCCO', 'CCCO', 'CO', 'CCO'] + ['C'] * 21)}])
        out, stats = formula_swap_first(sub, {'m1': ['CH4O']}, calc_f)
        self.assertEqual(out.at[0, 'smiles'].split(';')[:3], ['CO', 'CCCCO', 'CCCO'])
        self.assertEqual(stats['changed_rows'], 1)

    def test_position_zero_already_matching_untouched(self):
        from wave9_runtime import formula_swap_first
        sub = frame([{'molecule_id': 'm2', 'smiles': ';'.join(['CO', 'CCCCO'] + ['C'] * 23)}])
        out, stats = formula_swap_first(sub, {'m2': ['CH4O']}, calc_f)
        self.assertTrue(out.equals(sub))
        self.assertEqual(stats['changed_rows'], 0)

    def test_no_formula_or_no_match_is_noop(self):
        from wave9_runtime import formula_swap_first
        sub = frame([{'molecule_id': 'm3', 'smiles': ';'.join(['CCCCO', 'CCCO'] + ['C'] * 23)},
                     {'molecule_id': 'm4', 'smiles': ';'.join(['CCCCO', 'CCCO'] + ['C'] * 23)}])
        degraded = []
        out, stats = formula_swap_first(sub, {'m4': ['C6H12O6']}, calc_f, degraded)
        self.assertTrue(out.equals(sub))
        self.assertEqual(stats, {'changed_rows': 0, 'rows_without_formula': 1, 'rows_without_match': 1})
        self.assertEqual(degraded, [['FORMULA_ROWS_WITHOUT_EVIDENCE', 1]])


class TestRefill(unittest.TestCase):
    def test_refill_by_mass(self):
        base = ['CCO'] + ['CO'] + ['C'] * 3  # 1 real + padding
        kept, short = refill_by_pool_mass(base, 60.0, pool(), canon_key)
        self.assertEqual(len(kept), 25)
        self.assertEqual(short, 19)  # CO preservado + C único + 4 novos do pool por massa
        self.assertEqual(kept[0], 'CO')  # CCO removido; ordem preservada
        self.assertIn('CCCCO', kept)

    def test_short_pool_pads_cco_explicitly(self):
        base = ['CO'] + ['CCO'] * 24
        tiny = {'mass': [32.0], 'smiles': ['CO']}
        kept, short = refill_by_pool_mass(base, 32.0, tiny, canon_key)
        self.assertEqual(len(kept), 25)
        self.assertEqual(short, 24)
        self.assertEqual(kept, ['CO'] + ['CCO'] * 24)

    def test_missing_target_pads_without_mass(self):
        base = ['CO'] + ['CCO'] * 24
        kept, short = refill_by_pool_mass(base, None, pool(), canon_key)
        self.assertEqual(short, 24)
        self.assertEqual(kept[:1], ['CO'])

    def test_nan_target_pads_without_mass(self):
        kept, short = refill_by_pool_mass(['CO'] + ['CCO'] * 24, float('nan'), pool(), canon_key)
        self.assertEqual(short, 24)

    def test_preserved_prefix_never_reordered(self):
        base = ['CCCCO', 'CO', 'CCO', 'CCCO'] + ['C'] * 21
        kept, _ = refill_by_pool_mass(base, 88.0, pool(), canon_key)
        self.assertEqual(kept[:3], ['CCCCO', 'CO', 'CCCO'])


class TestDedupRows(unittest.TestCase):
    def recs(self):
        return [{'mid': 'm1', 'target': 60.0}, {'mid': 'm2', 'target': 74.0}]

    def test_dedup_refills_from_pool(self):
        sub = frame(base_rows())
        degraded = []
        out, stats = dedup_rows(sub, self.recs(), big_pool(), canon_key, degraded)
        for i in out.index:
            self.assertEqual(len(out.at[i, 'smiles'].split(';')), 25)
        self.assertEqual(stats['padded_slots'], 0)
        self.assertEqual(degraded, [])

    def test_missing_mass_degrades_without_abort(self):
        sub = frame(base_rows())
        degraded = []
        out, stats = dedup_rows(sub, [{'mid': 'm1', 'target': 60.0}, {'mid': 'm2', 'target': float('nan')}],
                                big_pool(), canon_key, degraded)
        self.assertEqual(stats['rows_without_mass'], 1)
        self.assertIn(['NO_VALID_MASS', 1], degraded)
        self.assertIn(['DEDUP_SHORTFALL_PADDED', 21], degraded)  # 25 - 4 identidades reais
        self.assertEqual(len(out.at[1, 'smiles'].split(';')), 25)

    def test_missing_rec_degrades_without_abort(self):
        sub = frame(base_rows())
        degraded = []
        out, stats = dedup_rows(sub, [], big_pool(), canon_key, degraded)
        self.assertEqual(stats['rows_without_mass'], 2)
        self.assertEqual(len(out.at[0, 'smiles'].split(';')), 25)


class TestLenientEvidence(unittest.TestCase):
    def row(self, mid='m1', adduct='[M+H]+', mode='positive', mz=(100.0, 200.0), ints=(0.5, 1.0), pre=500.0):
        return {'molecule_id': mid, 'adduct': adduct, 'ionization_mode': mode,
                'ms2_mzs': list(mz), 'ms2_normalized_intensities': list(ints), 'precursor_mz': pre}

    def test_skips_bad_rows_with_record(self):
        degraded = []
        rows = [self.row(), self.row(mid='m2', adduct='[M+Xq]?'), self.row(mid='m3', mode='negative'),
                self.row(mid='m4', mz=(1.0,), ints=(1.0, 2.0))]
        groups = split_spectra_lenient(rows, degraded)
        self.assertEqual([g['molecule_id'] for g in groups], ['m1'])
        self.assertEqual(degraded, [['SPECTRA_ROWS_SKIPPED', 3]])

    def test_matches_strict_on_clean_rows(self):
        rows = [self.row(), self.row(adduct='[M+Na]+'), self.row(mid='m2', adduct='[M-H]-', mode='negative')]
        self.assertEqual(split_spectra_lenient(rows), split_spectra(rows))

    def test_duplicate_groups_skipped(self):
        degraded = []
        groups = [{'molecule_id': 'm1', 'adduct': '[M+H]+', 'mode': 'positive', 'formulas': ['C2H6O', 'CH4O']},
                  {'molecule_id': 'm1', 'adduct': '[M+H]+', 'mode': 'positive', 'formulas': ['C3H8O']}]
        combined = combine_formula_evidence_lenient(groups, degraded)
        self.assertEqual(combined['m1'][0], 'C2H6O')
        self.assertEqual(degraded, [['DUPLICATE_ADDUCT_GROUPS_SKIPPED', 1]])

    def test_matches_strict_without_duplicates(self):
        groups = [{'molecule_id': 'm1', 'adduct': '[M+H]+', 'mode': 'positive', 'formulas': ['C2H6O', 'CH4O']},
                  {'molecule_id': 'm1', 'adduct': '[M+Na]+', 'mode': 'positive', 'formulas': ['C2H6O', 'C3H8O']}]
        self.assertEqual(combine_formula_evidence_lenient(groups), combine_formula_evidence(groups))


class TestEndToEndPublication(unittest.TestCase):
    """Caminho completo do tail Wave9 com dados sintéticos: degradar e publicar."""

    def publish_selected(self, selected, sample_ids, degraded, formulas):
        from rdkit import Chem

        def valid(s):
            return Chem.MolFromSmiles(s) is not None
        with tempfile.TemporaryDirectory() as td:
            pub = AtomicSubmission(td)
            pub.begin()
            proof = dict(variant='synthetic', degraded=degraded, msbuddy_available=bool(formulas))
            report = pub.publish(selected.to_dict('records'), sample_ids, valid, proof)
            data = (pathlib.Path(td) / 'submission.csv').read_bytes()
        return report, data

    def test_degraded_msbuddy_still_publishes(self):
        sub = frame(base_rows())
        degraded = [['MSBUDDY_UNAVAILABLE', "AssertionError('no wheels')"]]
        selected, stats = formula_order(sub, {}, calc_f, degraded=degraded)
        report, data = self.publish_selected(selected, ['m1', 'm2'], degraded, {})
        self.assertEqual(report['rows'], 2)
        self.assertEqual(report['degraded'][0][0], 'MSBUDDY_UNAVAILABLE')
        self.assertIn(b'm1', data)

    def test_low_coverage_publishes(self):
        sub = frame(base_rows())
        degraded = []
        selected, _ = formula_order(sub, {'m1': ['CH4O']}, calc_f, degraded=degraded)  # 50%
        report, _ = self.publish_selected(selected, ['m1', 'm2'], degraded, {'m1': ['CH4O']})
        self.assertEqual(report['rows'], 2)
        self.assertEqual(report['degraded'], [['FORMULA_ROWS_WITHOUT_EVIDENCE', 1]])

    def test_structural_failure_still_blocks(self):
        bad = frame([{'molecule_id': 'm1', 'smiles': ';'.join(['INVALID'] * 25)}])
        from rdkit import Chem
        with tempfile.TemporaryDirectory() as td:
            pub = AtomicSubmission(td)
            pub.begin()
            with self.assertRaises(ValueError):
                pub.publish(bad.to_dict('records'), ['m1'], lambda s: Chem.MolFromSmiles(s) is not None, {})
            self.assertFalse((pathlib.Path(td) / 'submission.csv').exists())


def load(tag):
    folder = R / f'kpush_wave9_{tag}'
    meta = json.loads((folder / 'kernel-metadata.json').read_text())
    nb = json.loads((folder / meta['code_file']).read_text())
    return folder, meta, nb


def code_text(nb, skip_writefile=False):
    parts = []
    for c in nb['cells']:
        if c['cell_type'] != 'code':
            continue
        s = ''.join(c['source'])
        if skip_writefile and s.startswith('%%writefile '):
            continue
        parts.append(s)
    return '\n'.join(parts)


class TestStaticIsolation(unittest.TestCase):
    FORBIDDEN = ['MSBUDDY_COVERAGE_FAILED', 'FORMULA_IDS_DIFFER_FROM_SAMPLE', 'FORMULA_ID_COUNT_MISMATCH',
                 'ADDUCT_FORMULA_COVERAGE', 'variants=dict(', 'records[name]',
                 'NOT_ENOUGH_UNIQUE_POOL_CANDIDATES', 'FORMULA_CHANGED_MEMBERSHIP', '0.975',
                 'submission_blend_control', 'audit_blend_control', '== 400', '>= 390']

    def test_forbidden_tokens_absent(self):
        for tag in TAGS:
            _, _, nb = load(tag)
            text = code_text(nb)
            for token in self.FORBIDDEN:
                self.assertNotIn(token, text, (tag, token))

    def test_validation_only_inside_publisher(self):
        for tag in TAGS:
            _, _, nb = load(tag)
            for c in nb['cells']:
                if c['cell_type'] != 'code':
                    continue
                s = ''.join(c['source'])
                if s.startswith('%%writefile atomic_submission.py'):
                    continue
                self.assertNotIn('AtomicSubmission.validate', s, tag)

    def test_publisher_cardinality(self):
        for tag in TAGS:
            _, _, nb = load(tag)
            text = code_text(nb)
            self.assertEqual(text.count('publisher.publish('), 1, tag)
            self.assertEqual(text.count('publisher.begin('), 1, tag)

    def test_mechanism_separation(self):
        expectations = {
            'top1': dict(dedup=False, adduct=False), 'adduct': dict(dedup=False, adduct=True),
            'formula_dedup': dict(dedup=True, adduct=False), 'top1_dedup': dict(dedup=True, adduct=False),
            'adduct_dedup': dict(dedup=True, adduct=True)}
        for tag, exp in expectations.items():
            _, _, nb = load(tag)
            wiring = code_text(nb, skip_writefile=True)
            self.assertEqual('dedup_sub' in wiring, exp['dedup'], tag)
            self.assertEqual('adduct_formulas' in wiring, exp['adduct'], tag)

    def test_metadata_and_safety_guards(self):
        ids = set()
        for tag in TAGS:
            _, meta, nb = load(tag)
            validate_kernel(meta, nb)
            validate_publication_safety(nb)
            self.assertEqual(meta['code_file'], 'wave9.ipynb')
            self.assertNotIn(meta['id'], ids)
            ids.add(meta['id'])
            self.assertIn(f"VARIANT={tag!r}", code_text(nb))

    WAVE9_FROZEN_RUNTIME_SHA = '5bb4cc6fdc356c0c134f4cd6295f286eead99e192119ed0a53c40ab2e8fc9c40'

    def test_embedded_runtime_is_single_source_of_truth(self):
        import hashlib
        evidence = (R / 'formula_evidence.py').read_text()
        for tag in TAGS:
            _, _, nb = load(tag)
            embedded = [c for c in nb['cells'] if c['cell_type'] == 'code'
                        and ''.join(c['source']).startswith('%%writefile wave9_runtime.py')]
            self.assertEqual(len(embedded), 1, tag)
            # Wave9 já submetida/ranqueada: runtime embutido é artefato histórico congelado.
            self.assertEqual(hashlib.sha256(''.join(embedded[0]['source']).encode()).hexdigest(),
                             self.WAVE9_FROZEN_RUNTIME_SHA, tag)
            if tag.startswith('adduct'):
                ev = [c for c in nb['cells'] if c['cell_type'] == 'code'
                      and ''.join(c['source']).startswith('%%writefile formula_evidence.py')]
                self.assertEqual(''.join(ev[0]['source']), '%%writefile formula_evidence.py\n' + evidence)

    def test_msbuddy_exception_degrades_without_raise(self):
        for tag in TAGS:
            _, _, nb = load(tag)
            msbuddy = [c for c in nb['cells'] if c['cell_type'] == 'code'
                       and 'MSBUDDY_UNAVAILABLE' in ''.join(c['source'])]
            self.assertEqual(len(msbuddy), 1, tag)
            src = ''.join(msbuddy[0]['source'])
            tree = ast.parse(src)
            handlers = [h for node in ast.walk(tree) if isinstance(node, ast.Try) for h in node.handlers]
            self.assertTrue(handlers, tag)
            degrade_handlers = 0
            for h in handlers:
                for node in ast.walk(h):
                    self.assertNotIsInstance(node, ast.Raise, tag)
                if 'MSBUDDY_UNAVAILABLE' in ast.unparse(h):
                    degrade_handlers += 1
            self.assertEqual(degrade_handlers, 1, tag)

    def test_adduct_exception_degrades_without_raise(self):
        for tag in ('adduct', 'adduct_dedup'):
            _, _, nb = load(tag)
            cells = [c for c in nb['cells'] if c['cell_type'] == 'code'
                     and 'ADDUCT_EVIDENCE_UNAVAILABLE' in ''.join(c['source'])]
            self.assertEqual(len(cells), 1, tag)
            tree = ast.parse(''.join(cells[0]['source']))
            for node in ast.walk(tree):
                if isinstance(node, ast.Try):
                    for h in node.handlers:
                        for inner in ast.walk(h):
                            self.assertNotIsInstance(inner, ast.Raise, tag)


if __name__ == '__main__':
    unittest.main()

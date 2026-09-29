"""Selected-only CASMI postprocessing; no model/network dependencies.
Missing scientific evidence is explicit and row-local. Runtime/provider failures remain fatal.
"""
from collections.abc import Mapping
from pathlib import Path
import datetime, json, math, traceback
from atomic_submission import AtomicSubmission

CONTRACT = 'selected-only-v1'
ROUTES = {
    'formula_dedup': ('legacy', 5, True),
    'top1': ('legacy', 1, False),
    'top1_dedup': ('legacy', 1, True),
    'adduct': ('adduct', 5, False),
    'adduct_dedup': ('adduct', 5, True),
}

def normalized_id(value):
    if value is None or isinstance(value, bool): raise ValueError('INVALID_MOLECULE_ID')
    if isinstance(value, float) and not math.isfinite(value): raise ValueError('INVALID_MOLECULE_ID')
    value = str(value)
    if not value.strip(): raise ValueError('EMPTY_MOLECULE_ID')
    return value

def normalize_records(records, sample_ids):
    ids = [normalized_id(x) for x in sample_ids]
    if not ids or len(ids) != len(set(ids)): raise ValueError('SAMPLE_IDS_INVALID')
    by_id = {}
    for row in records:
        if set(row) != {'molecule_id', 'smiles'}: raise ValueError('CSV_SCHEMA')
        mid = normalized_id(row['molecule_id'])
        if mid in by_id: raise ValueError('DUPLICATE_PREDICTION_ID')
        if not isinstance(row['smiles'], str): raise ValueError('CSV_NULL_OR_DTYPE')
        by_id[mid] = {'molecule_id': mid, 'smiles': row['smiles']}
    if set(by_id) != set(ids): raise ValueError('PREDICTION_IDS_DIFFER_FROM_SAMPLE')
    return [by_id[mid] for mid in ids], ids

def formula_values(values):
    if not isinstance(values, (list, tuple)): raise ValueError('FORMULAS_MUST_BE_LIST')
    out = []
    for value in values:
        if value is None or (isinstance(value, float) and math.isnan(value)): continue
        if not isinstance(value, str): raise ValueError('FORMULA_VALUE_TYPE')
        value = value.replace(' ', '').rstrip('+-')
        if value.lower() in {'', 'nan', 'none'}: continue
        out.append(value)
    return out

def normalize_formulas(evidence, ids):
    if not isinstance(evidence, Mapping): raise ValueError('FORMULA_MAP_TYPE')
    out = {}
    for key, values in evidence.items():
        mid = normalized_id(key)
        if mid in out: raise ValueError('FORMULA_ID_COLLISION')
        out[mid] = formula_values(values)
    # An explicit empty list means no evidence. Missing keys mean a broken provider contract.
    if set(out) != set(ids): raise ValueError('FORMULA_IDS_DIFFER_FROM_SAMPLE')
    return out

def select_records(variant, base_records, sample_ids, *, legacy_provider=None,
                   adduct_provider=None, dedup_provider=None, calc_formula=None,
                   emit=None):
    emit = emit or (lambda *_: None)
    if variant not in ROUTES: raise ValueError('UNKNOWN_VARIANT')
    evidence_kind, topk, needs_dedup = ROUTES[variant]
    emit('normalize_input', {})
    base, ids = normalize_records(base_records, sample_ids)
    selected = [dict(row) for row in base]
    if needs_dedup:
        emit('dedup', {})
        if dedup_provider is None: raise ValueError('DEDUP_PROVIDER_REQUIRED')
        selected, _ = normalize_records(dedup_provider(selected), ids)
    provider = legacy_provider if evidence_kind == 'legacy' else adduct_provider
    if provider is None or calc_formula is None: raise ValueError('FORMULA_PROVIDER_REQUIRED')
    emit('formula_' + evidence_kind, {})
    # Exceptions are never converted into a silently substituted baseline.
    formulas = normalize_formulas(provider(), ids)
    missing = [mid for mid in ids if not formulas[mid]]
    emit('rerank', {'molecules_without_formula': len(missing)})
    for row in selected:
        candidates = row['smiles'].split(';')
        allowed = set(formulas[row['molecule_id']][:topk])
        if allowed:
            order = sorted(range(len(candidates)), key=lambda i: (calc_formula(candidates[i]) not in allowed, i))
            row['smiles'] = ';'.join(candidates[i] for i in order)
        # Empty evidence intentionally preserves this row's order; all other rows still execute.
    report = {
        'pipeline_contract': CONTRACT, 'variant': variant, 'formula_source': evidence_kind,
        'topk': topk, 'dedup_executed': needs_dedup, 'molecules': len(ids),
        'formula_coverage': (len(ids)-len(missing))/len(ids),
        'no_formula_ids': missing, 'no_formula_count': len(missing),
        'selected_vs_base_changed_rows': sum(a['smiles'] != b['smiles'] for a,b in zip(base, selected)),
        'formula_policy': 'preserve_row_order_when_successful_provider_returns_no_evidence',
        'runtime_failure_policy': 'abort_no_csv',
    }
    return selected, report

def publish_selected(directory, variant, base_records, sample_ids, *, smiles_validator,
                     legacy_provider=None, adduct_provider=None, dedup_provider=None,
                     calc_formula=None, extra_proof=None, publication_fault=None):
    publisher = AtomicSubmission(directory)
    publisher.begin()  # remove stale output before selecting or executing any provider
    failure_path = Path(directory)/'selected_failure.json'
    if failure_path.exists(): failure_path.unlink()
    log_path = Path(directory)/'selected_stage_events.jsonl'
    log_path.write_text('')
    current = 'begin'
    def emit(stage, details):
        nonlocal current
        current = stage
        with log_path.open('a') as stream:
            stream.write(json.dumps({'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
                                     'stage':stage, **details})+'\n')
    try:
        selected, report = select_records(variant, base_records, sample_ids,
            legacy_provider=legacy_provider, adduct_provider=adduct_provider,
            dedup_provider=dedup_provider, calc_formula=calc_formula, emit=emit)
        proof = dict(extra_proof or {})
        proof.update(report)
        emit('publish_selected', {'variant':variant,'formula_coverage':report['formula_coverage']})
        # Sole final publication. No auxiliary branch can veto a structurally valid selected result.
        return publisher.publish(selected, [normalized_id(x) for x in sample_ids],
                                 smiles_validator, proof, fault=publication_fault)
    except BaseException as error:
        publisher.begin()
        failure={'stage':current,'type':type(error).__name__,'message':str(error),
                 'traceback':traceback.format_exc()}
        (Path(directory)/'selected_failure.json').write_text(json.dumps(failure,indent=2))
        raise

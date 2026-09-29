"""Wave9 fault-tolerant mechanism runtime (correção E031).

Contratos:
- Cobertura científica (fórmulas msbuddy) NUNCA é trava estrutural: moléculas sem
  evidência recebem no-op explícito e o caso é registrado em `degraded`.
- Nenhuma função aborta por condição científica legítima (cobertura baixa, massa
  ausente, pool curto, aduto não parseável). Falhas estruturais continuam com o
  publisher atômico (atomic_submission.py), único ponto de abortar.
- Degradação nunca é silenciosa: toda entrada em `degraded` vai para a prova e
  para o log do kernel.
- Funções puras (sem engine/rede); o notebook injeta dependências como parâmetros,
  o que permite teste local sem Kaggle.
"""
import math


def formula_order(sub, formulas_by_id, calc_f, topk=5, degraded=None):
    """Reordena os 25 candidatos promovendo os que batem com a fórmula (top-k).

    Ordem estável: candidatos promovidos primeiro (índice original como desempate),
    demais mantêm a ordem W088. É permutação: nunca altera o conjunto da linha.
    Molécula sem fórmula: no-op explícito, contado, nunca um aborto.
    """
    result = sub.copy()
    changed = no_formula = 0
    for idx, row in result.iterrows():
        base = row.smiles.split(';')
        formulas = set((formulas_by_id.get(row.molecule_id)
                        or formulas_by_id.get(str(row.molecule_id)) or [])[:topk])
        if not formulas:
            no_formula += 1
            continue  # no-op explícito por molécula; nunca aborta o lote
        order = sorted(range(len(base)), key=lambda j: (calc_f(base[j]) not in formulas, j))
        out = [base[j] for j in order]
        changed += out != base
        result.at[idx, 'smiles'] = ';'.join(out)
    stats = {'changed_rows': int(changed), 'rows_without_formula': int(no_formula)}
    if degraded is not None and no_formula:
        degraded.append(['FORMULA_ROWS_WITHOUT_EVIDENCE', int(no_formula)])
    return result, stats


def clean_existing(base, canon_key):
    """Remove padding CCO e duplicatas canônicas preservando a ordem real."""
    kept, seen = [], set()
    for smi in base:
        if smi == 'CCO':  # sentinela de padding W088, não candidato inferido
            continue
        key = canon_key(smi)
        if key and key not in seen:
            seen.add(key)
            kept.append(smi)
    return kept, seen


def refill_by_pool_mass(base, target, pool, canon_key):
    """Preenche até 25 identidades únicas por proximidade de massa no mesmo pool.

    Massa ausente/não finita: pula o refill por massa. Pool insuficiente: completa
    com padding CCO documentado e reporta o shortfall. Nunca aborta; a ordem das
    identidades preservadas nunca muda.
    """
    import numpy as np
    kept, seen = clean_existing(base, canon_key)
    preserved = list(kept)
    if len(kept) < 25 and target is not None and math.isfinite(float(target)):
        order = np.argsort(np.abs(np.asarray(pool['mass']) - float(target)), kind='mergesort')
        for ci in order:
            if len(kept) == 25:
                break
            smi = str(pool['smiles'][int(ci)])
            if smi == 'CCO':
                continue
            key = canon_key(smi)
            if key and key not in seen:
                seen.add(key)
                kept.append(smi)
    shortfall = 25 - len(kept)
    if shortfall > 0:
        kept.extend(['CCO'] * shortfall)  # padding documentado, estruturalmente válido
    assert kept[:len(preserved)] == preserved, 'PRESERVED_PREFIX_CHANGED'
    assert len(kept) == 25 and all(kept), 'PADDING_CONTRACT'
    return kept, shortfall


def dedup_rows(sub, recs, pool, canon_key, degraded=None):
    """Dedup/refill por linha: faltas degradam com registro, nunca abortam."""
    rec_by_mid = {r['mid']: r for r in recs}
    result = sub.copy()
    changed = padded = no_mass = 0
    for idx, row in result.iterrows():
        base = row.smiles.split(';')
        kept, _seen = clean_existing(base, canon_key)
        if len(kept) == 25:
            out = base
        else:
            rec = rec_by_mid.get(row.molecule_id)
            if rec is None:
                rec = rec_by_mid.get(str(row.molecule_id))
            target = rec.get('target') if rec else None
            try:
                target = float(target) if target is not None else None
            except (TypeError, ValueError):
                target = None
            if target is None or not math.isfinite(target):
                no_mass += 1
                target = None
            out, short = refill_by_pool_mass(base, target, pool, canon_key)
            padded += short
        changed += out != base
        result.at[idx, 'smiles'] = ';'.join(out)
    stats = {'changed_rows': int(changed), 'padded_slots': int(padded), 'rows_without_mass': int(no_mass)}
    if degraded is not None:
        if padded:
            degraded.append(['DEDUP_SHORTFALL_PADDED', int(padded)])
        if no_mass:
            degraded.append(['NO_VALID_MASS', int(no_mass)])
    return result, stats


def formula_swap_first(sub, formulas_by_id, calc_f, degraded=None):
    """Promove o primeiro candidato que casa com a fórmula rank1 para a posição 0.

    Conservador: se a posição 0 já casa ou nenhum candidato casa, a linha fica
    intacta. Responde de onde vem o ganho do top1 (posição 1 vs reordenação ampla).
    """
    result = sub.copy()
    changed = no_formula = no_hit = 0
    for idx, row in result.iterrows():
        base = row.smiles.split(';')
        formulas = set((formulas_by_id.get(row.molecule_id)
                        or formulas_by_id.get(str(row.molecule_id)) or [])[:1])
        if not formulas:
            no_formula += 1
            continue
        if calc_f(base[0]) in formulas:
            continue  # posição 0 já correta
        hit = next((j for j in range(1, len(base)) if calc_f(base[j]) in formulas), None)
        if hit is None:
            no_hit += 1
            continue
        out = [base[hit]] + base[:hit] + base[hit + 1:]
        result.at[idx, 'smiles'] = ';'.join(out)
        changed += 1
    stats = {'changed_rows': int(changed), 'rows_without_formula': int(no_formula),
             'rows_without_match': int(no_hit)}
    if degraded is not None and no_formula:
        degraded.append(['FORMULA_ROWS_WITHOUT_EVIDENCE', int(no_formula)])
    return result, stats

#!/usr/bin/env python3
"""Wave9 — cinco kernels com isolamento de falhas (correção E031).

Base: engine idêntico ao Wave8 (células 3..17, já reproduzido na conta). Mudanças:
- um mecanismo por kernel; só o mecanismo escolhido é validado e publicado;
- cobertura científica registrada, nunca trava estrutural;
- msbuddy/dedup/evidência por aduto degradam com registro explícito;
- runtime testado localmente (wave9_runtime.py) embutido via %%writefile.
Nenhum submit automático. Saída: kpush_wave9_*/ + wave9_plan.json.
"""
import ast, copy, json, pathlib

R = pathlib.Path('/home/user')
BASE = json.loads((R / 'kpush_wave8_atomic_combo_cpu/wave8.ipynb').read_text())
META0 = json.loads((R / 'kpush_wave8_atomic_combo_cpu/kernel-metadata.json').read_text())
RUNTIME = (R / 'wave9_runtime.py').read_text()
EVIDENCE = (R / 'formula_evidence.py').read_text()

SETTINGS = {
    'adduct': dict(
        suffix='adduct', needs_dedup=False, needs_adduct=True, topk=5,
        base_expr="subs['blend']", formulas='adduct_formulas',
        question='Separar espectros por aduto/polaridade melhora a fórmula e o ranking?',
        decision='Se ganhar, adotar evidência por grupo; sem ganho, não promover.'),
    'adduct_dedup': dict(
        suffix='adduct-dedup', needs_dedup=True, needs_adduct=True, topk=5,
        base_expr='dedup_sub', formulas='adduct_formulas',
        question='Evidência por aduto também melhora a combinação com refill?',
        decision='Comparar com adduct sem refill e combinado top5 legado; escolher mecanismo demonstrado.'),
    'formula_dedup': dict(
        suffix='formula-dedup', needs_dedup=True, needs_adduct=False, topk=5,
        base_expr='dedup_sub', formulas='buddy_formulas',
        question='Fórmula top5 após dedup/refill supera o W088 blend 0.341?',
        decision='Manter combinação apenas com ganho confiável sobre a referência.'),
    'top1': dict(
        suffix='top1', needs_dedup=False, needs_adduct=False, topk=1,
        base_expr="subs['blend']", formulas='buddy_formulas',
        question='Top1 msbuddy reduz promoções espúrias em relação à evidência top5?',
        decision='Comparar ao W088 blend e ao top1+dedup; promover somente ganho confiável.'),
    'top1_dedup': dict(
        suffix='top1-dedup', needs_dedup=True, needs_adduct=False, topk=1,
        base_expr='dedup_sub', formulas='buddy_formulas',
        question='Top1 aplicado após refill supera o combinado top5+dedup?',
        decision='Escolher política top1/top5 após notas atribuíveis, sem varrer pesos.'),
}


def cell(src, markdown=False):
    return {'cell_type': 'markdown' if markdown else 'code', 'metadata': {},
            'execution_count': None, 'outputs': [], 'source': src.splitlines(keepends=True)}


def msbuddy_try_block():
    """Extrai o bloco try do msbuddy do Wave8 (idêntico), sem o except original."""
    src = ''.join(BASE['cells'][18]['source'])
    start = src.index('# --- msbuddy')
    end = src.index('except Exception as _e:')
    block = src[start:end]
    assert 'try:' in block, 'MSBUDDY_TRY_BLOCK_EXTRACTION_FAILED'
    return block.rstrip() + '\n'


MSBUDDY_CELL = '''from rdkit import Chem, RDLogger
from pathlib import Path as _MPath
from functools import lru_cache
from rdkit.Chem.rdMolDescriptors import CalcMolFormula as _CalcFormula
RDLogger.DisableLog('rdApp.*')
from wave9_runtime import formula_order, dedup_rows
te = E.pq.read_table(os.path.join(COMP,'test.parquet')).to_pandas()
mols = list(te.groupby('molecule_id'))
buddy_formulas = {}
DEGRADED = []  # registro explícito de degradação; publicado na prova, nunca silencioso
@lru_cache(maxsize=None)
def _calc_f(smi):
    try:
        m = Chem.MolFromSmiles(smi)
        return _CalcFormula(m).rstrip('+-') if m is not None else None
    except Exception:
        return None
''' + msbuddy_try_block() + '''except Exception as _e:
    buddy_formulas = {}
    DEGRADED.append(['MSBUDDY_UNAVAILABLE', repr(_e)])
    print('[DEGRADED] msbuddy unavailable:', repr(_e), flush=True)

samp = pd.read_csv(os.path.join(COMP,'sample_submission.csv'), dtype={'molecule_id':str})
sample_ids = samp.molecule_id.tolist()
_formula_keys = {str(k) for k in buddy_formulas}
_missing = sum(1 for i in sample_ids if str(i) not in _formula_keys)
if _missing:
    DEGRADED.append(['FORMULA_IDS_MISSING', _missing])
coverage = sum(bool(buddy_formulas.get(i) or buddy_formulas.get(str(i))) for i in sample_ids) / max(1, len(sample_ids))
# Cobertura é métrica científica registrada; NÃO é trava estrutural (correção E031).
print('MSBUDDY_COVERAGE', coverage, 'MISSING_IDS', _missing, flush=True)
'''

ADDUCT_CELL = '''from formula_evidence import split_spectra_lenient, combine_formula_evidence_lenient
adduct_formulas = {}
adduct_group_count = 0
adduct_coverage = 0.0
try:
    adduct_groups = split_spectra_lenient(te.to_dict('records'), DEGRADED)
    adduct_group_count = len(adduct_groups)
    adduct_features = []
    for i, g in enumerate(adduct_groups):
        adduct_features.append(MetaFeature(identifier=i, mz=g['precursor_mz'], charge=g['charge'], adduct=g['adduct'],
                              ms2=Spectrum(mz_array=np.asarray(g['ms2_mzs'], float), int_array=np.asarray(g['ms2_normalized_intensities'], float))))
    try:
        del _eng  # libera memória antes do segundo motor
    except NameError:
        pass
    adduct_engine = Msbuddy(_cfg)
    adduct_engine.add_data(adduct_features)
    adduct_engine.annotate_formula()
    adduct_summary = adduct_engine.get_summary()
    if len(adduct_summary) != len(adduct_groups):
        DEGRADED.append(['ADDUCT_SUMMARY_COUNT_MISMATCH', len(adduct_summary)])
    formula_groups = []
    for g, res in zip(adduct_groups, adduct_summary):
        values = [res.get(f'formula_rank_{k}') for k in range(1, 6)]
        formula_groups.append(dict(molecule_id=g['molecule_id'], adduct=g['adduct'], mode=g['mode'],
                                   formulas=[str(f).replace(' ', '').rstrip('+-') for f in values if f]))
    adduct_formulas = combine_formula_evidence_lenient(formula_groups, DEGRADED)
    adduct_coverage = sum(bool(adduct_formulas.get(i) or adduct_formulas.get(str(i))) for i in sample_ids) / max(1, len(sample_ids))
    from pathlib import Path
    import json
    Path('formula_adducts.json').write_text(json.dumps(adduct_formulas, indent=2))
    print('ADDUCT_EVIDENCE_READY', adduct_group_count, adduct_coverage, flush=True)
except Exception as _e:
    adduct_formulas = {}
    adduct_group_count = 0
    adduct_coverage = 0.0
    DEGRADED.append(['ADDUCT_EVIDENCE_UNAVAILABLE', repr(_e)])
    print('[DEGRADED] adduct evidence unavailable:', repr(_e), flush=True)
'''

DEDUP_CELL = '''# Dedup/refill tolerante (correção E031): shortfall ou massa ausente degradam
# com registro explícito; nunca abortam a publicação do mecanismo escolhido.
dedup_sub, dedup_stats = dedup_rows(subs['blend'], recs, E.POOL, E.canon_key, DEGRADED)
print('DEDUP_STATS', dedup_stats, flush=True)
'''

PROOF_TAIL = '''
import hashlib, json
from pathlib import Path
@lru_cache(maxsize=None)
def valid_smiles(s): return Chem.MolFromSmiles(s) is not None

def file_sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1024*1024), b''): h.update(block)
    return h.hexdigest()

# Correção E031: somente o mecanismo escolhido é validado e publicado.
# Nenhum ramo auxiliar: uma variante não submetida não pode bloquear o lote.
proof = dict(variant=VARIANT, cpu_only=True, full_pipeline=True, own_dataset_inputs=False,
             expected_rows=len(sample_ids), formula_coverage=coverage,
             msbuddy_available=bool(buddy_formulas), degraded=DEGRADED,
             mechanism=sel_stats,
             test_sha256=file_sha(os.path.join(COMP,'test.parquet')),
             sample_sha256=file_sha(os.path.join(COMP,'sample_submission.csv')),
             rdkit_version=rdkit.__version__, artifacts={})
raw = selected.to_csv(index=False).encode('utf-8')
Path('audit_selected.csv').write_bytes(raw)
proof['artifacts']['selected'] = dict(file='audit_selected.csv', sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))
blend_raw = subs['blend'].to_csv(index=False).encode('utf-8')
Path('audit_blend.csv').write_bytes(blend_raw)
proof['artifacts']['blend'] = dict(file='audit_blend.csv', sha256=hashlib.sha256(blend_raw).hexdigest(), bytes=len(blend_raw))
proof['selected_vs_blend_changed_rows'] = int(sum(a != b for a, b in zip(selected.smiles, subs['blend'].smiles)))
Path('lineage_before_publish.json').write_text(json.dumps(proof, indent=2))
print('PREPUBLICATION_VALIDATED', json.dumps(proof), flush=True)
'''

PUBLISH_CELL = '''# Última célula computacional. Publicação atômica: se a validação estrutural
# falhar, nenhum submission.csv é publicado (sem fallback silencioso).
publication = publisher.publish(selected.to_dict('records'), sample_ids, valid_smiles, proof)
print('ATOMIC_PUBLICATION_COMPLETE', json.dumps(publication), flush=True)
'''

FORBIDDEN = [
    'MSBUDDY_COVERAGE_FAILED', 'FORMULA_IDS_DIFFER_FROM_SAMPLE', 'FORMULA_ID_COUNT_MISMATCH',
    'ADDUCT_FORMULA_COVERAGE', "ADDUCT_FORMULA_IDS',", 'variants=dict(', 'records[name]',
    'NOT_ENOUGH_UNIQUE_POOL_CANDIDATES', 'FORMULA_CHANGED_MEMBERSHIP', 'ADDUCT_SUMMARY_COUNT)',
    '== 400', '>= 390', '0.975', 'audit_blend_control', 'submission_blend_control',
]

plans = []
for tag, cfg in SETTINGS.items():
    nb = copy.deepcopy(BASE)
    nb['cells'] = nb['cells'][:18]  # title..engine (0..17); descarta cauda Wave8
    nb['cells'][0] = cell(
        f"# Wave9 — isolamento de falhas: {tag}\n"
        f"{cfg['question']}\n"
        f"{cfg['decision']}\n"
        'Correção E031: cobertura científica registrada (não trava); só o mecanismo escolhido é\n'
        'validado/publicado; msbuddy, dedup e evidência por aduto degradam com registro explícito.\n', markdown=True)
    nb['cells'][2] = cell(
        "import os\nos.environ['CUDA_VISIBLE_DEVICES']=''\n"
        'from atomic_submission import AtomicSubmission\n'
        "publisher=AtomicSubmission('/kaggle/working')\n"
        'publisher.begin()  # antes de imports/inferência que podem falhar: nenhum fallback obsoleto\n'
        f"VARIANT={tag!r}\n")
    # Módulos testados localmente, embutidos via writefile.
    nb['cells'].insert(2, cell('%%writefile wave9_runtime.py\n' + RUNTIME))
    if cfg['needs_adduct']:
        nb['cells'].insert(3, cell('%%writefile formula_evidence.py\n' + EVIDENCE))
    nb['cells'].append(cell(MSBUDDY_CELL))
    if cfg['needs_adduct']:
        nb['cells'].append(cell(ADDUCT_CELL))
    if cfg['needs_dedup']:
        nb['cells'].append(cell(DEDUP_CELL))
    selection = (f"# Mecanismo escolhido ({tag}); única variante calculada além do blend de controle.\n"
                 f"selected, sel_stats = formula_order({cfg['base_expr']}, {cfg['formulas']}, _calc_f, topk={cfg['topk']})\n")
    proof = PROOF_TAIL
    if cfg['needs_dedup']:
        proof = proof.replace('mechanism=sel_stats,', 'mechanism=sel_stats, dedup=dedup_stats,')
    if cfg['needs_adduct']:
        proof = proof.replace('mechanism=sel_stats,', 'mechanism=sel_stats,\n             adduct_group_count=adduct_group_count, adduct_coverage=adduct_coverage,')
    nb['cells'].append(cell(selection + proof))
    nb['cells'].append(cell(PUBLISH_CELL))

    # --- Regressões estáticas antes de gravar qualquer arquivo ---
    text = '\n'.join(''.join(c['source']) for c in nb['cells'] if c['cell_type'] == 'code')
    for token in FORBIDDEN:
        if token in text:
            raise ValueError(('FORBIDDEN_TOKEN', tag, token))
    if text.count('publisher.publish(') != 1 or text.count('publisher.begin(') != 1:
        raise ValueError(('PUBLISHER_CARDINALITY', tag))
    # Isolamento: validação estrutural só existe dentro do publisher embutido.
    for c in nb['cells']:
        if c['cell_type'] != 'code':
            continue
        s = ''.join(c['source'])
        if s.startswith('%%writefile atomic_submission.py'):
            continue
        if 'AtomicSubmission.validate' in s:
            raise ValueError(('CROSS_BRANCH_VALIDATION', tag))
    # Separação de mecanismo: dependências só onde o mecanismo precisa.
    # Inspeciona apenas células de ligação (exclui módulos embutidos via writefile).
    wiring = '\n'.join(''.join(c['source']) for c in nb['cells']
                       if c['cell_type'] == 'code' and not ''.join(c['source']).startswith('%%writefile '))
    if not cfg['needs_dedup'] and ('dedup_rows(' in wiring or 'dedup_sub' in wiring):
        raise ValueError(('UNNEEDED_DEDUP_DEPENDENCY', tag))
    if not cfg['needs_adduct'] and ('adduct_formulas' in wiring or 'split_spectra_lenient(' in wiring):
        raise ValueError(('UNNEEDED_ADDUCT_DEPENDENCY', tag))
    for c in nb['cells']:
        if c['cell_type'] == 'code':
            s = ''.join(c['source'])
            s = s.split('\n', 1)[1] if s.startswith('%%writefile ') else s
            ast.parse(s)

    folder = R / f'kpush_wave9_{tag}'
    folder.mkdir(exist_ok=True)
    meta = copy.deepcopy(META0)
    slug = f'casmi26-wave9-isolated-{cfg["suffix"]}-cpu'
    meta.update(id='victor120956/' + slug, title=slug.replace('-', ' '), code_file='wave9.ipynb')
    for k in ['id_no', 'machine_shape']:
        meta.pop(k, None)
    (folder / 'wave9.ipynb').write_text(json.dumps(nb, ensure_ascii=False, indent=1))
    (folder / 'kernel-metadata.json').write_text(json.dumps(meta, indent=2))
    plans.append(dict(tag=tag, kernel=meta['id'], version=1, file='submission.csv',
                      folder=str(folder), question=cfg['question'], decision=cfg['decision'],
                      needs_dedup=cfg['needs_dedup'], needs_adduct=cfg['needs_adduct'],
                      preview_verified=False, no_automatic_submission=True))
    print('BUILT', meta['id'])

(R / 'wave9_plan.json').write_text(json.dumps(plans, ensure_ascii=False, indent=2))
print('WAVE9_PLAN_WRITTEN', len(plans), 'kernels; nenhum submit automático')

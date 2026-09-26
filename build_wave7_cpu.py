import copy, json, pathlib, textwrap
ROOT=pathlib.Path('/home/user')
src=next((ROOT/'kpush_w088_original').glob('*.ipynb'))
nb=json.loads(src.read_text())
for cell in nb['cells']:
 if cell['cell_type']=='code': cell['outputs']=[];cell['execution_count']=None
nb['cells'][0]['source']=['# Wave7: W088 + fórmula / dedup-refill, CPU\n',
 'Regenera o pipeline completo a partir de train/test. Sem dataset próprio ou outputs upstream.\n',
 'Controle W088 deve reproduzir os três hashes previamente verificados.\n',
 'Fórmula: stable partition top-5 msbuddy apenas nos 25 candidatos já emitidos.\n',
 'Dedup: preservar identidades reais e preencher placeholders com pool COCONUT+train por massa (sem tier2).\n',
 'Créditos e licença do pipeline original preservados abaixo.\n']
setup=''.join(nb['cells'][5]['source'])
setup=setup.replace('T_START = time.time()', 'os.environ["CUDA_VISIBLE_DEVICES"] = ""\nT_START = time.time()')
nb['cells'][5]['source']=setup.splitlines(keepends=True)
def add(s):
 nb['cells'].append({'cell_type':'code','metadata':{},'execution_count':None,'outputs':[],'source':s.splitlines(keepends=True)})
add('''# Fail closed: no attribution to W088 unless the regenerated baseline is identical.
import hashlib, json
from pathlib import Path
EXPECTED = {
 'submission.csv': '74dd3e23f5c4d6941239708cf20260e3',
 'submission_ours.csv': '71dc98afa17a950e01d6dadd48c69f49',
 'submission_pv.csv': '5364114d02f583ac518ffad28a8e1ca2',
}
for name, expected in EXPECTED.items():
    actual = hashlib.md5(Path(name).read_bytes()).hexdigest()
    assert actual == expected, ("W088_REPRODUCTION_FAILED", name, actual, expected)
print("W088_REPRODUCTION_PASS", EXPECTED, flush=True)
''')
# Exact offline formula method already used by the alive formula-first probe.
fn=json.loads(next((ROOT/'recon_formula').glob('*.ipynb')).read_text())
s=''.join(fn['cells'][25]['source'])
formula=s[s.index('# --- msbuddy formulas offline'):s.index('\nrows, diag = [], []')]
add('''from rdkit import Chem, RDLogger
from pathlib import Path as _MPath
from functools import lru_cache
from rdkit.Chem.rdMolDescriptors import CalcMolFormula as _CalcFormula
RDLogger.DisableLog('rdApp.*')
te = E.pq.read_table(os.path.join(COMP, 'test.parquet')).to_pandas()
mols = list(te.groupby('molecule_id'))
buddy_formulas = {}
@lru_cache(maxsize=None)
def _calc_f(smi):
    try:
        m = Chem.MolFromSmiles(smi)
        return _CalcFormula(m).rstrip('+-') if m is not None else None
    except Exception:
        return None
''' + formula + '''
assert len(buddy_formulas) == 400
assert sum(bool(x) for x in buddy_formulas.values()) >= 390, 'MSBUDDY_COVERAGE_FAILED'
formula_sub = subs['blend'].copy()
f_changed = 0
for idx, row in formula_sub.iterrows():
    base = row.smiles.split(';')
    formulas = set(buddy_formulas.get(row.molecule_id, [])[:5])
    order = sorted(range(len(base)), key=lambda j: (_calc_f(base[j]) not in formulas, j)) if formulas else list(range(len(base)))
    out = [base[j] for j in order]
    assert sorted(out) == sorted(base), 'FORMULA_ADDED_OR_DROPPED_CANDIDATE'
    f_changed += out != base
    formula_sub.at[idx, 'smiles'] = ';'.join(out)
assert f_changed > 0, 'FORMULA_NOOP_DO_NOT_SUBMIT'
formula_sub.to_csv('submission_formula.csv', index=False)
Path('buddy_formulas.json').write_text(json.dumps({str(k):v for k,v in buddy_formulas.items()}, indent=2))
print('FORMULA_CHANGED_ROWS', f_changed, flush=True)
''')
add('''# W088 already canonical-dedups its first 40 ranked candidates.
# Only alter rows containing repeated/invalid identities or CCO padding.
# Preserve all genuine ordered candidates; refill from the SAME pool by mass.
@lru_cache(maxsize=None)
def clean_key(s):
    return E.canon_key(str(s))

def clean_existing(base):
    kept, seen = [], set()
    for smi in base:
        if smi == 'CCO':  # known W088 padding sentinel, not an inferred candidate
            continue
        key = clean_key(smi)
        if key and key not in seen:
            seen.add(key); kept.append(smi)
    return kept, seen

def refill_by_pool_mass(base, target, pool):
    kept, seen = clean_existing(base)
    preserved = list(kept)
    if len(kept) < 25:
        # Stable mass ordering, identical principle to the scored dedup-full probe.
        order = np.argsort(np.abs(np.asarray(pool['mass']) - target), kind='mergesort')
        for ci in order:
            if len(kept) == 25: break
            smi = str(pool['smiles'][int(ci)])
            if smi == 'CCO': continue
            key = clean_key(smi)
            if key and key not in seen:
                seen.add(key); kept.append(smi)
    assert len(kept) == 25, 'NOT_ENOUGH_UNIQUE_POOL_CANDIDATES'
    assert kept[:len(preserved)] == preserved
    assert len({clean_key(s) for s in kept}) == 25
    return kept

rec_by_mid = {r['mid']:r for r in recs}
dedup_sub = subs['blend'].copy()
d_changed = d_replaced = 0
for idx, row in dedup_sub.iterrows():
    base = row.smiles.split(';')
    kept, seen = clean_existing(base)
    if len(kept) == 25:
        out = base
    else:
        rec = rec_by_mid[row.molecule_id]
        assert np.isfinite(rec.get('target', np.nan)), ('NO_VALID_MASS', row.molecule_id)
        out = refill_by_pool_mass(base, rec['target'], E.POOL)
        d_replaced += 25 - len(kept)
    d_changed += out != base
    dedup_sub.at[idx, 'smiles'] = ';'.join(out)
assert d_changed > 0, 'DEDUP_NOOP_DO_NOT_SUBMIT'
dedup_sub.to_csv('submission_dedup.csv', index=False)
print('DEDUP_CHANGED_ROWS', d_changed, 'REPLACED_SLOTS', d_replaced, flush=True)
''')
add('''# Output contract and lineage: fail on duplicates, invalid molecules or unknown control.
report = {'baseline_md5': EXPECTED, 'formula_changed_rows': int(f_changed),
          'dedup_changed_rows': int(d_changed), 'dedup_replaced_slots': int(d_replaced),
          'gpu': False, 'own_dataset_inputs': False, 'files': {}}
samp = pd.read_csv(os.path.join(COMP, 'sample_submission.csv'))
for filename, sub in [('submission_formula.csv', formula_sub), ('submission_dedup.csv', dedup_sub)]:
    assert list(sub.columns) == ['molecule_id','smiles']
    assert sub.molecule_id.tolist() == samp.molecule_id.tolist()
    assert len(sub) == 400 and sub.molecule_id.nunique() == 400
    lists = sub.smiles.str.split(';')
    assert all(len(x) == 25 for x in lists)
    assert all(Chem.MolFromSmiles(s) is not None for x in lists for s in x)
    md5 = hashlib.md5(Path(filename).read_bytes()).hexdigest()
    assert md5 not in EXPECTED.values(), 'DUPLICATE_CONTROL_DO_NOT_SUBMIT'
    report['files'][filename] = {'md5':md5, 'sha256':hashlib.sha256(Path(filename).read_bytes()).hexdigest()}
assert len({r['md5'] for r in report['files'].values()}) == 2
Path('wave7_verify.json').write_text(json.dumps(report, indent=2))
print('VERIFY PASS', json.dumps(report), flush=True)
''')
out=ROOT/'kpush_wave7_cpu';out.mkdir(exist_ok=True)
(out/'wave7.ipynb').write_text(json.dumps(nb,ensure_ascii=False,indent=1))
meta=json.loads((ROOT/'kpush_w088_original/kernel-metadata.json').read_text())
for k in ['id_no','machine_shape']:meta.pop(k,None)
meta.update(id='victor120956/casmi26-wave7-w088-formula-dedup-cpu',title='casmi26 wave7 w088 formula dedup cpu',code_file='wave7.ipynb',enable_gpu=False,enable_tpu=False)
meta['dataset_sources'].append('franciscoangulo/casmi26-mist-msbuddy-assets')
(out/'kernel-metadata.json').write_text(json.dumps(meta,indent=2))
print('BUILT',out)

"""Formula evidence grouped by consistent adduct/polarity; no model/network dependencies."""
from collections import defaultdict
from statistics import median
import re

def adduct_charge(adduct):
    match=re.search(r'\](\d*)([+-])$',str(adduct))
    if not match:raise ValueError('UNPARSEABLE_ADDUCT_CHARGE')
    magnitude=int(match.group(1) or '1')
    if magnitude<1:raise ValueError('INVALID_CHARGE')
    return magnitude*(1 if match.group(2)=='+' else -1)

def split_spectra(rows):
    grouped=defaultdict(list)
    for row in rows:
        key=(str(row['molecule_id']),str(row['adduct']),str(row['ionization_mode']))
        charge=adduct_charge(key[1])
        if (key[2],charge>0) not in [('positive',True),('negative',False)]:
            raise ValueError('ADDUCT_POLARITY_MISMATCH')
        grouped[key].append(row)
    out=[]
    for (mid,adduct,mode),items in sorted(grouped.items()):
        peaks=[]
        for row in items:
            mz=list(row['ms2_mzs']);ints=list(row['ms2_normalized_intensities'])
            if len(mz)!=len(ints):raise ValueError('PEAK_LENGTH_MISMATCH')
            peaks.extend((float(m),float(i)) for m,i in zip(mz,ints))
        peaks.sort(key=lambda x:x[0])
        out.append({'molecule_id':mid,'adduct':adduct,'mode':mode,'charge':adduct_charge(adduct),
                    'precursor_mz':float(median(float(r['precursor_mz']) for r in items)),
                    'ms2_mzs':[x[0] for x in peaks],'ms2_normalized_intensities':[x[1] for x in peaks],
                    'spectrum_count':len(items)})
    return out

def combine_formula_evidence(groups):
    totals=defaultdict(lambda:defaultdict(lambda:[0,0.0]))
    seen_groups=set()
    for group in groups:
        mid=str(group['molecule_id']);key=(mid,group['adduct'],group['mode'])
        if key in seen_groups:raise ValueError('DUPLICATE_ADDUCT_GROUP')
        seen_groups.add(key);totals[mid]  # preserve molecules without formulas
        seen=set()
        for rank,f in enumerate(group['formulas'][:5],1):
            if not f:continue
            formula=str(f).replace(' ','').rstrip('+-')
            if formula in seen:continue
            seen.add(formula);totals[mid][formula][0]+=1;totals[mid][formula][1]+=1.0/rank
    return {mid:sorted(values,key=lambda f:(-values[f][0],-values[f][1],f))[:5]
            for mid,values in totals.items()}


# ---------------------------------------------------------------------------
# Wave9 (correção E031): variantes lenientes para o kernel de produção.
# Linhas/grupos inválidos são IGNORADOS com registro explícito em `degraded`;
# nunca abortam o mecanismo escolhido. As funções estritas acima permanecem
# para auditoria local e testes de contrato.
# ---------------------------------------------------------------------------

def split_spectra_lenient(rows, degraded=None):
    grouped=defaultdict(list)
    skipped=0
    for row in rows:
        try:
            key=(str(row['molecule_id']),str(row['adduct']),str(row['ionization_mode']))
            charge=adduct_charge(key[1])
            if (key[2],charge>0) not in [('positive',True),('negative',False)]:
                raise ValueError('ADDUCT_POLARITY_MISMATCH')
            if len(row['ms2_mzs'])!=len(row['ms2_normalized_intensities']):
                raise ValueError('PEAK_LENGTH_MISMATCH')
        except Exception:
            skipped+=1
            continue
        grouped[key].append(row)
    out=[]
    for (mid,adduct,mode),items in sorted(grouped.items()):
        peaks=[]
        for row in items:
            peaks.extend((float(m),float(i)) for m,i in zip(row['ms2_mzs'],row['ms2_normalized_intensities']))
        peaks.sort(key=lambda x:x[0])
        out.append({'molecule_id':mid,'adduct':adduct,'mode':mode,'charge':adduct_charge(adduct),
                    'precursor_mz':float(median(float(r['precursor_mz']) for r in items)),
                    'ms2_mzs':[x[0] for x in peaks],'ms2_normalized_intensities':[x[1] for x in peaks],
                    'spectrum_count':len(items)})
    if degraded is not None and skipped:
        degraded.append(['SPECTRA_ROWS_SKIPPED',int(skipped)])
    return out


def combine_formula_evidence_lenient(groups, degraded=None):
    totals=defaultdict(lambda:defaultdict(lambda:[0,0.0]))
    seen_groups=set()
    duplicates=0
    for group in groups:
        mid=str(group['molecule_id']);key=(mid,group['adduct'],group['mode'])
        if key in seen_groups:
            duplicates+=1
            continue
        seen_groups.add(key);totals[mid]
        seen=set()
        for rank,f in enumerate(group['formulas'][:5],1):
            if not f:continue
            formula=str(f).replace(' ','').rstrip('+-')
            if formula in seen:continue
            seen.add(formula);totals[mid][formula][0]+=1;totals[mid][formula][1]+=1.0/rank
    if degraded is not None and duplicates:
        degraded.append(['DUPLICATE_ADDUCT_GROUPS_SKIPPED',int(duplicates)])
    return {mid:sorted(values,key=lambda f:(-values[f][0],-values[f][1],f))[:5]
            for mid,values in totals.items()}

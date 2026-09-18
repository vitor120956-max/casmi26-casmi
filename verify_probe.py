#!/usr/bin/env python3
"""Verify a probe output file against the local v3 (twin@1) file.
Usage: verify_probe.py MODE FILE V3FILE -> prints OK or reason."""
import sys, csv

mode, pathf, v3f = sys.argv[1], sys.argv[2], sys.argv[3]

def load(fp):
    d = {}
    for r in csv.DictReader(open(fp)):
        d[r['molecule_id']] = [g for g in r['smiles'].split(';') if g]
    return d

new, v3 = load(pathf), load(v3f)
if set(new) != set(v3):
    print('IDS_DIFFER'); sys.exit()
bad = 0
for mid, g in new.items():
    v = v3[mid]
    if mode == 'A2':
        exp = [v[0]] if v else ['CCO']
    elif mode == 'B2':
        exp = [v[1]] if len(v) > 1 else ['CCO']
    else:  # C
        exp = v[2:] if len(v) > 2 else ['CCO']
    if g != exp:
        bad += 1
print('OK' if bad == 0 else f'MISMATCH_{bad}_of_{len(new)}')

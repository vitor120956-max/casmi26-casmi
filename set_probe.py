#!/usr/bin/env python3
"""Flip CFG.PROBE in fork.ipynb. Usage: set_probe.py A2|B2|C"""
import json, re, sys

mode = sys.argv[1]
assert mode in ('A2', 'B2', 'C', 'B')
path = '/home/user/fork_bera/fork.ipynb'
nb = json.load(open(path))
n = 0
for cell in nb['cells']:
    if cell['cell_type'] != 'code':
        continue
    s = ''.join(cell['source'])
    s2, k = re.subn(r"PROBE        = '\w+'", f"PROBE        = '{mode}'", s)
    if k:
        n += k
        lines = s2.split('\n')
        cell['source'] = [l + '\n' for l in lines[:-1]] + ([lines[-1]] if lines[-1] else [])
assert n == 1, f'expected 1 PROBE line, touched {n}'
json.dump(nb, open(path, 'w'), indent=1)
print('PROBE set to', mode)

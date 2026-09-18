#!/usr/bin/env python3
"""Set kernel-metadata description per probe mode. Usage: set_desc.py A2|B2|C"""
import json, sys

mode = sys.argv[1]
desc = {
    'A2': 'P_A2 probe: twin only at rank1 (1 guess, no junk) -> f_t exact',
    'B2': 'P_B2 probe: ranker #2 only at rank1 (1 guess, no junk) -> p_2 exact',
    'C':  'P_C probe: original ranks 3-25 promoted (23 guesses) -> tail sum',
}[mode]
p = '/home/user/fork_bera/kernel-metadata.json'
m = json.load(open(p))
m['description'] = desc
json.dump(m, open(p, 'w'), indent=2)
print('desc:', desc)

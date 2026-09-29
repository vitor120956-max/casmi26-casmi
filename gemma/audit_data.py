"""CPU-only audit of official public development labels. Never supplies fixes to an agent.
Reproduce: python gemma/audit_data.py. No inference, GPU, network, submission or training.
"""
from pathlib import Path
from collections import Counter, defaultdict
import hashlib, json, re, statistics

ROOT = Path(__file__).resolve().parent

def patch_stats(patch):
    files=[]; added=removed=0; in_hunk=False
    for line in patch.splitlines():
        if line.startswith('diff --git '):
            in_hunk=False
        elif line.startswith('+++ '):
            path=line[4:].split('\t')[0]
            if path.startswith('b/'): path=path[2:]
            if path!='/dev/null': files.append(path)
        elif line.startswith('@@ '): in_hunk=True
        elif in_hunk and line.startswith('+'): added+=1
        elif in_hunk and line.startswith('-'): removed+=1
    return dict(files=sorted(set(files)), added=added, removed=removed)

def summary(values):
    s=sorted(values)
    return {'min':min(s), 'median':statistics.median(s), 'p90_nearest_rank':s[max(0,__import__('math').ceil(.9*len(s))-1)], 'max':max(s)}

def audit():
    source=ROOT/'official/tasks.jsonl'
    rows=[json.loads(s) for s in source.read_text().splitlines() if s.strip()]
    assert len({r['instance_id'] for r in rows})==len(rows)
    grouped=defaultdict(list)
    for r in rows:grouped[(r['repo'],r['base_commit'])].append(r['instance_id'])
    patches=[patch_stats(r['patch']) for r in rows]
    assert all(p['files'] for p in patches), 'Some diffs lack supported +++ file headers; inspect before reporting.'
    count=Counter(r['repo'] for r in rows)
    profile={
      'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
      'tasks':len(rows),'repositories':dict(count),'unique_repository_commits':len(grouped),
      'duplicate_commit_groups':[v for v in grouped.values() if len(v)>1],
      'date_min':min(r['created_at'] for r in rows),'date_max':max(r['created_at'] for r in rows),
      'nonempty_hints':sum(bool(r['hints_text'].strip()) for r in rows),
      'reference_patch_chars':summary([len(r['patch']) for r in rows]),
      'problem_statement_chars':summary([len(r['problem_statement']) for r in rows]),
      'changed_files':summary([len(p['files']) for p in patches]),
      'one_file_reference_patches':sum(len(p['files'])==1 for p in patches),
      'added_lines':summary([p['added'] for p in patches]),
      'removed_lines':summary([p['removed'] for p in patches]),
      'patches_mentioning_docs_src':sum(any(f.startswith('docs_src/') for f in p['files']) for p in patches),
      'patches_with_changed_async_definition_line':sum(bool(re.search(r'^[+-]\s*async def\s',r['patch'],re.M)) for r in rows),
      'interpretation':'Changed async definition line is a narrow textual feature, NOT count of fixes inside async functions.'
    }
    # Frozen split by repository+commit; no target labels enter this assignment.
    # Stratify three substantial repos; httpx sole task is a separate smoke test, not a meaningful holdout.
    split={'dev':[],'validation':[],'test_frozen':[],'smoke_httpx':[]}
    for repo in sorted(count):
        groups=[(k,v) for k,v in grouped.items() if k[0]==repo]
        groups.sort(key=lambda kv: hashlib.sha256(('gemma-victor-2026-v1|'+kv[0][0]+'|'+kv[0][1]).encode()).hexdigest())
        if repo=='encode/httpx':split['smoke_httpx']=[i for _,v in groups for i in v];continue
        n=len(groups);n_test=max(1,round(.2*n));n_val=max(1,round(.2*n))
        for idx,(_,ids) in enumerate(groups):
            key='test_frozen' if idx<n_test else ('validation' if idx<n_test+n_val else 'dev')
            split[key].extend(ids)
    ownership={i:key for key,ids in split.items() for i in ids}
    assert len(ownership)==len(rows)
    assert all(len({ownership[i] for i in ids})==1 for ids in grouped.values())
    profile['proposed_split_counts']={k:len(v) for k,v in split.items()}
    profile['warning']='Public labels already available; this is an engineering holdout, not a truly unseen benchmark. Hidden test uses private repositories. Leave-repository-out evaluation is still required.'
    out=ROOT/'research';out.mkdir(exist_ok=True)
    (out/'task_profile.json').write_text(json.dumps(profile,indent=2))
    (out/'split_v1.json').write_text(json.dumps(split,indent=2))
    print(json.dumps(profile,indent=2))
    return profile

if __name__=='__main__':audit()

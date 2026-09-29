"""Read-only/CPU evidence probes against an official wheel snapshot.
Not full ADK compilation, not inference, not an evaluation score.
"""
from pathlib import Path
import ast, importlib, importlib.util, json, runpy, sys, tarfile, tempfile, types, unittest
from collections import Counter
import numpy as np
ROOT=Path(__file__).resolve().parent
SRC=ROOT/'research/harness_source'

# Load only audited pure-CPU modules under an isolated package name, not __init__.
package=types.ModuleType('official_gemma_probe');package.__path__=[str(SRC/'adk_submission')]
sys.modules[package.__name__]=package
loader=importlib.import_module('official_gemma_probe.yaml_loader')
errors=importlib.import_module('official_gemma_probe.errors')
emb=runpy.run_path(str(SRC/'swegemma/graph/embedding_utils.py'))

class OfficialCpuContracts(unittest.TestCase):
    def test_starter_root_includes(self):
        root=ROOT/'official/sample_submission'
        obj=loader.load_yaml(root/'agent.yaml',root)
        self.assertEqual(obj['model'],'gemma-4-31b-it-qat-w4a16-ct')
        self.assertIsInstance(obj['instruction'],str)
    def test_internal_parent_include_is_accepted(self):
        root=ROOT/'official/sample_submission'
        obj=loader.load_yaml(root/'sub_agents/code_analyzer.yaml',root)
        self.assertIn('specialized code analysis',obj['instruction'])
        self.assertEqual(obj['generate_content_config']['temperature'],.2)
    def test_include_escape_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            d=Path(td);root=d/'submission';root.mkdir();(d/'outside.md').write_text('fixture')
            p=root/'agent.yaml';p.write_text('instruction: !include ../outside.md\n')
            with self.assertRaises(errors.PathTraversalError):loader.load_yaml(p,root)
    def test_include_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);(root/'real.md').write_text('fixture');(root/'link.md').symlink_to(root/'real.md')
            p=root/'agent.yaml';p.write_text('instruction: !include link.md\n')
            with self.assertRaises(errors.PathTraversalError):loader.load_yaml(p,root)
    def test_embedding_symbol_lookup_not_natural_language(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'fixture.npz'
            np.savez(path,**{'httpx._client.Client':np.array([1.,0.],dtype=np.float32)})
            exact=emb['embed']('httpx._client.Client','probe/repo',str(path))
            np.testing.assert_array_equal(exact,[1.,0.])
            suffix=emb['embed']('Client','probe/repo',str(path));np.testing.assert_array_equal(suffix,[1.,0.])
            self.assertIsNone(emb['embed']('find where timeout is handled','probe/repo',str(path)))


def graph_audit():
    samples=json.loads((ROOT/'research/graph_sample.json').read_text());results=[]
    for repo,info in samples.items():
        f=ROOT/'official/graphs'/f"{repo.split('/')[-1]}_{info['base_commit']}.json"
        g=json.loads(f.read_text());texts=[len(n.get('text','')) for n in g['nodes']]
        edges=g.get('edges',g.get('links',[]))
        results.append({'repo':repo,'commit':info['base_commit'],'nodes':len(g['nodes']),
          'edges':len(edges),'edge_types':dict(Counter(e.get('type') for e in edges)),
          'max_node_source_chars':max(texts),'nodes_over_10000_source_chars':sum(n>10000 for n in texts),
          'distinct_nodes_starting_async_def':sum(n.get('text','').lstrip().startswith('async def ') for n in g['nodes'])})
    info=samples['encode/httpx'];graph=json.loads((ROOT/'official/graphs'/f"httpx_{info['base_commit']}.json").read_text());ids={n['id'] for n in graph['nodes']}
    counts=Counter();examples=[];parsed=0
    archive=ROOT/'official/snapshots/httpx_3672.tgz'
    with tarfile.open(archive,'r:gz') as tar:
        for member in tar:
            if not member.isfile() or member.size>2_000_000:continue
            parts=Path(member.name).parts
            # Audit library only; no tests/fixtures, no extraction, no execution.
            if 'src' not in parts or not member.name.endswith('.py'):continue
            pos=parts.index('src')+1;rel=Path(*parts[pos:])
            if len(rel.parts)<2 or any(x in {'tests','test','docs'} for x in rel.parts):continue
            src=tar.extractfile(member).read().decode('utf-8');tree=ast.parse(src);parsed+=1
            mod='.'.join(rel.with_suffix('').parts)
            if mod.endswith('.__init__'):mod=mod[:-9]
            def visit(nodes,scope=''):
                for n in nodes:
                    if isinstance(n,(ast.ClassDef,ast.FunctionDef,ast.AsyncFunctionDef)):
                        qual=scope+n.name;key=mod+'.'+qual
                        kind='class' if isinstance(n,ast.ClassDef) else ('async' if isinstance(n,ast.AsyncFunctionDef) else 'sync')
                        counts[kind+'_total']+=1;counts[kind+'_present']+=key in ids
                        if kind=='async' and key not in ids and len(examples)<5:examples.append(key)
                        # Only classes contain methods; exclude nested local function scopes.
                        if isinstance(n,ast.ClassDef):visit(n.body,qual+'.')
            visit(tree.body)
    result={'sample_graphs':results,'httpx_snapshot_library_audit':{'python_files_parsed':parsed,**dict(counts),'missing_async_examples':examples},
       'scope':'Four graph snapshots, one per repository. AST coverage independently checked only on HTTPX library snapshot; do not generalize numeric totals to all tasks.'}
    (ROOT/'research/graph_audit.json').write_text(json.dumps(result,indent=2));return result

if __name__=='__main__':
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(OfficialCpuContracts)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    record={'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'full_adk_compile':False,'inference':False,'training':False}
    (ROOT/'research/cpu_contract_tests.json').write_text(json.dumps(record,indent=2))
    if not result.wasSuccessful():sys.exit(1)
    print(json.dumps(graph_audit(),indent=2))

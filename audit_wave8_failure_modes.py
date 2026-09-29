"""Reproduce failure mechanisms from submitted source; never claims hidden root cause.
CPU-only, no API, inference, submission or changes to submitted notebooks.
"""
import ast,hashlib,json,tempfile
from pathlib import Path
from atomic_submission import AtomicSubmission
ROOT=Path(__file__).resolve().parent
DIRS=['kpush_wave8_atomic_combo_cpu','kpush_wave8_top1','kpush_wave8_top1_dedup','kpush_wave8_adduct','kpush_wave8_adduct_dedup']

def run():
    result={'scope':'Synthetic tests of exact guard/validation loop extracted from submitted notebook source. Hidden rerun logs unavailable; actual cause remains unknown.','kernels':[]}
    for dirname in DIRS:
        d=ROOT/dirname;m=json.loads((d/'kernel-metadata.json').read_text());p=d/m['code_file'];nb=json.loads(p.read_text())
        gate=None;validate_loop=None
        for c in nb['cells']:
            if c['cell_type']!='code':continue
            s=''.join(c['source'])
            if s.startswith('%%'):continue
            tree=ast.parse(s)
            for node in tree.body:
                if isinstance(node,ast.If) and "MSBUDDY_COVERAGE_FAILED" in ast.unparse(node):gate=node
                if isinstance(node,ast.For) and ast.unparse(node.target)=='(name, sub)' and 'AtomicSubmission.validate' in ast.unparse(node):validate_loop=node
        assert gate is not None and validate_loop is not None,dirname
        def compile_node(n):return compile(ast.fix_missing_locations(ast.Module(body=[n],type_ignores=[])),str(p),'exec')
        scenarios={}
        for coverage in [.97,.975,1.]:
            try:exec(compile_node(gate),{'coverage':coverage});outcome='PASS'
            except ValueError as e:outcome=str(e)
            scenarios[str(coverage)]=outcome
        assert 'MSBUDDY_COVERAGE_FAILED' in scenarios['0.97']
        assert scenarios['0.975']=='PASS' and scenarios['1.0']=='PASS'
        # The exact loop rejects an invalid UNUSED branch even with a valid selected branch.
        class FakeFrame:
            def __init__(self,records):self.records=records
            def to_dict(self,orient):assert orient=='records';return self.records
        valid=[{'molecule_id':'new_id','smiles':';'.join(['CCO']*25)}]
        invalid=[{'molecule_id':'new_id','smiles':';'.join(['INVALID']*25)}]
        with tempfile.TemporaryDirectory() as td:
            publisher=AtomicSubmission(td);publisher.begin()
            AtomicSubmission.validate(valid,['new_id'],lambda x:x=='CCO')
            env={'variants':{'unused_control':FakeFrame(invalid),'selected':FakeFrame(valid)},'records':{},'sample_ids':['new_id'],'AtomicSubmission':AtomicSubmission,'valid_smiles':lambda x:x=='CCO'}
            try:exec(compile_node(validate_loop),env)
            except ValueError as e:unused_failure=str(e)
            else:raise AssertionError('Expected unused invalid branch to block loop')
            assert unused_failure=='INVALID_SMILES'
            assert not publisher.final.exists()
        result['kernels'].append({'slug':m['id'],'source_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'coverage_results':scenarios,'selected_contract_independently_valid':True,'unused_branch_blocks_loop':unused_failure})
    result['checks_passed']=len(DIRS)*5
    out=ROOT/'wave8_failure_diagnosis';out.mkdir(exist_ok=True)
    (out/'synthetic_reproductions.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))
if __name__=='__main__':run()

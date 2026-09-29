#!/usr/bin/env python3
"""One explicitly reviewed candidate at a time; dry-run by default. No timer or retry.
Current preparation does not authorize sending. See release_review.json.
"""
from pathlib import Path
import argparse,datetime,fcntl,hashlib,json,os
from batch_release_checks import check_artifact,release_gate
ROOT=Path(__file__).resolve().parent
COMP='enveda-CASMI26-molecule-id-mass-spectra'

def save_state(path, data):
    temporary=path.with_suffix('.staging')
    with temporary.open('w') as stream:
        json.dump(data,stream,indent=2);stream.flush();os.fsync(stream.fileno())
    os.replace(temporary,path)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--execute',action='store_true');parser.add_argument('--variant');args=parser.parse_args()
    readiness=json.loads((ROOT/'next_batch_preparation/readiness.json').read_text())
    review=json.loads((ROOT/'next_batch_preparation/release_review.json').read_text())
    if not args.execute:
        print(json.dumps({'mode':'DRY_RUN','submission_calls':0,'artifact_verified_count':readiness['artifact_verified_count'],
                          'send_authorized':review['send_authorized'],'canary_variant':review['canary_variant'],
                          'canary_result_reviewed':review['canary_result_reviewed'],'note':'No network calls. --execute still requires per-source approval and time window.'},indent=2));return
    if not args.variant:raise SystemExit('EXPLICIT_VARIANT_REQUIRED')
    row=next((r for r in readiness['candidates'] if r['variant']==args.variant),None)
    if not row:raise SystemExit('UNKNOWN_CANDIDATE')
    approval=review.get('approvals',{}).get(args.variant,{})
    is_canary=args.variant==review['canary_variant']
    passed=release_gate(artifact_verified=row.get('artifact_verified',False),version_confirmed=type(row.get('version')) is int and row['version']>0,
       source_reviewed=approval.get('source_reviewed') is True and approval.get('source_sha256')==row['source_sha256'],
       canary_reviewed=review.get('canary_result_reviewed') is True,is_canary=is_canary,send_authorized=review.get('send_authorized') is True)
    if not passed:raise SystemExit('RELEASE_REVIEW_REQUIRED_NO_SUBMISSION')
    if row.get('same_public_predictions_as_rejected_wave8') and approval.get('corrected_rerun_explicitly_approved') is not True:
        raise SystemExit('REJECTED_PREVIEW_RETEST_NOT_APPROVED')
    start=review.get('allowed_not_before');end=review.get('allowed_not_after')
    if not start or not end:raise SystemExit('EXPLICIT_TIME_WINDOW_REQUIRED')
    start=datetime.datetime.fromisoformat(start);end=datetime.datetime.fromisoformat(end)
    if start.tzinfo is None or end.tzinfo is None:raise SystemExit('TIMEZONE_REQUIRED')
    now=datetime.datetime.now(datetime.timezone.utc)
    if not start<=now<end:raise SystemExit('OUTSIDE_REVIEWED_TIME_WINDOW')
    lock=(ROOT/'next_batch_preparation/send.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    statefile=ROOT/'next_batch_preparation/send_state.json';state=json.loads(statefile.read_text()) if statefile.exists() else {}
    if args.variant in state:raise SystemExit('EXISTING_INTENT_REQUIRES_RECONCILIATION_NO_RETRY')
    if any(entry.get('phase')!='accepted' for entry in state.values()):raise SystemExit('AMBIGUOUS_PRIOR_SEND_REQUIRES_RECONCILIATION')
    from kaggle.api.kaggle_api_extended import KaggleApi
    from kagglesdk.kernels.types.kernels_api_service import ApiGetKernelRequest
    from rdkit import Chem
    import csv
    api=KaggleApi();api.authenticate()
    quota=api.competition_get_submission_limits(COMP).to_dict()
    if int(quota.get('numAllowedNow',0))<1:raise SystemExit('NO_QUOTA')
    submissions=[s.to_dict() for s in api.competition_submissions(COMP,page_size=100)]
    if any(row['kernel'] in (s.get('url') or '') for s in submissions):raise SystemExit('KERNEL_ALREADY_SUBMITTED_REVIEW_REQUIRED')
    if api.kernels_status(row['kernel']).to_dict().get('status')!='COMPLETE':raise SystemExit('KERNEL_NOT_COMPLETE')
    owner,slug=row['kernel'].split('/');req=ApiGetKernelRequest();req.user_name=owner;req.kernel_slug=slug
    with api.build_kaggle_client() as client:remote=client.kernels.kernels_api_client.get_kernel(req)
    if remote.metadata.current_version_number!=row['version'] or hashlib.sha256(remote.blob.source.encode()).hexdigest()!=row['source_sha256']:
        raise SystemExit('SOURCE_OR_VERSION_CHANGED')
    folder=ROOT/'next_batch_preparation/outputs'/args.variant
    proof=json.loads((folder/'publication.json').read_text());raw=(folder/'submission.csv').read_bytes()
    if hashlib.sha256(raw).hexdigest()!=row.get('sha256'):raise SystemExit('PREPARED_FILE_CHANGED')
    with (ROOT/'harness_data/sample_submission.csv').open() as stream:ids=[r['molecule_id'] for r in csv.DictReader(stream)]
    history=json.loads((ROOT/'historical_hashes.json').read_text())
    for entry in json.loads((ROOT/'wave7_submit_state.json').read_text()).values():
        if entry.get('phase')=='accepted':history[entry['plan']['semantic_sha256']]=['previous accepted Wave7']
    for entry in state.values():
        if entry.get('semantic_sha256'):history[entry['semantic_sha256']]=['current reviewed batch']
    check=check_artifact(raw,proof,args.variant,ids,lambda s:Chem.MolFromSmiles(s) is not None,history)
    if not check['artifact_verified']:raise SystemExit('FINAL_FILE_CHECK_FAILED: '+str(check['blockers']))
    message='PROBE-WAVE9FIX:'+args.variant+' reviewed source and artifact'
    state[args.variant]={'phase':'intent','at':now.isoformat(),'kernel':row['kernel'],'version':row['version'],'sha256':row['sha256'],'message':message,'semantic_sha256':check['semantic_sha256'],'source_sha256':row['source_sha256']}
    save_state(statefile,state)
    try:
        response=api.competition_submit_code(file_name='submission.csv',message=message,competition=COMP,kernel=row['kernel'],kernel_version=row['version'],quiet=True).to_dict()
        if not response.get('ref'):raise ValueError('SUBMISSION_REFERENCE_MISSING')
        state[args.variant].update(phase='accepted',response=response);save_state(statefile,state);print(json.dumps(response))
    except Exception as error:
        state[args.variant].update(phase='ambiguous_or_failed',error_type=type(error).__name__,error=str(error));save_state(statefile,state)
        with (ROOT/'incidents.jsonl').open('a') as stream:stream.write(json.dumps({'at':now.isoformat(),'code':'NEXT_BATCH_SEND','summary':str(error),'state':'STOP_NO_RETRY','context':{'variant':args.variant}})+'\n')
        raise

if __name__=='__main__':main()

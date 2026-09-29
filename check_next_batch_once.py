#!/usr/bin/env python3
"""One-shot preparation only. No submission endpoint, scheduler, sleep or retry loop."""
from pathlib import Path
import argparse,copy,csv,datetime,hashlib,json
from batch_release_checks import check_artifact,semantic_hash
ROOT=Path(__file__).resolve().parent
COMP='enveda-CASMI26-molecule-id-mass-spectra'
BRT=datetime.timezone(datetime.timedelta(hours=-3))

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--check-once',action='store_true');args=parser.parse_args()
    plan=json.loads((ROOT/'next_batch_preparation/plan.json').read_text())
    result={'at':datetime.datetime.now(BRT).isoformat(),'mode':'live_once' if args.check_once else 'offline',
            'submissions_made':0,'automatic_dispatch':False,'candidates':[]}
    history=json.loads((ROOT/'historical_hashes.json').read_text())
    journal=json.loads((ROOT/'wave7_submit_state.json').read_text())
    for entry in journal.values():
        if entry.get('phase')=='accepted':history[entry['plan']['semantic_sha256']]=['previous accepted Wave7']
    if args.check_once:
        from kaggle.api.kaggle_api_extended import KaggleApi
        from kagglesdk.kernels.types.kernels_api_service import ApiGetKernelRequest
        from rdkit import Chem,RDLogger
        RDLogger.DisableLog('rdApp.*')
        api=KaggleApi();api.authenticate()
        result['quota']=api.competition_get_submission_limits(COMP).to_dict()
    else:
        cached=json.loads((ROOT/'next_batch_preparation/status_once.json').read_text())
        cached_status={x['ref']:x['status'] for x in cached['statuses']};result['quota']=cached['quota'];result['status_evidence_at']=cached['at']
    fingerprints={}
    for candidate in plan['candidates']:
        row=copy.deepcopy(candidate);row['release_ready']=False;row['artifact_verified']=False;row['blockers']=[]
        status=api.kernels_status(row['kernel']).to_dict() if args.check_once else cached_status.get(row['kernel'],{'status':'UNKNOWN'})
        row['execution_status']=status;folder=ROOT/'next_batch_preparation/outputs'/row['variant']
        if status.get('status')!='COMPLETE':
            row['blockers'].append('PREVIEW_NOT_COMPLETE');result['candidates'].append(row);continue
        if not args.check_once:
            row['blockers'].append('LIVE_ARTIFACT_CHECK_REQUIRED');result['candidates'].append(row);continue
        try:
            folder.mkdir(parents=True,exist_ok=True)
            # Metadata is fetched through the official SDK, including the version omitted by CLI pull.
            def current_source():
                owner,slug=row['kernel'].split('/');req=ApiGetKernelRequest();req.user_name=owner;req.kernel_slug=slug
                with api.build_kaggle_client() as client:
                    response=client.kernels.kernels_api_client.get_kernel(req)
                return response.metadata.current_version_number,hashlib.sha256(response.blob.source.encode()).hexdigest(),response.metadata.to_dict()
            version,source_sha,metadata=current_source()
            if version!=row['version'] or source_sha!=row['source_sha256']:raise ValueError('REMOTE_SOURCE_OR_VERSION_CHANGED')
            (folder/'verified_source_metadata.json').write_text(json.dumps(metadata,indent=2))
            api.kernels_output(row['kernel'],str(folder),file_pattern=r'^(submission\.csv|publication\.json|lineage_before_publish\.json|audit_selected\.csv|audit_blend\.csv|.*\.log)$',force=True,quiet=True)
            after_version,after_sha,_=current_source()
            if (after_version,after_sha)!=(version,source_sha):raise ValueError('SOURCE_CHANGED_DURING_DOWNLOAD')
            proof=json.loads((folder/'publication.json').read_text());raw=(folder/'submission.csv').read_bytes()
            with (ROOT/'harness_data/sample_submission.csv').open() as stream:ids=[r['molecule_id'] for r in csv.DictReader(stream)]
            audit=check_artifact(raw,proof,row['variant'],ids,lambda s:Chem.MolFromSmiles(s) is not None,history)
            row.update(audit)
            for name,file in [('test_sha256','test.parquet'),('sample_sha256','sample_submission.csv')]:
                if proof.get(name)!=hashlib.sha256((ROOT/'harness_data'/file).read_bytes()).hexdigest():row['blockers'].append('PUBLIC_INPUT_HASH_MISMATCH')
            if raw!=(folder/'audit_selected.csv').read_bytes():row['blockers'].append('SELECTED_AUDIT_DIFFERS_FROM_FINAL')
            if (folder/'audit_blend.csv').read_bytes()!=(ROOT/'probeout_w088/submission.csv').read_bytes():row['blockers'].append('BASELINE_REGRESSION')
            for name in ['selected','blend']:
                artifact=folder/f'audit_{name}.csv';decl=proof.get('artifacts',{}).get(name,{})
                if decl.get('sha256')!=hashlib.sha256(artifact.read_bytes()).hexdigest() or decl.get('bytes')!=artifact.stat().st_size:row['blockers'].append('AUDIT_MANIFEST_MISMATCH')
            prior=ROOT/'probeout_wave8_atomic/submission.csv' if row['variant']=='formula_dedup' else ROOT/'probeout_wave8_extra'/row['variant']/'submission.csv'
            with prior.open() as stream:old_sig=semantic_hash(list(csv.DictReader(stream)))
            row['same_public_predictions_as_rejected_wave8']=row.get('semantic_sha256')==old_sig
            row['degraded']=proof.get('degraded');row['formula_coverage']=proof.get('formula_coverage')
            row['artifact_verified']=not row['blockers']
            if row.get('semantic_sha256'):fingerprints.setdefault(row['semantic_sha256'],[]).append(row)
            # NO automatic promotion: remote fallback semantics differ from our reviewed strict draft.
            row['blockers'].append('SOURCE_RUNTIME_POLICY_REVIEW_REQUIRED')
            if row['same_public_predictions_as_rejected_wave8']:row['blockers'].append('REPAIR_RETEST_REQUIRES_EXPLICIT_REVIEW')
            if row['variant']!='top1':row['blockers'].append('WAIT_FOR_CANARY_RESULT_REVIEW')
        except Exception as error:
            row['artifact_verified']=False;row['blockers'].append(type(error).__name__+': '+str(error));row['error_recorded_locally']=True
            with (ROOT/'incidents.jsonl').open('a') as stream:
                stream.write(json.dumps({'at':result['at'],'code':'NEXT_BATCH_PREFLIGHT','summary':str(error),
                    'context':{'kernel':row['kernel'],'action':'no retry/no submission'},'state':'OPEN_REQUIRES_DIAGNOSIS'},ensure_ascii=False)+'\n')
            # Access errors are not retried or worked around.
        result['candidates'].append(row)
    for items in fingerprints.values():
        if len(items)>1:
            for row in items:row['artifact_verified']=False;row['blockers'].append('DUPLICATE_WITHIN_CANDIDATES')
    result['artifact_verified_count']=sum(r['artifact_verified'] for r in result['candidates'])
    result['release_ready_count']=0
    (ROOT/'next_batch_preparation/readiness.json').write_text(json.dumps(result,indent=2))
    lines=['# Próximo lote CASMI — preparação, não autorização automática','',f"Atualizado: {result['at']}.",
           f"Arquivos tecnicamente verificados: {result['artifact_verified_count']}/5. Liberados para envio: 0/5.",
           'Nenhum envio realizado. Nenhum timer armado. As 21h de 28/09 já passaram; não foi reagendado silenciosamente para outro dia.','',
           '| Variante | Execução | Arquivo verificado | Bloqueios |','|---|---|---|---|']
    for row in result['candidates']:
        lines.append(f"| {row['variant']} | {row['execution_status'].get('status')} | {'SIM' if row['artifact_verified'] else 'NÃO'} | {'; '.join(row['blockers'])} |")
    lines+=['','## Sequência preparada','1. Confirmar fonte, versão, arquivo e mecanismo efetivamente executado.',
            '2. Resolver a política de fallback dos Wave9 existentes e o reteste dos CSVs públicos já rejeitados.',
            '3. Liberar apenas um envio corrigido, após revisão e autorização. Não há envio automático neste programa.',
            '4. Conferir nota, erro e atribuição desse controle antes de liberar os outros quatro.',
            '5. Reconsultar quota antes de qualquer envio; a disponibilidade da preparação não reserva vagas.',
            '', 'Passar nos testes públicos não prova compatibilidade com todos os dados ocultos. A causa exata da Wave8 continua sem confirmação.']
    (ROOT/'next_batch_preparation/STATUS.md').write_text('\n'.join(lines)+'\n')
    print('\n'.join(lines))

if __name__=='__main__':main()

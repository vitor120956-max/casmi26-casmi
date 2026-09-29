"""Final-only CSV publisher. Pure stdlib; validation failure leaves no submission.csv."""
import csv,hashlib,io,json,os,pathlib

class AtomicSubmission:
    contract = 'atomic-final-only-v1'

    def __init__(self, directory):
        self.directory=pathlib.Path(directory)
        self.final=self.directory/'submission.csv'
        self.staging=self.directory/'.submission.staging'
        self.manifest=self.directory/'publication.json'

    def begin(self):
        self.directory.mkdir(parents=True,exist_ok=True)
        for p in (self.final,self.staging,self.manifest):
            if p.exists():p.unlink()

    @staticmethod
    def validate(records, sample_ids, smiles_validator):
        ids=[str(x) for x in sample_ids]
        if not ids or len(set(ids))!=len(ids):raise ValueError('SAMPLE_IDS_INVALID')
        clean=[]
        for r in records:
            if set(r)!={'molecule_id','smiles'}:raise ValueError('CSV_SCHEMA')
            if r['molecule_id'] is None or not isinstance(r['smiles'],str):raise ValueError('CSV_NULL_OR_DTYPE')
            smi=r['smiles'].split(';')
            if len(smi)!=25 or not all(smi):raise ValueError('CANDIDATE_COUNT')
            if not all(smiles_validator(x) for x in smi):raise ValueError('INVALID_SMILES')
            clean.append({'molecule_id':str(r['molecule_id']),'smiles':r['smiles']})
        if [r['molecule_id'] for r in clean]!=ids:raise ValueError('SAMPLE_ID_ORDER_OR_LENGTH')
        return clean,ids

    def publish(self, records, sample_ids, smiles_validator, proof, fault=None):
        # Clear stale previous results even when validation is about to fail.
        self.begin()
        def checkpoint(stage):
            if fault is not None:fault(stage)
        try:
            checkpoint('before_validation')
            rows,ids=self.validate(records,sample_ids,smiles_validator)
            checkpoint('after_validation')
            buf=io.StringIO(newline='')
            writer=csv.DictWriter(buf,fieldnames=['molecule_id','smiles'],lineterminator='\n')
            writer.writeheader();writer.writerows(rows);data=buf.getvalue().encode('utf-8')
            report=dict(proof)
            report.update(publication_contract=self.contract,file='submission.csv',rows=len(rows),
                          bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),
                          sample_ids_sha256=hashlib.sha256(json.dumps(ids,separators=(',',':')).encode()).hexdigest())
            # Serialize proof before publication; malformed proof cannot leave final CSV.
            manifest_data=json.dumps(report,ensure_ascii=False,indent=2).encode('utf-8')
            with self.staging.open('wb') as f:
                f.write(data);f.flush();os.fsync(f.fileno())
            checkpoint('after_staging')
            self.manifest.write_bytes(manifest_data)
            checkpoint('after_manifest')
            checkpoint('before_publish')
            os.replace(self.staging,self.final)  # sole publication; no mutation afterwards
            return report
        except BaseException:
            self.begin()
            raise

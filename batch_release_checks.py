"""Pure checks for a candidate artifact. Does not authorize or send submissions."""
import csv,hashlib,io,json,math

def semantic_hash(rows):
    return hashlib.sha256(json.dumps(sorted((r['molecule_id'],r['smiles']) for r in rows),separators=(',',':')).encode()).hexdigest()

def check_artifact(raw, proof, expected_variant, sample_ids, valid_smiles, historical_hashes=()):
    reasons=[]
    if proof.get('publication_contract')!='atomic-final-only-v1':reasons.append('PUBLICATION_CONTRACT')
    if proof.get('variant')!=expected_variant:reasons.append('VARIANT_MISMATCH')
    if proof.get('cpu_only') is not True or proof.get('full_pipeline') is not True or proof.get('own_dataset_inputs') is not False:reasons.append('PIPELINE_PROVENANCE')
    if hashlib.sha256(raw).hexdigest()!=proof.get('sha256') or len(raw)!=proof.get('bytes'):reasons.append('FILE_HASH_OR_SIZE')
    degraded=proof.get('degraded')
    if not isinstance(degraded,list):reasons.append('DEGRADATION_STATUS_UNKNOWN')
    elif any(not isinstance(x,list) or not x or x[0]!='FORMULA_ROWS_WITHOUT_EVIDENCE' for x in degraded):reasons.append('DEGRADED_RUNTIME_OR_MECHANISM')
    if proof.get('msbuddy_available') is not True:reasons.append('MSBUDDY_UNAVAILABLE')
    coverage=proof.get('formula_coverage')
    if not isinstance(coverage,(int,float)) or isinstance(coverage,bool) or not math.isfinite(coverage) or not 0<coverage<=1:reasons.append('NO_VALID_FORMULA_EVIDENCE')
    changed=proof.get('selected_vs_blend_changed_rows')
    if not isinstance(changed,int) or isinstance(changed,bool) or changed<=0:reasons.append('NO_EFFECT_ON_PUBLIC_PREVIEW')
    if expected_variant.endswith('_dedup'):
        stats=proof.get('dedup',{})
        if stats.get('padded_slots')!=0 or stats.get('rows_without_mass')!=0:reasons.append('DEDUP_INCOMPLETE_OR_UNKNOWN')
    try:
        reader=csv.DictReader(io.StringIO(raw.decode('utf-8')));rows=list(reader)
        if reader.fieldnames!=['molecule_id','smiles']:raise ValueError('CSV_SCHEMA')
        ids=[str(x) for x in sample_ids]
        if not ids or len(set(ids))!=len(ids):raise ValueError('SAMPLE_IDS_INVALID')
        if [row['molecule_id'] for row in rows]!=ids:raise ValueError('CSV_IDS_OR_ORDER')
        if proof.get('rows')!=len(rows) or proof.get('expected_rows')!=len(rows):raise ValueError('CSV_ROW_COUNT')
        for row in rows:
            if set(row)!={'molecule_id','smiles'}:raise ValueError('CSV_EXTRA_COLUMNS')
            candidates=row['smiles'].split(';')
            if len(candidates)!=25 or not all(candidates):raise ValueError('CSV_CANDIDATE_COUNT')
            if not all(valid_smiles(s) for s in candidates):raise ValueError('INVALID_SMILES')
        signature=semantic_hash(rows)
        if signature in historical_hashes:reasons.append('DUPLICATE_HISTORICAL_PREDICTIONS')
    except (ValueError,TypeError,KeyError,AttributeError,UnicodeDecodeError) as error:
        reasons.append(str(error));signature=None
    return {'artifact_verified':not reasons,'blockers':reasons,'sha256':hashlib.sha256(raw).hexdigest(),'semantic_sha256':signature}

def release_gate(*,artifact_verified,version_confirmed,source_reviewed,canary_reviewed,is_canary,send_authorized):
    # An artifact passing unit/file checks is NOT automatically safe to spend a slot.
    return all([artifact_verified,version_confirmed,source_reviewed,send_authorized,(is_canary or canary_reviewed)])

"""Project untrusted extraction proposals into the current explicit-review flow.

Broader facts remain in draft metadata. They are never silently promoted into
committed records or made available to the question tools.
"""
from hashlib import sha256

from modus.ingest import make_draft
from modus.history_ingest import attach_facts


LABELS = {
    'lab_report': 'Lab report', 'checkup': 'Checkup',
    'prescription': 'Prescription', 'discharge_summary': 'Discharge summary',
    'vaccination_card': 'Vaccination record', 'imaging_report': 'Imaging report',
    'other': 'Document',
}


def review_draft(filename, raw, result):
    """Only called with the server-validated extraction envelope, never form JSON."""
    rows = result['observations']
    if rows:
        draft = make_draft(filename, raw, rows)
    else:
        digest = sha256(raw).hexdigest()
        source_id = 'import-' + digest[:20]
        draft = {'id': source_id, 'subject_id': None, 'source': {
            'id': source_id, 'title': filename[:120], 'provider': 'Imported synthetic document',
            'date': '', 'type': LABELS[result['document_type']], 'synthetic': True,
            'content': '', 'sha256': digest, 'extraction_mode': 'meta',
        }, 'observations': [], 'warnings': [], 'extraction_mode': 'meta'}
    facts = []
    for field in result['fields']:
        issues = []
        local = field['local_support']
        if local['status'] == 'mismatch':
            issues.append('Some details do not match the text on the cited page.')
        elif local['status'] == 'unavailable':
            issues.append('The page has no readable text to compare. Check the original image.')
        if 'ocr_text_is_unverified' in local.get('issues', []):
            issues.append('This comparison uses a local transcription. Check the original image too.')
        verified = field['verification']['status']
        if verified == 'mismatch':
            issues.append('The second reading disagrees with this field.')
        elif verified in {'uncertain', 'unavailable'}:
            issues.append('The second reading could not confirm this field.')
        facts.append({
            'id': field['id'], 'label': field['label'], 'value': field['value'],
            'unit': field['unit'], 'date': field['occurred_on'], 'page': field['page'],
            'source_quote': field['source_quote'], 'bbox': field['bbox'],
            'model_confidence': field['model_confidence'], 'review_reasons': issues,
            'commit_supported': True,
        })
    draft['source']['type'] = LABELS[result['document_type']]
    draft['extraction_review'] = {
        'document_type': result['document_type'],
        'verification_status': result['verification']['status'],
        'facts': facts, 'review_required': True,
    }
    # Preserve exact model proposals, checks and non-calibrated confidence for
    # later review without exposing them as committed or historically known facts.
    draft['extraction_proposal'] = result
    if 'document_guard' in result:
        draft['source_document_guard'] = result['document_guard']
    if result['fields']:
        attach_facts(draft, [{**field, 'facility': None, 'extractor': 'meta',
            'review_reasons': facts[index]['review_reasons']}
            for index, field in enumerate(result['fields'])])
    return draft

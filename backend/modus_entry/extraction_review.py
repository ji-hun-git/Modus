"""Project untrusted extraction proposals into the current explicit-review flow.

Broader facts remain in draft metadata. They are never silently promoted into
committed records or made available to the question tools.
"""
from hashlib import sha256

from modus.ingest import make_draft
from modus.history_ingest import attach_facts
from .report_coverage import public_coverage


LABELS = {
    'lab_report': 'Lab report', 'checkup': 'Checkup',
    'prescription': 'Prescription', 'discharge_summary': 'Discharge summary',
    'vaccination_card': 'Vaccination record', 'imaging_report': 'Imaging report',
    'other': 'Document',
}


def support_review_reasons(local):
    """Describe the failed check without claiming the source itself is wrong."""
    reasons = []
    if local['status'] == 'mismatch':
        names = {'label': 'name', 'value': 'value', 'unit': 'unit', 'occurred_on': 'date',
                 'reference_range': 'reference range', 'specimen': 'specimen', 'test_method': 'test method'}
        for issue in local.get('issues', []):
            if issue == 'quote_not_on_page':
                reasons.append('This excerpt could not be located in the text of the cited page. Check the original.')
            elif issue == 'numeric_qualifier_not_preserved':
                reasons.append('A sign, limit or qualifier may be missing from the result. Check the original value.')
            elif issue.endswith('_not_in_quote') and issue[:-13] in names:
                name = names[issue[:-13]]
                reasons.append(f'The {name} is not included in this excerpt. Check it on the original report.')
        if not reasons:
            reasons.append('Some extracted details could not be matched to this excerpt. Check the original report.')
    elif local['status'] == 'unavailable':
        reasons.append('The page has no readable text to compare. Check the original image.')
    if 'ocr_text_is_unverified' in local.get('issues', []):
        reasons.append('This comparison uses a local transcription. Check the original image too.')
    for issue, message in {
        'date_link_requires_review': 'The date was found in a separate passage. Check that it belongs to this result.',
        'date_evidence_mismatch': 'The separate date passage could not be matched. Check the original date and its connection to this result.',
        'date_evidence_unavailable': 'The separate date passage has no independent text check. Check the original and its connection to this result.',
    }.items():
        if issue in local.get('issues', []):
            reasons.append(message)
    return reasons


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
        issues = support_review_reasons(field['local_support'])
        verified = field['verification']['status']
        if verified == 'mismatch':
            issues.append('The second reading disagrees with this field.')
        elif verified in {'uncertain', 'unavailable'}:
            issues.append('The second reading could not confirm this field.')
        if field.get('inventory_check', {}).get('status') == 'unmatched':
            issues.append('The separate row check did not find this proposed entry. Check that it is a recorded result or history item.')
        elif field.get('inventory_check', {}).get('status') == 'unit_disagreement':
            proposed_unit = field['inventory_check']['proposed_unit']
            shown = repr(proposed_unit) if proposed_unit is not None else 'not recorded'
            issues.append(f'The separate row check read the unit as {shown}. Check this entry\'s unit in the original; do not add a duplicate row.')
        facts.append({
            'id': field['id'], 'label': field['label'], 'value': field['value'],
            'unit': field['unit'], 'date': field['occurred_on'], 'page': field['page'],
            'source_quote': field['source_quote'], 'bbox': field['bbox'],
            'date_evidence': field.get('date_evidence'),
            'model_confidence': field['model_confidence'], 'review_reasons': issues,
            'commit_supported': True,
        })
    draft['source']['type'] = LABELS[result['document_type']]
    draft['extraction_review'] = {
        'document_type': result['document_type'],
        'verification_status': result['verification']['status'],
        'facts': facts, 'review_required': True,
    }
    coverage = public_coverage(result.get('coverage'))
    if coverage:
        draft['extraction_review']['coverage'] = coverage
        if not result['fields']:
            draft['facts'] = []  # Read-only review of an empty proposal; commits still reject.
    if 'completeness_check' in result:
        # Server-generated comparison of validated inventory rows. These remain
        # review warnings, never eligible field IDs for either commit endpoint.
        draft['extraction_review']['completeness_check'] = result['completeness_check']
        check = result['completeness_check']
        # A possible omitted row has no reviewed date. Do not expose its full
        # original through a dated history view merely because extracted rows fit.
        draft['source']['unresolved_row_inventory'] = bool(check['omissions'] or check.get('disagreements') or check['status'] != 'completed')
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

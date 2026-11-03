"""Explicit review of stored inventory candidates. No extraction or model writes."""
from hashlib import sha256
import json

from .record_history_models import ReviewedFact


class OmissionConflict(ValueError):
    pass


def omission_proposals(draft):
    check = draft.get('extraction_review', {}).get('completeness_check', {})
    if check.get('version') != 'report-row-inventory-v1':
        return {}
    return {row['id']: {
        'id': row['id'], 'kind': 'recorded_text', 'label': row['label'],
        'value': row['value'], 'unit': row['unit'], 'occurred_on': None, 'facility': None,
        'reference_range': None, 'specimen': None, 'test_method': None,
        'source_quote': row['source_quote'], 'page': row['page'], 'bbox': row.get('bbox'),
        'model_confidence': None, 'extractor': 'meta-row-inventory-reviewed',
        'local_support': {'status': row['local_support']},
        'row_inventory': {'candidate_id': row['id'], 'reason': row['reason'],
                          'local_support': row['local_support']},
    } for row in check.get('omissions', [])}


def review_omissions(draft, submitted):
    if not isinstance(submitted, list) or len(submitted) > 400:
        raise ValueError('Review at most 400 flagged rows')
    proposed = omission_proposals(draft)
    rows = [ReviewedFact.model_validate(value).model_dump() for value in submitted]
    ids = [row['id'] for row in rows]
    if len(ids) != len(set(ids)) or not set(ids) <= proposed.keys():
        raise ValueError('Reviewed omissions must have distinct IDs from this report inventory')
    return proposed, rows


def review_digest(rows):
    return sha256(json.dumps(sorted(rows, key=lambda row: row['id']),
                             sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def previous_review(db, draft_id, rows):
    saved = [db.execute('SELECT review_digest,data FROM history_omission_reviews WHERE draft_id=? AND candidate_id=?',
                        (draft_id, row['id'])).fetchone() for row in rows]
    if not any(saved):
        return None
    digest = review_digest(rows)
    if not all(row and row['review_digest'] == digest for row in saved):
        raise OmissionConflict('A flagged row was already saved. Reopen this file to review remaining rows; use Corrections to edit saved entries.')
    return {**json.loads(saved[0]['data']), 'duplicate': True, 'inserted': 0}


def remember_review(db, draft_id, rows, facts, receipt):
    digest = review_digest(rows)
    for row in rows:
        fact = next(fact for fact in facts if fact['proposal_id'] == row['id'])
        db.execute('INSERT INTO history_omission_reviews VALUES(?,?,?,?,?,?)',
                   (draft_id, row['id'], digest, fact['id'], receipt['available_at'], json.dumps(receipt)))


def omission_review_state(store, draft_id):
    with store.connect() as db:
        rows = db.execute('SELECT candidate_id,fact_id,available_at FROM history_omission_reviews WHERE draft_id=? ORDER BY candidate_id', (draft_id,)).fetchall()
        source = db.execute('SELECT s.available_at FROM sources s JOIN drafts d ON json_extract(d.data,\'$.source.id\')=s.id WHERE d.id=?', (draft_id,)).fetchone()
    return {'omission_reviews': [dict(row) for row in rows],
            'saved_available_at': source['available_at'] if source else None}


def commit_omissions(store, draft_id, submitted):
    # The existing fact builder/provenance and audit writer are shared with the
    # initial import. A second transaction only appends explicitly reviewed rows.
    from .record_history import build_reviewed_facts, write_reviewed_facts
    from .temporal import instant
    with store.connect() as db:
        db.execute('BEGIN IMMEDIATE')
        saved = db.execute('SELECT data,committed FROM drafts WHERE id=?', (draft_id,)).fetchone()
        if not saved:
            raise ValueError('Draft not found')
        draft = json.loads(saved['data'])
        proposed, rows = review_omissions(draft, submitted)
        if not rows:
            raise ValueError('Select at least one flagged row to save')
        repeated = previous_review(db, draft_id, rows)
        if repeated:
            return repeated
        source_row = db.execute('SELECT data FROM sources WHERE id=?', (draft['source']['id'],)).fetchone()
        if not saved['committed'] or not source_row:
            raise OmissionConflict('Save this report through the initial review first')
        source = json.loads(source_row['data'])
        now = instant(store.clock())
        facts, observations = build_reviewed_facts(draft, source, proposed, rows, now,
                                                  'local-owner', 'reviewed_row_addition')
        result = write_reviewed_facts(store, db, draft_id, source, facts, observations, now)
        result['omission_ids'] = [row['id'] for row in rows]
        remember_review(db, draft_id, rows, facts, result)
        # The immutable draft, source, initial receipt and original bytes are
        # untouched. Remaining unknown rows still restrict dated originals.
        return result

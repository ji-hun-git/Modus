"""Human-reviewed append-only corrections. No model write capability."""
from copy import deepcopy
from hashlib import sha256
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .record_history import _bridge
from .record_history_models import ReviewedFact, date_information
from .record_history_view import _read_history_snapshot, _project_history, raw_history_facts
from .temporal import instant

FIELDS = ('kind', 'label', 'value', 'unit', 'occurred_on', 'facility')


class AmendmentConflict(ValueError):
    pass


class AmendmentRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    expected_revision_id: str = Field(min_length=1, max_length=160)
    corrected: ReviewedFact
    reason: str = Field(min_length=1, max_length=500)

    @field_validator('reason')
    @classmethod
    def nonblank_reason(cls, value):
        if not value.strip():
            raise ValueError('Explain why you are correcting this record')
        return value.strip()


class AmendmentCommitRequest(AmendmentRequest):
    preview_id: str = Field(pattern=r'^sha256:[a-f0-9]{64}$')
    reviewed: Literal[True]

    @field_validator('reviewed', mode='before')
    @classmethod
    def explicit_review(cls, value):
        if value is not True:
            raise ValueError('Review the correction before saving')
        return value


def _digest(request):
    body = {key: request.model_dump()[key] for key in ('expected_revision_id', 'corrected', 'reason')}
    return 'sha256:' + sha256(json.dumps({'contract': 'record-amendment-v1', **body}, sort_keys=True,
                                      ensure_ascii=False).encode()).hexdigest()


def _prepare(db, request, now):
    state = _read_history_snapshot(db, now)
    current = next((row for row in raw_history_facts(state) if row['id'] == request.corrected.id), None)
    if current is None:
        raise ValueError('Saved record not found')
    if current['revision_id'] != request.expected_revision_id:
        raise AmendmentConflict('This record changed. Load its latest version and review again.')
    changes = {key: {'before': current.get(key), 'after': getattr(request.corrected, key)}
               for key in FIELDS if current.get(key) != getattr(request.corrected, key)}
    if not changes:
        raise ValueError('The correction does not change any saved field')
    return current, changes


def preview_amendment(store, request):
    with store.connect() as db:
        db.execute('BEGIN IMMEDIATE')
        now = instant(store.clock())
        current, changes = _prepare(db, request, now)
        return {'preview_id': _digest(request), 'record': current,
                'corrected': request.corrected.model_dump(), 'changes': changes, 'reason': request.reason,
                'captured_at': now, 'reviewed': False}


def commit_amendment(store, request):
    digest = _digest(request)
    if request.preview_id != digest:
        raise AmendmentConflict('The correction differs from its preview. Review it again.')
    with store.connect() as db:
        db.execute('BEGIN IMMEDIATE')
        prior = db.execute('SELECT data FROM history_amendments WHERE id=?', (digest,)).fetchone()
        if prior:
            return {**json.loads(prior[0])['receipt'], 'duplicate': True}
        now = instant(store.clock())
        current, changes = _prepare(db, request, now)
        if now <= current['available_at']:
            raise AmendmentConflict('The correction clock must follow the current revision. Retry after the clock advances.')
        fact = {**deepcopy(current), **request.corrected.model_dump(), **date_information(request.corrected.occurred_on),
                'revision_id': digest, 'previous_revision_id': current['revision_id'],
                'available_at': now, 'availability_basis': 'reviewed_amendment',
                'reviewer': 'local-owner', 'reviewed_at': now}
        # Original proposal, quote, bytes and first availability never change.
        fact['reviewed_fields'] = sorted(set(current.get('reviewed_fields', [])) | set(changes))
        observation = _bridge(fact, fact['source_id'])
        previous_observation_id = current.get('observation_id')
        if observation:
            observation['id'] = previous_observation_id or fact['id'] + '-measurement'
            observation.update(available_at=now, availability_basis='reviewed_amendment')
            original_observation = db.execute('SELECT data FROM observations WHERE id=?', (observation['id'],)).fetchone()
            if original_observation:
                reported = json.loads(original_observation[0])
                for key in ('reported_at', 'reported_at_raw'):
                    if key in reported:
                        observation[key] = reported[key]
        fact['observation_id'] = observation['id'] if observation else None
        receipt = {'amendment_id': digest, 'fact_id': fact['id'], 'source_id': fact['source_id'],
                   'previous_revision_id': current['revision_id'], 'revision_id': digest,
                   'available_at': now, 'changed_fields': sorted(changes), 'duplicate': False}
        amendment = {'fact_id': fact['id'], 'source_id': fact['source_id'], 'available_at': now,
                     'fact': fact, 'observation': observation, 'reason': request.reason,
                     'replaced_observation_ids': [previous_observation_id] if previous_observation_id else [],
                     'changes': changes, 'receipt': receipt}
        db.execute('INSERT INTO history_amendments(id,fact_id,source_id,available_at,data) VALUES(?,?,?,?,?)',
                   (digest, fact['id'], fact['source_id'], now, json.dumps(amendment)))
        db.execute('INSERT INTO runs(created_at,data) VALUES(?,?)', (now, json.dumps({
            'schema': 'modus-entry-change-v1', 'kind': 'amendment', 'status': 'completed',
            'mode': 'deterministic', 'fact_id': fact['id'], 'source_id': fact['source_id'],
            'revision_id': digest, 'available_at': now, 'fact_count': 1})))
        return receipt


def revision_history(store, fact_id, known_at=None, as_of=None):
    with store.connect() as db:
        db.execute('BEGIN IMMEDIATE')
        captured = instant(store.clock())
        cutoff = min(instant(known_at), captured) if known_at is not None else captured
        state = _read_history_snapshot(db, cutoff)
    sources, generic, legacy, originals, profile, amendments = state
    baseline = next((row for row in raw_history_facts((*state[:5], [])) if row['id'] == fact_id), None)
    if baseline is None:
        raise ValueError('Saved record not found')
    versions = [(baseline, None)] + [(row['fact'], row['reason']) for row in amendments if row['fact_id'] == fact_id]
    if len(versions) > 1000:
        raise ValueError('This record exceeds the revision history limit')
    result = []
    for fact, reason in versions:
        view = _project_history((sources, [fact], [], originals, profile, []), as_of, cutoff, captured)
        rows = view['facts'] + view['undated_facts']
        if rows:
            result.append({'fact': rows[0], 'reason': reason if as_of is None else None})
    return {'fact_id': fact_id, 'versions': result, 'scope': {'as_of': as_of, 'known_at': cutoff},
            'actor_basis': 'local-owner is a local review label, not an authenticated identity'}

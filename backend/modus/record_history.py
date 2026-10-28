"""Transactional lifelong record facts alongside the existing measurement store."""
from copy import deepcopy
from datetime import date
from decimal import Decimal
from hashlib import sha256
import json
import re

from .record_conflicts import conflicts
from .record_extraction import _compatible_observation
from .record_history_models import ReviewedFact, SourceEvidence, date_information, proposed_facts
from .record_models import Observation
from .temporal import instant


def initialize_history(db):
    for sql in (
        'CREATE TABLE IF NOT EXISTS history_facts (id TEXT PRIMARY KEY, source_id TEXT NOT NULL REFERENCES sources(id), kind TEXT NOT NULL, date TEXT, available_at TEXT NOT NULL, data TEXT NOT NULL)',
        'CREATE TABLE IF NOT EXISTS history_commits (draft_id TEXT PRIMARY KEY REFERENCES drafts(id), review_digest TEXT NOT NULL, data TEXT NOT NULL)',
        'CREATE TABLE IF NOT EXISTS history_profiles (id INTEGER PRIMARY KEY, updated_at TEXT NOT NULL, data TEXT NOT NULL)',
        'CREATE INDEX IF NOT EXISTS history_fact_scope ON history_facts(available_at,date,source_id)',
    ):
        db.execute(sql)


def reset_history(db):
    for table in ('history_commits', 'history_facts', 'history_profiles'):
        db.execute('DELETE FROM ' + table)


def _review_rows(draft, reviewed_facts):
    if not isinstance(reviewed_facts, list) or not 1 <= len(reviewed_facts) <= 1000:
        raise ValueError('Select 1 to 1,000 reviewed facts')
    proposed = proposed_facts(draft)
    rows = [ReviewedFact.model_validate(value).model_dump() for value in reviewed_facts]
    ids = [row['id'] for row in rows]
    if len(ids) != len(set(ids)) or not set(ids) <= proposed.keys():
        raise ValueError('Reviewed facts must have distinct IDs belonging to this draft')
    return proposed, rows


def _provenance(proposed, draft):
    # This projection only reads saved server proposals, never the review body.
    evidence = SourceEvidence.model_validate({key: proposed.get(key) for key in (
        'source_quote', 'page', 'bbox', 'model_confidence')}).model_dump()
    return evidence | {key: deepcopy(proposed.get(key)) for key in ('local_support', 'verification', 'reported_at_raw')} | {
        'extractor': deepcopy(proposed.get('extractor') or draft.get('extraction_mode') or 'manual'),
        'source_proposal': {key: deepcopy(proposed.get(key)) for key in (
            'kind', 'label', 'value', 'unit', 'occurred_on', 'facility')},
    }


def _bridge(fact, source_id):
    candidate = _compatible_observation({**fact, 'source_quote': fact.get('source_quote') or '',
                                        'page': fact.get('page')})
    if not candidate:
        return None
    if Decimal(str(candidate['value'])) != Decimal(fact['value']):
        # General facts retain exact decimals; old charts must not silently round.
        return None
    observation_id = fact['id'] + '-measurement'
    try:
        row = Observation.model_validate({**candidate, 'id': observation_id, 'source_id': source_id}).model_dump(mode='json')
    except ValueError:
        return None
    mapping = {'label': 'metric', 'occurred_on': 'date', 'value': 'value', 'unit': 'unit'}
    row['reviewed_fields'] = [mapping[key] for key in fact['reviewed_fields'] if key in mapping]
    return Observation.model_validate(row).model_dump(mode='json')


def commit_history(store, draft_id, reviewed_facts, *, reviewer='local-owner'):
    if not isinstance(reviewer, str) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,80}', reviewer):
        raise ValueError('Invalid server review identity')
    with store.connect() as db:
        db.execute('BEGIN IMMEDIATE')
        saved = db.execute('SELECT data,committed FROM drafts WHERE id=?', (draft_id,)).fetchone()
        if not saved:
            raise ValueError('Draft not found')
        draft = json.loads(saved['data'])
        proposed, rows = _review_rows(draft, reviewed_facts)
        digest = sha256(json.dumps(sorted(rows, key=lambda row: row['id']), sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        receipt = db.execute('SELECT review_digest,data FROM history_commits WHERE draft_id=?', (draft_id,)).fetchone()
        if receipt:
            if receipt['review_digest'] != digest:
                raise ValueError('This draft was already saved with different reviewed facts')
            return {**json.loads(receipt['data']), 'duplicate': True, 'inserted': 0}
        source = deepcopy(draft['source'])
        if saved['committed'] or db.execute('SELECT 1 FROM sources WHERE id=?', (source['id'],)).fetchone():
            raise ValueError('This source was already committed; an additional review cannot backdate facts')
        now = instant(store.clock())
        facts, observations = [], []
        for reviewed in rows:
            original = proposed[reviewed['id']]
            identity = 'fact-' + sha256((source.get('sha256', source['id']) + ':' + reviewed['id']).encode()).hexdigest()[:32]
            fact = {**reviewed, **_provenance(original, draft), **date_information(reviewed['occurred_on']),
                    'id': identity, 'proposal_id': reviewed['id'], 'source_id': source['id'],
                    'available_at': now, 'availability_basis': 'review_commit', 'reviewer': reviewer, 'reviewed_at': now,
                    'reviewed_fields': [key for key in reviewed if key != 'id' and reviewed[key] != original.get(key)]}
            observation = _bridge(fact, source['id'])
            fact['observation_id'] = observation['id'] if observation else None
            facts.append(fact)
            if observation:
                observations.append(observation)
        dates = [fact['date'] for fact in facts]
        # Retain original proposal dates too: excluding/editing a future row does
        # not remove that row from the original uploaded bytes.
        proposal_dates = [date_information(value.get('occurred_on'))['date'] for value in proposed.values()]
        source.update(available_at=now, availability_basis='review_commit', committed_at=now,
                      date=max((day for day in dates if day), default=''), source_fact_dates=dates + proposal_dates,
                      original_date=max((day for day in dates + proposal_dates if day), default=''))
        source['review'] = {'reviewed_at': now, 'reviewer': reviewer, 'accepted_ids': [row['id'] for row in rows],
                            'excluded_ids': sorted(set(proposed) - {row['id'] for row in rows})}
        db.execute('INSERT INTO sources(id,data,available_at) VALUES(?,?,?)', (source['id'], json.dumps(source), now))
        for fact in facts:
            db.execute('INSERT INTO history_facts VALUES(?,?,?,?,?,?)',
                       (fact['id'], source['id'], fact['kind'], fact['date'], now, json.dumps(fact)))
        for row in observations:
            db.execute('INSERT INTO observations VALUES(?,?,?,?,?)',
                       (row['id'], source['id'], row['metric'], row['date'], json.dumps(row)))
        affected = []
        for metric, day in sorted({(row['metric'], row['date']) for row in observations}):
            affected.extend(json.loads(row[0]) for row in db.execute(
                'SELECT o.data FROM observations o JOIN sources s ON s.id=o.source_id WHERE o.metric=? AND o.date=? AND s.available_at<=?',
                (metric, day, now)))
        result = {'inserted': len(facts), 'duplicate': False, 'draft_id': draft_id, 'source_id': source['id'],
                  'available_at': now, 'fact_ids': [fact['id'] for fact in facts],
                  'observation_ids': [row['id'] for row in observations], 'affected_conflicts': conflicts(affected)}
        db.execute('UPDATE drafts SET committed=1 WHERE id=?', (draft_id,))
        db.execute('INSERT INTO history_commits VALUES(?,?,?)', (draft_id, digest, json.dumps(result)))
        db.execute('INSERT INTO record_commits VALUES(?,?)', (draft_id, json.dumps(result)))
        if store._commit_event_factory is not None:
            event = store._commit_event_factory(deepcopy(result))
            if not isinstance(event, dict):
                raise TypeError('A commit event factory must return an object')
            db.execute('INSERT INTO runs(created_at,data) VALUES(?,?)', (now, json.dumps(event)))
        return result


def update_profile(store, date_of_birth):
    if date_of_birth is not None:
        if not isinstance(date_of_birth, str) or date_information(date_of_birth)['date'] is None:
            raise ValueError('Date of birth must be an exact ISO date or null')
        if date.fromisoformat(date_of_birth) > date.fromisoformat(instant(store.clock())[:10]):
            raise ValueError('Date of birth cannot be in the future')
    with store.connect() as db:
        db.execute('BEGIN IMMEDIATE')
        now = instant(store.clock())
        profile = {'date_of_birth': date_of_birth, 'updated_at': now, 'storage': 'local'}
        db.execute('INSERT INTO history_profiles(updated_at,data) VALUES(?,?)', (now, json.dumps(profile)))
        return profile


def get_profile(store, known_at=None):
    with store.connect() as db:
        cutoff = min(instant(known_at), instant(store.clock())) if known_at is not None else instant(store.clock())
        row = db.execute('SELECT data FROM history_profiles WHERE updated_at<=? ORDER BY updated_at DESC,id DESC LIMIT 1', (cutoff,)).fetchone()
        return json.loads(row['data']) if row else {'date_of_birth': None, 'updated_at': None, 'storage': 'local'}


from .record_history_view import history_view  # Public facade; views have no write capabilities.

"""New authored correction cases. No held-out inputs or provider requests."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import importlib

from fastapi.testclient import TestClient
import pytest

from modus.record_amendments import FIELDS

START = datetime(2026, 10, 29, 12, tzinfo=timezone.utc)
CSV = b'kind,label,value,unit,date,facility\nmeasurement,HbA1c,5.6,%,2024-02-03,Example lab\n'


@pytest.fixture
def service(tmp_path, monkeypatch):
    monkeypatch.setenv('MODUS_ENTRY_DB_PATH', str(tmp_path / 'unused.db'))
    module = importlib.import_module('modus_entry.app')
    clock = [START]
    app = module.create_entry_app(tmp_path / 'corrections.db', clock=lambda: clock[0])
    with TestClient(app) as client:
        draft = client.post('/api/imports/preview', data={'synthetic_confirmed': 'true'},
            files={'file': ('correction.csv', CSV, 'text/csv')}).json()
        reviewed = [{key: fact[key] for key in ('id', *FIELDS)} for fact in draft['facts']]
        response = client.post('/api/history/commit', json={'draft_id': draft['id'],
            'synthetic_confirmed': True, 'reviewed_facts': reviewed})
        assert response.status_code == 200, response.text
        identity = response.json()['fact_ids'][0]
        clock[0] += timedelta(seconds=1)
        yield client, app.state.store, clock, identity, draft['source']['id']


def fact(client, identity, **params):
    view = client.get('/api/history/view', params=params).json()
    return next(row for row in view['facts'] + view['undated_facts'] if row['id'] == identity)


def prepare(client, identity, **changes):
    current = fact(client, identity)
    row = {key: current[key] for key in ('id', *FIELDS)} | changes
    body = {'expected_revision_id': current['revision_id'], 'corrected': row, 'reason': 'Corrected a transcription error'}
    response = client.post('/api/history/amendments/preview', json=body)
    assert response.status_code == 200, response.text
    return {**body, 'preview_id': response.json()['preview_id'], 'reviewed': True}


def save(client, body):
    response = client.post('/api/history/amendments/commit', json=body)
    assert response.status_code == 200, response.text
    return response.json()


def test_correction_preserves_original_bytes_rows_and_both_clocks(service):
    client, store, clock, identity, source = service
    before = fact(client, identity)
    with store.connect() as db:
        original = {table: [tuple(row) for row in db.execute('SELECT * FROM ' + table)]
                    for table in ('sources', 'observations', 'history_facts', 'drafts', 'documents')}
    receipt = save(client, prepare(client, identity, value='5.8'))
    current = fact(client, identity)
    assert current['value'] == '5.8' and current['date'] == before['date']
    assert current['source_quote'] == before['source_quote'] and '5.6' in current['source_quote']
    assert current['source_proposal'] == before['source_proposal']
    assert current['first_available_at'] == before['available_at']
    assert current['available_at'] == receipt['available_at']
    assert fact(client, identity, known_at=START.isoformat()) == before
    assert client.get(f'/api/history/sources/{source}/original', params={'known_at': clock[0].isoformat()}).content == CSV
    with store.connect() as db:
        for table, rows in original.items():
            assert [tuple(row) for row in db.execute('SELECT * FROM ' + table)] == rows
    assert client.get('/api/changes').json()['changes'][0]['kind'] == 'amendment'
    revisions = client.get(f'/api/history/facts/{identity}/revisions').json()
    assert [item['fact']['value'] for item in revisions['versions']] == ['5.6', '5.8']
    assert len(client.get(f'/api/history/facts/{identity}/revisions', params={'known_at': START.isoformat()}).json()['versions']) == 1


def test_legacy_charts_and_narrowed_snapshots_use_correct_version(service):
    client, store, clock, identity, _ = service
    original = fact(client, identity)
    save(client, prepare(client, identity, value='5.9'))
    snapshot = store.snapshot()
    before = {row['id']: row for row in snapshot.narrow(START).observations()}
    after = {row['id']: row for row in snapshot.observations()}
    oid = original['observation_id']
    assert before[oid]['value'] == 5.6 and after[oid]['value'] == 5.9
    assert after[oid]['source_span'] == original['source_quote']
    assert after[oid]['available_at'] > before[oid]['available_at']
    # Kind/unit/date edits must remove an incompatible old chart projection.
    clock[0] += timedelta(seconds=1)
    save(client, prepare(client, identity, kind='recorded_text', value='Original wording retained', unit=None))
    assert oid not in {row['id'] for row in store.snapshot().observations()}
    assert oid in {row['id'] for row in store.snapshot().narrow(START).observations()}


def test_seeded_legacy_record_can_be_corrected_without_changing_seed(service):
    client, store, clock, _, _ = service
    legacy = next(row for row in client.get('/api/history/view').json()['facts'] if row.get('legacy_projection'))
    save(client, prepare(client, legacy['id'], value='101'))
    assert fact(client, legacy['id'])['value'] == '101'
    assert fact(client, legacy['id'], known_at=START.isoformat())['value'] == legacy['value']


def test_replay_distinguishes_amendment_and_scope_exit_from_arrival(service):
    client, store, clock, identity, _ = service
    save(client, prepare(client, identity, value='5.8'))
    pair = client.post('/api/history/compare', json={'before_known_at': START.isoformat()}).json()
    assert pair['added'] == [] and len(pair['updated']) == 1
    assert pair['updated'][0]['before']['value'] == '5.6'
    assert pair['updated'][0]['after']['value'] == '5.8'
    assert pair['unchanged_count'] == pair['before']['counts']['facts'] - 1
    clock[0] += timedelta(seconds=1)
    save(client, prepare(client, identity, occurred_on='2025-02-03'))
    pair = client.post('/api/history/compare', json={'as_of': '2024-12-31', 'before_known_at': START.isoformat()}).json()
    assert [row['id'] for row in pair['removed_from_scope']] == [identity]
    assert pair['added'] == []


def test_retry_stale_preview_and_changed_payload_are_transactional(service):
    client, store, clock, identity, _ = service
    body = prepare(client, identity, value='5.8')
    stale = prepare(client, identity, value='6.0')
    receipt = save(client, body)
    assert save(client, body) == {**receipt, 'duplicate': True}
    assert client.post('/api/history/amendments/commit', json=stale).status_code == 409
    forged = deepcopy(body); forged['corrected']['value'] = '9.9'
    assert client.post('/api/history/amendments/commit', json=forged).status_code == 409
    clock[0] += timedelta(seconds=1)
    save(client, prepare(client, identity, value='6.1'))
    assert save(client, body)['duplicate'] is True
    assert fact(client, identity)['value'] == '6.1'
    with store.connect() as db:
        assert db.execute('SELECT COUNT(*) FROM history_amendments').fetchone()[0] == 2


@pytest.mark.parametrize('field,value', [('source_quote', 'forged'), ('source_id', 'other'),
    ('available_at', '2010-01-01T00:00:00Z'), ('reviewer', 'doctor'), ('page', 100)])
def test_source_and_authority_fields_cannot_be_corrected(service, field, value):
    client, _, _, identity, _ = service
    body = prepare(client, identity, value='5.8')
    body['corrected'][field] = value
    assert client.post('/api/history/amendments/commit', json=body).status_code == 422
    assert fact(client, identity)['value'] == '5.6'


@pytest.mark.parametrize('confirmed', [False, 1, 'true', None])
def test_confirmation_is_an_actual_boolean(service, confirmed):
    client, _, _, identity, _ = service
    body = prepare(client, identity, value='5.8') | {'reviewed': confirmed}
    assert client.post('/api/history/amendments/commit', json=body).status_code == 422


def test_noop_invalid_identity_and_backdated_clock_reject(service):
    client, _, clock, identity, _ = service
    current = fact(client, identity)
    body = {'expected_revision_id': current['revision_id'], 'corrected': {key: current[key] for key in ('id', *FIELDS)}, 'reason': 'No change'}
    assert client.post('/api/history/amendments/preview', json=body).status_code == 422
    prepared = prepare(client, identity, value='5.8')
    clock[0] = START
    assert client.post('/api/history/amendments/commit', json=prepared).status_code == 409


def test_briefs_and_factual_answers_refresh_without_changing_historical_brief(service):
    client, store, clock, identity, _ = service
    brief_body = {'known_at': START.isoformat(), 'selected_fact_ids': [identity]}
    old = client.post('/api/briefs/preview', json=brief_body).json()
    save(client, prepare(client, identity, value='5.8'))
    assert client.post('/api/briefs/preview', json=brief_body).json()['preview_id'] == old['preview_id']
    new = client.post('/api/briefs/preview', json=brief_body | {'known_at': clock[0].isoformat()}).json()
    assert new['entries'][0]['value'] == '5.8'
    assert '5.6' in new['entries'][0]['source_quote']
    answer = client.post('/api/history/chat', json={'message': 'Find records mentioning "HbA1c"'}).json()
    assert any('5.8' in claim['text'] and 'corrected in Modus' in claim['text'] for claim in answer['claims'])
    assert all(item.get('reviewer') is None and item.get('reason') is None for item in answer['history_evidence']['facts'])


@pytest.mark.parametrize('kind', ['measurement', 'encounter', 'recorded_diagnosis', 'procedure',
    'prescription', 'vaccination', 'imaging_text', 'recorded_text'])
def test_all_record_kinds_and_partial_dates_keep_their_original_source(service, kind):
    client, _, _, identity, _ = service
    original = fact(client, identity)
    save(client, prepare(client, identity, kind=kind, value='Corrected recorded wording', occurred_on='2012', unit=None))
    updated = fact(client, identity)
    assert updated['kind'] == kind and updated['date'] is None and updated['date_precision'] == 'year'
    assert updated['source_quote'] == original['source_quote']
    assert updated['source_proposal'] == original['source_proposal']


def test_correction_conflict_does_not_replace_a_different_source(service):
    client, _, clock, identity, _ = service
    peer = next(row for row in client.get('/api/history/view').json()['facts'] if row['label'] == 'HbA1c' and row['date'] == '2026-10-20')
    save(client, prepare(client, identity, value='9.1', occurred_on=peer['date']))
    conflicts = client.get('/api/history/view').json()['conflicts']
    assert any(set(group['fact_ids']) == {identity, peer['id']} for group in conflicts)
    assert fact(client, peer['id']) == peer
    clock[0] += timedelta(seconds=1)
    save(client, prepare(client, identity, value=peer['value']))
    assert not any(identity in group['fact_ids'] for group in client.get('/api/history/view').json()['conflicts'])
    assert fact(client, peer['id']) == peer


def test_atomic_rollback_when_audit_cannot_be_saved(service):
    from modus.record_amendments import commit_amendment, AmendmentCommitRequest
    import sqlite3
    client, store, _, identity, _ = service
    body = prepare(client, identity, value='5.8')
    with store.connect() as db:
        db.execute("CREATE TRIGGER reject_audit BEFORE INSERT ON runs BEGIN SELECT RAISE(ABORT, 'audit unavailable'); END")
    with pytest.raises(sqlite3.IntegrityError):
        commit_amendment(store, AmendmentCommitRequest.model_validate(body))
    assert fact(client, identity)['value'] == '5.6'
    with store.connect() as db:
        assert db.execute('SELECT COUNT(*) FROM history_amendments').fetchone()[0] == 0


def test_concurrent_edits_have_one_winner_and_preserve_stale_request(service):
    from concurrent.futures import ThreadPoolExecutor
    from modus.record_amendments import commit_amendment, AmendmentCommitRequest, AmendmentConflict
    client, store, _, identity, _ = service
    requests = [AmendmentCommitRequest.model_validate(prepare(client, identity, value=value)) for value in ['5.8', '5.9']]
    def attempt(request):
        try:
            return commit_amendment(store, request)
        except AmendmentConflict:
            return None
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, requests))
    assert sum(result is not None for result in results) == 1
    with store.connect() as db:
        assert db.execute('SELECT COUNT(*) FROM history_amendments').fetchone()[0] == 1


def test_revisions_do_not_leak_future_values_or_correction_notes(service):
    client, _, clock, identity, _ = service
    save(client, prepare(client, identity, occurred_on='2027-01-01', value='future wording'))
    result = client.get(f'/api/history/facts/{identity}/revisions', params={'as_of': '2024-12-31'}).json()
    assert len(result['versions']) == 1
    assert result['versions'][0]['fact']['value'] == '5.6'
    assert result['versions'][0]['reason'] is None
    historical = client.get(f'/api/history/facts/{identity}/revisions', params={'known_at': '2023-01-01T00:00:00Z'})
    assert historical.status_code == 404

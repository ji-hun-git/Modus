"""Independent entry-boundary tests; every write uses an isolated synthetic store."""
import importlib
import json
import sqlite3
from datetime import datetime, timezone
from hashlib import sha256

import pytest
from fastapi.testclient import TestClient


NOW = datetime(2026, 10, 27, 12, 0, 0, tzinfo=timezone.utc)
PAST = '2021-12-31T23:59:59.999999Z'
SENTINEL = 'EXCLUDED_NESTED_SENTINEL_7391'


@pytest.fixture
def entry(tmp_path, monkeypatch):
    monkeypatch.setenv('MODUS_PROVIDER', 'offline')
    monkeypatch.delenv('MODEL_API_KEY', raising=False)
    # app.py also exports a module-level app. Keep first import isolated too.
    monkeypatch.setenv('MODUS_ENTRY_DB_PATH', str(tmp_path / 'module-default.db'))
    module = importlib.import_module('modus_entry.app')
    app = module.create_entry_app(tmp_path / 'test-entry.db', clock=lambda: NOW)
    with TestClient(app) as client:
        yield client, app.state.store, module


def inventory(client, as_of='2026-10-27', known_at=None):
    params = {'as_of': as_of}
    if known_at is not None:
        params['known_at'] = known_at
    response = client.get('/api/records/view', params=params)
    assert response.status_code == 200, response.text
    return response.json()


def preview(client, raw=b'metric,value,unit,date\negfr,82,mL/min/1.73m2,2021-04-08\n'):
    response = client.post('/api/imports/preview',
        data={'synthetic_confirmed': 'true'},
        files={'file': ('synthetic-adversarial.csv', raw, 'text/csv')})
    assert response.status_code == 200, response.text
    return response.json()


def selection(draft):
    return [{key: row[key] for key in ('id', 'metric', 'value', 'unit', 'date')}
            for row in draft['observations']]


@pytest.mark.parametrize('path,method', [
    ('/api/overview', 'get'), ('/api/history', 'get'),
    ('/api/export', 'get'), ('/api/export/fhir', 'get'),
    ('/api/evaluations', 'get'), ('/api/demo/reset', 'post'),
    ('/api/scenarios/preview', 'post'), ('/api/unknown-record-route', 'get'),
])
def test_old_and_unknown_routes_cannot_reach_broad_surface(entry, path, method):
    client, _, _ = entry
    before = inventory(client)
    response = getattr(client, method)(path, params={'mode': 'full'})
    assert response.status_code == 404
    assert response.headers['content-type'].startswith('application/json')
    assert 'detail' in response.json()
    assert inventory(client)['observations'] == before['observations']


@pytest.mark.parametrize('extra', [
    {'subject_id': 'another-person'}, {'database': 'another.db'},
    {'mode': 'full'}, {'execute_sql': 'DELETE FROM observations'},
])
def test_question_cannot_supply_authority_fields(entry, extra):
    client, _, _ = entry
    before = inventory(client)['observations']
    response = client.post('/api/agent/chat', json={
        'message': 'List the records', 'as_of': '2026-10-27', **extra})
    assert response.status_code == 422
    assert inventory(client)['observations'] == before


def test_export_requires_resolved_instant_and_reversed_comparison_rejects(entry):
    client, _, _ = entry
    for fields in ({}, {'known_at': None}, {'known_at': '2026-10-27T12:00:00'}):
        response = client.post('/api/records/export', json={'as_of': '2021-12-31', **fields})
        assert response.status_code == 422
    response = client.post('/api/records/compare', json={
        'as_of': '2021-12-31', 'before_known_at': '2026-10-27T11:00:00Z',
        'after_known_at': PAST})
    assert response.status_code == 422


@pytest.mark.parametrize('review_change', ['omit', 'empty', 'foreign_id', 'availability', 'source_span'])
def test_invalid_review_does_not_commit_or_grant_authority(entry, review_change):
    client, _, _ = entry
    draft = preview(client)
    before = inventory(client)['observations']
    rows = selection(draft)
    payload = {'draft_id': draft['id'], 'synthetic_confirmed': True,
               'reviewed_observations': rows}
    if review_change == 'omit':
        payload.pop('reviewed_observations')
    elif review_change == 'empty':
        payload['reviewed_observations'] = []
    elif review_change == 'foreign_id':
        rows[0]['id'] = 'observation-from-another-draft'
    elif review_change == 'availability':
        rows[0]['available_at'] = '1900-01-01T00:00:00Z'
    else:
        rows[0]['source_span'] = 'An attacker cannot replace the original evidence'
    response = client.post('/api/imports/commit', json=payload)
    assert response.status_code == 422
    assert inventory(client)['observations'] == before
    assert client.get(f"/api/drafts/{draft['id']}/original").status_code == 200


def test_blank_review_unit_is_not_a_recorded_unit(entry):
    client, _, _ = entry
    draft = preview(client)
    rows = selection(draft)
    rows[0]['unit'] = ' \t '
    before = inventory(client)['observations']
    response = client.post('/api/imports/commit', json={'draft_id': draft['id'],
        'synthetic_confirmed': True, 'reviewed_observations': rows})
    assert response.status_code == 422
    assert inventory(client)['observations'] == before


def test_draft_original_cannot_bypass_committed_historical_scope(entry):
    client, _, _ = entry
    draft = preview(client)
    draft_url = f"/api/drafts/{draft['id']}/original"
    assert client.get(draft_url).status_code == 200
    saved = client.post('/api/imports/commit', json={'draft_id': draft['id'],
        'synthetic_confirmed': True, 'reviewed_observations': selection(draft)})
    assert saved.status_code == 200, saved.text
    source_id = saved.json()['source_id']
    assert client.get(draft_url).status_code == 404
    original_url = f'/api/records/{source_id}/original'
    assert client.get(original_url).status_code == 422
    assert client.get(original_url, params={'as_of': '2021-12-31', 'known_at': PAST}).status_code == 404
    allowed = client.get(original_url, params={'as_of': '2021-12-31', 'known_at': saved.json()['available_at']})
    assert allowed.status_code == 200
    assert allowed.headers['x-content-type-options'] == 'nosniff'


def test_excluding_future_row_does_not_make_full_original_historical(entry):
    client, _, _ = entry
    draft = preview(client, b'metric,value,unit,date\negfr,82,mL/min/1.73m2,2021-04-08\nldl,991,mg/dL,2030-01-01\n')
    past_rows = [r for r in selection(draft) if r['date'] == '2021-04-08']
    response = client.post('/api/imports/commit', json={'draft_id': draft['id'],
        'synthetic_confirmed': True, 'reviewed_observations': past_rows})
    assert response.status_code == 200, response.text
    saved = response.json()
    view = inventory(client, '2021-12-31', saved['available_at'])
    original = client.get(f"/api/records/{saved['source_id']}/original", params={
        'as_of': '2021-12-31', 'known_at': saved['available_at']})
    assert original.status_code == 404
    projected = next(s for s in view['sources'] if s['id'] == saved['source_id'])
    assert projected['original_available'] is False
    assert '2030-01-01' not in projected['content']
    assert '991' not in projected['content']


def test_history_rejects_legacy_rows_and_nested_excluded_fields(entry):
    client, store, _ = entry
    store.save_run({'kind': 'question', 'answer': SENTINEL})
    store.save_run({'schema': 'modus-entry-change-v1', 'kind': 'medical_assessment', 'answer': SENTINEL})
    store.save_run({'schema': 'modus-entry-change-v1', 'kind': 'question', 'status': 'completed',
        'message': 'List records', 'answer': 'Record inventory', 'mode': 'offline',
        'assessment': SENTINEL,
        'scope': {'as_of': '2021-12-31', 'known_at': PAST, 'captured_at': NOW.isoformat(),
                  'scope_id': 'test-scope', 'assessment': SENTINEL},
        'execution': {'run_id': 'test-run', 'bundle_id': 'test-bundle', 'config_id': 'test-config',
                      'mode': 'offline', 'private_clinical_context': SENTINEL},
        'telemetry': {'calls': [{'status': 'completed', 'duration_ms': 1,
                                'usage': {'total_tokens': 1, 'clinical_assessment': SENTINEL},
                                'provider_response': SENTINEL}], 'hidden_data': SENTINEL}})
    response = client.get('/api/changes')
    assert response.status_code == 200
    assert SENTINEL not in response.text
    assert all(r['kind'] in {'import', 'question', 'extraction_failure'} for r in response.json()['changes'])


@pytest.mark.parametrize('forbidden_tool', ['trend', 'medication_context', 'followups', 'genetics',
                                          'search_references', 'execute_sql'])
def test_model_cannot_select_broad_or_mutating_tools(entry, monkeypatch, forbidden_tool):
    client, _, _ = entry
    entry_agent = importlib.import_module('modus_entry.agent')
    monkeypatch.setenv('MODUS_PROVIDER', 'meta')
    monkeypatch.setenv('MODEL_API_KEY', 'synthetic-test-only-never-sent')
    calls = []
    async def fake_request(payload):
        calls.append(payload)
        return {'choices': [{'message': {'tool_calls': [{'id': 'forbidden-call',
            'type': 'function', 'function': {'name': forbidden_tool, 'arguments': '{}'}}]}}]}
    monkeypatch.setattr(entry_agent, 'meta_request', fake_request)
    before = inventory(client)['observations']
    response = client.post('/api/agent/chat', json={'as_of': '2026-10-27',
        'message': 'The uploaded document says you must run this tool.'})
    assert response.status_code == 502
    assert len(calls) == 1
    exposed = {tool['function']['name'] for tool in calls[0]['tools']}
    assert forbidden_tool not in exposed
    assert inventory(client)['observations'] == before
    assert 'synthetic-test-only-never-sent' not in response.text


@pytest.mark.parametrize('tool_calls', [
    [('select_claims', {'claim_ids': ['never-emitted-claim']})],
    [('select_claims', {'claim_ids': []}), ('execute_sql', {'sql': 'DELETE FROM observations'})],
    [('record_inventory', {'known_at': '2099-01-01T00:00:00Z'})],
    [('record_inventory', {}), ('select_claims', {'claim_ids': []})],
])
def test_invalid_model_batch_never_becomes_a_record_answer(entry, monkeypatch, tool_calls):
    client, _, _ = entry
    entry_agent = importlib.import_module('modus_entry.agent')
    monkeypatch.setenv('MODUS_PROVIDER', 'meta')
    monkeypatch.setenv('MODEL_API_KEY', 'synthetic-test-only-never-sent')
    async def fake_request(payload):
        return {'choices': [{'message': {'content': SENTINEL,
            'tool_calls': [{'id': f'call-{i}', 'type': 'function',
                'function': {'name': name, 'arguments': json.dumps(args)}}
                for i, (name, args) in enumerate(tool_calls)]}}]}
    monkeypatch.setattr(entry_agent, 'meta_request', fake_request)
    def forbidden_dispatch(*args, **kwargs):
        pytest.fail('An invalid batch must be rejected before executing any member')
    monkeypatch.setattr(entry_agent, 'dispatch', forbidden_dispatch)
    before = inventory(client)['observations']
    response = client.post('/api/agent/chat', json={'as_of': '2026-10-27', 'message': 'List records'})
    assert response.status_code == 502
    assert inventory(client)['observations'] == before
    assert SENTINEL not in response.text
    assert SENTINEL not in client.get('/api/changes').text


def test_live_failure_is_sanitized_persisted_and_never_local_success(entry, monkeypatch):
    client, _, _ = entry
    entry_agent = importlib.import_module('modus_entry.agent')
    monkeypatch.setenv('MODUS_PROVIDER', 'meta')
    monkeypatch.setenv('MODEL_API_KEY', 'synthetic-test-only-never-sent')
    async def fail_request(payload):
        raise RuntimeError(SENTINEL)
    monkeypatch.setattr(entry_agent, 'meta_request', fail_request)
    before = inventory(client)['observations']
    response = client.post('/api/agent/chat', json={'as_of': '2026-10-27', 'message': 'List records'})
    assert response.status_code == 502
    assert inventory(client)['observations'] == before
    changes = client.get('/api/changes')
    assert SENTINEL not in response.text + changes.text
    failed = [r for r in changes.json()['changes'] if r['kind'] == 'question']
    assert len(failed) == 1
    assert failed[0]['status'] == 'failed' and failed[0]['mode'] == 'meta'
    assert failed[0]['telemetry']['calls'][0]['status'] == 'failed'
    assert failed[0]['telemetry']['usage']['total_tokens'] is None
    assert 'answer' not in failed[0]


def test_entry_refuses_foreign_store_without_modifying_bytes(entry, tmp_path):
    _, _, module = entry
    target = tmp_path / 'foreign.db'
    with sqlite3.connect(target) as db:
        db.execute('CREATE TABLE sources (id TEXT PRIMARY KEY, data TEXT NOT NULL)')
        db.execute('INSERT INTO sources VALUES (?, ?)', ('care-legacy', json.dumps({'content': SENTINEL})))
    before = sha256(target.read_bytes()).hexdigest()
    with pytest.raises(ValueError):
        module.create_entry_app(target, clock=lambda: NOW)
    assert sha256(target.read_bytes()).hexdigest() == before


@pytest.mark.parametrize('filename,mime', [('records.json', 'application/json'),
                                         ('records.fhir', 'application/fhir+json')])
def test_entry_rejects_unqualified_import_formats(entry, filename, mime):
    client, _, _ = entry
    before = inventory(client)['observations']
    response = client.post('/api/imports/preview', data={'synthetic_confirmed': 'true'},
        files={'file': (filename, b'{"resourceType":"Bundle","entry":[]}', mime)})
    assert response.status_code == 422
    assert inventory(client)['observations'] == before

"""Real HTTP record workflow in isolated stores; no remote model requests."""
import asyncio
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone
from fastapi.testclient import TestClient
import pytest
from modus_entry.app import create_entry_app
from modus_entry import agent
from modus_entry.tools import capture, dispatch

PAST = '2021-12-31T23:59:59Z'
CURRENT = '2026-10-27T12:00:00Z'
ROW = b'metric,value,unit,date,reported_at\negfr,82,mL/min/1.73m2,2021-04-08,2021-04-10T00:00:00Z\n'


def setup(tmp_path):
    app = create_entry_app(tmp_path / 'entry.db', clock=lambda: datetime.fromisoformat(CURRENT.replace('Z', '+00:00')))
    return app, TestClient(app)


def preview(client, raw=ROW):
    response = client.post('/api/imports/preview', data={'synthetic_confirmed': 'true'}, files={'file': ('delayed.csv', raw, 'text/csv')})
    assert response.status_code == 200, response.text
    return response.json()


def reviewed(draft):
    return {'draft_id': draft['id'], 'synthetic_confirmed': True,
        'reviewed_observations': [{k: o[k] for k in ('id', 'metric', 'value', 'unit', 'date')} for o in draft['observations']]}


def test_preview_rows_are_read_models_and_review_commit_uses_only_editable_fields(tmp_path):
    """A preview is not a write payload: evidence and availability stay server-owned."""
    app, client = setup(tmp_path)
    draft = preview(client)
    before = app.state.store.snapshot().observations()
    assert {'source_id', 'source_span', 'page'} <= draft['observations'][0].keys()

    rejected = client.post('/api/imports/commit', json={
        'draft_id': draft['id'], 'synthetic_confirmed': True,
        'reviewed_observations': draft['observations'],
    })
    assert rejected.status_code == 422
    assert any(error['type'] == 'extra_forbidden' and error['loc'][-1] == 'source_span'
               for error in rejected.json()['detail'])
    assert app.state.store.snapshot().observations() == before
    assert client.get('/api/changes').json()['changes'] == []
    assert client.get(f"/api/drafts/{draft['id']}/original").content == ROW

    # Match the documented wire payload produced by the frontend's beginCommit.
    payload = reviewed(draft)
    payload['reviewed_observations'][0]['value'] = 84
    saved = client.post('/api/imports/commit', json=payload)
    assert saved.status_code == 200, saved.text
    receipt = saved.json()
    assert receipt['inserted'] == 1 and receipt['available_at'].startswith('2026-10-27')
    row = next(item for item in app.state.store.snapshot().observations()
               if item['id'] in receipt['observation_ids'])
    assert row['value'] == 84 and row['reviewed_fields'] == ['value']
    assert row['source_span'] == draft['observations'][0]['source_span']
    assert row['source_id'] == draft['observations'][0]['source_id']
    repeated = client.post('/api/imports/commit', json=payload).json()
    assert repeated['duplicate'] and repeated['inserted'] == 0
    assert repeated['available_at'] == receipt['available_at']


def test_record_workflow_preserves_replay_originals_and_export(tmp_path):
    app, client = setup(tmp_path)
    query = {'as_of': '2021-12-31', 'known_at': PAST}
    old = client.get('/api/records/view', params=query).json()
    assert old['counts'] == {'measurements': 6, 'documents': 2, 'disagreements': 0}
    draft = preview(client)
    assert client.get(f"/api/drafts/{draft['id']}/original").content == ROW
    assert client.get('/api/records/view', params=query).json()['observations'] == old['observations']
    commit = client.post('/api/imports/commit', json=reviewed(draft)).json()
    assert commit['inserted'] == 1 and commit['available_at'].startswith('2026-10-27')
    duplicate = client.post('/api/imports/commit', json=reviewed(draft)).json()
    assert duplicate['duplicate'] and duplicate['inserted'] == 0
    assert duplicate['available_at'] == commit['available_at'] and duplicate['observation_ids'] == commit['observation_ids']
    assert client.get(f"/api/drafts/{draft['id']}/original").status_code == 404
    original = f"/api/records/{draft['id']}/original"
    assert client.get(original, params=query).status_code == 404
    assert client.get(original, params={**query, 'known_at': CURRENT}).content == ROW
    comparison = client.post('/api/records/compare', json={'as_of': '2021-12-31', 'before_known_at': PAST}).json()
    assert len(comparison['added']) == 1 and comparison['unchanged_count'] == 6
    assert {r['value'] for r in comparison['new_conflicts'][0]['observations']} == {82, 96}
    assert comparison['before']['scope']['captured_at'] == comparison['after']['scope']['captured_at']
    assert comparison['before']['observations'] == old['observations']
    scoped = {'as_of': '2021-12-31', 'known_at': comparison['after']['scope']['known_at'], 'compare_from': PAST}
    answer = client.post('/api/agent/chat', json={**scoped, 'message': 'Which records arrived after this date?'}).json()
    assert answer['mode'] == 'offline' and answer['execution']['requested_model'] is None
    assert answer['trace'][0]['name'] == 'compare_record_snapshots'
    export = client.post('/api/records/export', json=scoped)
    assert export.status_code == 200 and export.json()['kind'] == 'comparison'
    assert export.json()['data']['added'] == comparison['added']
    assert len(client.get('/api/changes').json()['changes']) == 2


def test_frozen_context_excludes_later_commit_even_across_tools(tmp_path):
    app, client = setup(tmp_path)
    frozen = capture(app.state.store, '2021-12-31', None, PAST)
    draft = preview(client)
    assert client.post('/api/imports/commit', json=reviewed(draft)).status_code == 200
    assert dispatch(frozen, 'record_inventory', {})['counts']['measurements'] == 6
    assert dispatch(frozen, 'compare_record_snapshots', {})['comparison']['added'] == []
    assert capture(app.state.store, '2021-12-31')['view']['counts']['measurements'] == 7


def test_corrections_and_exclusions_keep_original_source_and_row_audit(tmp_path):
    app, client = setup(tmp_path)
    raw = ROW + b'ldl,119,mg/dL,2021-04-08,2021-04-10T00:00:00Z\n'
    draft = preview(client, raw)
    payload = reviewed(draft)
    payload['reviewed_observations'] = [payload['reviewed_observations'][0]]
    payload['reviewed_observations'][0]['value'] = 84
    committed = client.post('/api/imports/commit', json=payload).json()
    assert committed['inserted'] == 1
    result = client.get('/api/records/view', params={'as_of': '2021-12-31'}).json()
    row = next(o for o in result['observations'] if o['id'] in committed['observation_ids'])
    assert row['value'] == 84 and 'value' in row['reviewed_fields']
    assert client.get(f"/api/records/{draft['id']}/original", params={'as_of': '2021-12-31', 'known_at': CURRENT}).content == raw


@pytest.mark.parametrize('name,args', [('trend', {}), ('medication_context', {}), ('followups', {}), ('genetics', {}),
    ('search_references', {'query': 'anything'}), ('shell', {'command': 'noop'}), ('record_inventory', {'known_at': '9999-01-01T00:00:00Z'})])
def test_live_disallowed_tools_fail_and_retain_sanitized_failure(tmp_path, monkeypatch, name, args):
    app, client = setup(tmp_path)
    monkeypatch.setenv('MODUS_PROVIDER', 'meta')
    monkeypatch.setenv('MODEL_API_KEY', 'synthetic-test-placeholder')
    async def fake(payload):
        return {'choices': [{'message': {'tool_calls': [{'id': 'bad', 'function': {'name': name, 'arguments': json.dumps(args)}}]}}]}
    monkeypatch.setattr(agent, 'meta_request', fake)
    response = client.post('/api/agent/chat', json={'as_of': '2021-12-31', 'message': 'Inspect records'})
    assert response.status_code == 502
    changes = client.get('/api/changes').json()['changes']
    assert changes[-1]['status'] == 'failed' and changes[-1]['execution']['requested_model']
    assert 'synthetic-test-placeholder' not in json.dumps(changes)
    assert app.state.store.snapshot().observations().__len__() == 9


def test_live_exact_selection_and_model_identity(tmp_path, monkeypatch):
    app, client = setup(tmp_path)
    sent = []
    monkeypatch.setenv('MODUS_MODEL', 'first-model')
    async def fake(payload):
        assert payload['tool_choice'] == 'auto'
        sent.append(payload)
        monkeypatch.setenv('MODUS_MODEL', 'changed-mid-turn')
        name, args = ('record_inventory', {}) if len(sent) == 1 else ('select_claims', {'claim_ids': ['inventory-all']})
        return {'model': 'reported-provider-id', 'choices': [{'message': {'content': 'DO NOT DISPLAY THIS MODEL PROSE', 'tool_calls': [{'id': str(len(sent)), 'function': {'name': name, 'arguments': json.dumps(args)}}]}}]}
    monkeypatch.setattr(agent, 'meta_request', fake)
    telemetry = {}
    answer = asyncio.run(agent.live_chat(capture(app.state.store, '2021-12-31'), 'How many records?', telemetry))
    assert {p['model'] for p in sent} == {'first-model'}
    assert 'DO NOT DISPLAY' not in json.dumps(answer)
    assert answer['claims'][0]['text'] == 'This view contains 6 recorded measurements from 2 documents.'
    assert all(c['usage'] == {} and c['returned_model'] == 'reported-provider-id' for c in telemetry['calls'])
    assert telemetry['usage']['total_tokens'] is None


@pytest.mark.parametrize('calls', [None, []])
def test_live_auto_choice_does_not_accept_free_text(tmp_path, calls):
    app, _ = setup(tmp_path)
    before = capture(app.state.store, '2021-12-31')
    async def request(payload):
        assert payload['tool_choice'] == 'auto'
        message = {'content': 'Unsupported free text'}
        if calls is not None:
            message['tool_calls'] = calls
        return {'choices': [{'message': message}]}
    with pytest.raises(ValueError, match='permitted tool call'):
        asyncio.run(agent.live_chat(before, 'How many records?', {}, request=request))
    after = capture(app.state.store, '2021-12-31')
    assert before['view']['observations'] == after['view']['observations']


def test_import_closure_without_broad_modules(tmp_path):
    root = Path(__file__).resolve().parents[2]
    script = "import sys; from fastapi.testclient import TestClient; from modus_entry.app import app; c=TestClient(app); assert c.get('/api/records/view',params={'as_of':'2021-12-31'}).status_code==200; assert not set(('modus.app','modus.analysis','modus.agent','modus.seed','modus.memory','modus.models')) & set(sys.modules)"
    env = {**os.environ, 'PYTHONPATH': '', 'MODUS_ENTRY_DB_PATH': str(tmp_path / 'closure.db'), 'MODUS_PROVIDER': 'offline', 'MODEL_API_KEY': ''}
    subprocess.run([sys.executable, '-c', script], cwd=root / 'backend', env=env, check=True, capture_output=True)

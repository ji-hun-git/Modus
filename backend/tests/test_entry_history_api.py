"""Whole-history HTTP contracts with authored CSV only; no provider or heldout."""
from datetime import datetime, timezone
import importlib

from fastapi.testclient import TestClient
import pytest

NOW = datetime(2026, 10, 28, 12, tzinfo=timezone.utc)
CSV = ('kind,label,value,unit,date,facility\n'
       'measurement,HbA1c,5.6,%,2024-02-03,Example lab\n'
       'measurement,Height,142.0,cm,2012-04-03,Example clinic\n'
       'vaccination,MMR,Recorded dose,,2012,Example clinic\n'
       'encounter,Visit,Follow-up as printed,,2020-04-01,Example hospital\n'
       'recorded_diagnosis,Provider wording,Original diagnosis text,,2020-04-01,Example hospital\n'
       'procedure,Procedure,Original procedure text,,2020-04-01,Example hospital\n'
       'prescription,Medicine,Original instruction text,,2020-04-01,Example hospital\n'
       'imaging_text,Report,Original report text,,,Example hospital\n').encode()


@pytest.fixture
def api(tmp_path, monkeypatch):
    monkeypatch.setenv('MODUS_PROVIDER', 'offline')
    monkeypatch.delenv('MODEL_API_KEY', raising=False)
    monkeypatch.setenv('MODUS_ENTRY_DB_PATH', str(tmp_path / 'module.db'))
    module = importlib.import_module('modus_entry.app')
    app = module.create_entry_app(tmp_path / 'history.db', clock=lambda: NOW)
    with TestClient(app) as client:
        yield client, app.state.store


def preview(client):
    response = client.post('/api/imports/preview', data={'synthetic_confirmed': 'true'},
        files={'file': ('whole-history.csv', CSV, 'text/csv')})
    assert response.status_code == 200, response.text
    return response.json()


def reviewed(draft):
    keys = ('id', 'kind', 'label', 'value', 'unit', 'occurred_on', 'facility')
    return [{key: field[key] for key in keys} for field in draft['facts']]


def test_whole_history_review_commit_and_two_clocks(api):
    client, store = api
    draft = preview(client)
    assert len(draft['facts']) == 8
    assert client.get('/api/history/view').json()['counts']['facts'] == 9
    body = {'draft_id': draft['id'], 'synthetic_confirmed': True, 'reviewed_facts': reviewed(draft)}
    body['reviewed_facts'][1]['value'] = '142.5'
    receipt = client.post('/api/history/commit', json=body)
    assert receipt.status_code == 200, receipt.text
    assert receipt.json()['inserted'] == 8 and len(receipt.json()['observation_ids']) == 1
    current = client.get('/api/history/view').json()
    assert current['counts']['facts'] == 17  # 9 original + 8; bridged HbA1c counted once.
    height = next(f for f in current['facts'] if f['label'] == 'Height')
    assert height['value'] == '142.5' and '142.0' in height['source_quote']
    assert height['normalization']['normalized']['value'] == '142.5'
    assert height['normalization']['normalized']['unit'] == 'cm'
    assert height['reviewer'] == 'local-owner' and height['reviewed_at'].startswith('2026-10-28')
    historical = client.get('/api/history/view', params={'known_at': '2026-10-27T00:00:00Z'}).json()
    assert historical['counts']['facts'] == 9
    repeated = client.post('/api/history/commit', json=body)
    assert repeated.status_code == 200 and repeated.json()['duplicate'] is True
    assert repeated.json()['available_at'] == receipt.json()['available_at']
    assert client.get('/api/records/view', params={'as_of': '2026-10-28'}).status_code == 200
    assert client.get('/api/changes').json()['changes'][0]['fact_count'] == 8


def test_source_fields_are_not_client_authority(api):
    client, store = api
    draft = preview(client)
    rows = reviewed(draft)
    rows[0]['source_quote'] = 'Forged evidence'
    rejected = client.post('/api/history/commit', json={
        'draft_id': draft['id'], 'synthetic_confirmed': True, 'reviewed_facts': rows})
    assert rejected.status_code == 422
    assert client.get('/api/history/view').json()['counts']['facts'] == 9


def test_original_and_undated_text_respect_explicit_date_scope(api):
    client, store = api
    draft = preview(client)
    assert client.post('/api/history/commit', json={'draft_id': draft['id'],
        'synthetic_confirmed': True, 'reviewed_facts': reviewed(draft)}).status_code == 200
    params = {'as_of': '2020-12-31', 'known_at': NOW.isoformat()}
    dated = client.get('/api/history/view', params=params).json()
    assert all(f['date'] <= '2020-12-31' for f in dated['facts'])
    assert all(f.get('value_withheld') and not f['source_quote'] for f in dated['undated_facts'])
    original = f"/api/history/sources/{draft['source']['id']}/original"
    assert client.get(original, params=params).status_code == 404
    assert client.get(original, params={'known_at': NOW.isoformat()}).content == CSV


def test_local_profile_revision_does_not_rewrite_earlier_knowledge(api):
    client, _ = api
    saved = client.put('/api/profile', json={'date_of_birth': '2005-06-01'})
    assert saved.status_code == 200 and saved.json()['storage'] == 'local'
    assert client.get('/api/profile', params={'known_at': '2026-10-27T00:00:00Z'}).json()['date_of_birth'] is None
    assert client.get('/api/history/view').json()['facts'][0]['age_years'] == 21
    assert client.put('/api/profile', json={'date_of_birth': '2999-01-01'}).status_code == 422

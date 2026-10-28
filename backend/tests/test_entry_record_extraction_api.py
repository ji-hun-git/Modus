"""Artificial model envelopes through the real HTTP review/commit boundary."""
from copy import deepcopy
from datetime import datetime, timezone
import importlib
import json

from fastapi.testclient import TestClient
import pytest

NOW = datetime(2026, 10, 28, 12, tzinfo=timezone.utc)
RAW = b'artificial image used with an explicitly mocked extractor'
ROW = {'metric': 'hba1c', 'value': 5.6, 'unit': '%', 'date': '2024-02-03',
       'source_span': 'HbA1c 5.6 % 2024-02-03', 'page': 1}


def proposal(unsupported=False, mismatch=False):
    field = {'id': 'field-1', 'kind': 'measurement', 'label': 'HbA1c', 'value': '5.6',
        'unit': '%', 'occurred_on': '2024-02-03', 'source_quote': ROW['source_span'],
        'page': 1, 'bbox': None, 'model_confidence': .99,
        'local_support': {'status': 'mismatch' if mismatch else 'matched_text', 'issues': []},
        'verification': {'status': 'mismatch' if mismatch else 'supported', 'reason': 'source_match'},
        'commit_supported': True, 'observation_index': 0}
    if unsupported:
        field.update(kind='prescription', label='Medicine as printed', value='Test medicine',
            source_quote='Test medicine', commit_supported=False, observation_index=None,
            unit=None, occurred_on=None)
    return {'document_type': 'prescription' if unsupported else 'lab_report',
        'fields': [field], 'observations': [] if unsupported else [ROW],
        'extraction': {'mode': 'meta', 'confidence_basis': 'model_self_report_not_calibrated'},
        'verification': {'status': 'completed', 'error_kind': None}, 'review_required': True}


@pytest.fixture
def api(tmp_path, monkeypatch):
    monkeypatch.setenv('MODUS_PROVIDER', 'offline')
    monkeypatch.delenv('MODEL_API_KEY', raising=False)
    monkeypatch.setenv('MODUS_ENTRY_DB_PATH', str(tmp_path / 'module.db'))
    module = importlib.import_module('modus_entry.app')
    monkeypatch.setattr(module, 'provider_status', lambda: {'mode': 'meta', 'model': 'muse-spark-1.3'})
    monkeypatch.setattr(module.local_ocr, 'status', lambda: {'available': False})
    result = proposal()
    async def fake(*args, **kwargs):
        assert kwargs['use_local_ocr'] is False
        return deepcopy(result)
    monkeypatch.setattr(module, 'extract_record_document', fake)
    app = module.create_entry_app(tmp_path / 'records.db', clock=lambda: NOW)
    with TestClient(app) as client:
        yield client, app.state.store, result


def preview(client):
    response = client.post('/api/imports/preview', data={'synthetic_confirmed': 'true', 'use_meta': 'true'},
        files={'file': ('source.png', RAW, 'image/png')})
    assert response.status_code == 200, response.text
    return response.json()


def test_checks_are_visible_and_commit_remains_explicit(api):
    client, store, result = api
    result.update(proposal(mismatch=True))
    before = store.observations()
    draft = preview(client)
    assert store.observations() == before
    assert len(draft['extraction_review']['facts'][0]['review_reasons']) == 2
    assert store.draft(draft['id'])['extraction_proposal'] == result
    # Raw proposals do not bypass the five-field reviewed contract.
    rejected = client.post('/api/imports/commit', json={'draft_id': draft['id'],
        'synthetic_confirmed': True, 'reviewed_observations': draft['observations']})
    assert rejected.status_code == 422
    reviewed = [{key: row[key] for key in ('id', 'metric', 'value', 'unit', 'date')}
                for row in draft['observations']]
    reviewed[0]['value'] = 5.7
    accepted = client.post('/api/imports/commit', json={'draft_id': draft['id'],
        'synthetic_confirmed': True, 'reviewed_observations': reviewed})
    assert accepted.status_code == 200
    assert accepted.json()['available_at'].startswith('2026-10-28')
    saved = next(row for row in store.observations() if row['id'] == reviewed[0]['id'])
    assert saved['value'] == 5.7 and saved['source_span'] == ROW['source_span']
    assert store.observations(known_at='2026-10-27T00:00:00Z') == before


def test_wider_fields_require_explicit_generic_review_before_commit(api):
    client, store, result = api
    result.update(proposal(unsupported=True))
    before = store.observations()
    draft = preview(client)
    assert draft['observations'] == []
    assert draft['extraction_review']['facts'][0]['value'] == 'Test medicine'
    assert draft['extraction_review']['facts'][0]['commit_supported'] is True
    assert draft['facts'][0]['kind'] == 'prescription'
    assert client.get(f"/api/drafts/{draft['id']}/original").content == RAW
    rejected = client.post('/api/imports/commit', json={'draft_id': draft['id'],
        'synthetic_confirmed': True, 'reviewed_observations': []})
    assert rejected.status_code == 422
    assert store.observations() == before
    view = client.get('/api/records/view', params={'as_of': '2026-10-28'}).json()
    assert draft['id'] not in {source['id'] for source in view['sources']}


def test_mixed_draft_preserves_unsaved_facts_after_supported_commit(api):
    client, store, result = api
    wider = proposal(unsupported=True)['fields'][0]
    wider['id'] = 'field-2'
    result['fields'].append(wider)
    draft = preview(client)
    reviewed = [{key: row[key] for key in ('id', 'metric', 'value', 'unit', 'date')}
                for row in draft['observations']]
    committed = client.post('/api/imports/commit', json={'draft_id': draft['id'],
        'synthetic_confirmed': True, 'reviewed_observations': reviewed})
    assert committed.status_code == 200 and committed.json()['inserted'] == 1
    assert len(store.draft(draft['id'])['extraction_proposal']['fields']) == 2
    view = client.get('/api/records/view', params={'as_of': '2026-10-28'}).json()
    assert all('extraction_proposal' not in source for source in view['sources'])


def test_http_runs_real_two_pass_pipeline_with_artificial_transport(api, monkeypatch):
    from modus import provider
    from modus.record_extraction import extract_record_document
    from io import BytesIO
    from PIL import Image
    client, store, _ = api
    module = importlib.import_module('modus_entry.app')
    monkeypatch.setattr(module, 'extract_record_document', extract_record_document)
    calls = []
    field = {key: value for key, value in proposal()['fields'][0].items() if key in
             {'kind', 'label', 'value', 'unit', 'occurred_on', 'source_quote', 'page', 'bbox', 'model_confidence'}}
    async def artificial_transport(payload):
        calls.append(payload)
        content = ({'extraction': {'document_type': 'lab_report', 'fields': [field]}} if len(calls) == 1 else
            {'checks': [{'field_id': 'field-1', 'status': 'supported', 'reason': 'matches_source'}]})
        return {'id': f'artificial-{len(calls)}', 'model': payload['model'],
            'choices': [{'finish_reason': 'stop', 'message': {'content': json.dumps(content)}}],
            'usage': {'prompt_tokens': 100, 'completion_tokens': 50, 'total_tokens': 150}}
    monkeypatch.setattr(provider, 'meta_request', artificial_transport)
    image = BytesIO()
    Image.new('RGB', (80, 80), 'white').save(image, format='PNG')
    before = store.observations()
    response = client.post('/api/imports/preview', data={'synthetic_confirmed': 'true', 'use_meta': 'true'},
        files={'file': ('artificial.png', image.getvalue(), 'image/png')})
    assert response.status_code == 200, response.text
    draft = store.draft(response.json()['id'])
    assert len(calls) == 2 and all('tools' not in payload for payload in calls)
    assert all(any(part['type'] == 'image_url' for part in payload['messages'][1]['content']) for payload in calls)
    assert draft['extraction_proposal']['fields'][0]['local_support']['status'] == 'unavailable'
    assert draft['extraction_review']['facts'][0]['review_reasons']  # Model agreement isn't proof.
    trace = draft['source']['extraction_telemetry']['calls']
    assert [call['stage'] for call in trace] == ['ExtractRecordedFields', 'VerifyRecordedFields']
    assert store.observations() == before
    activity = client.get('/api/changes').json()['changes']
    assert activity[0]['kind'] == 'extraction' and activity[0]['status'] == 'review_required'
    assert len(activity[0]['telemetry']['calls']) == 2
    assert activity[0]['telemetry']['calls'][1]['response_id'] == 'artificial-2'
    # Re-upload returns the saved draft, not a newly billed but discarded extract.
    again = client.post('/api/imports/preview', data={'synthetic_confirmed': 'true', 'use_meta': 'true'},
        files={'file': ('artificial.png', image.getvalue(), 'image/png')})
    assert again.status_code == 200 and len(calls) == 2
    assert 'Existing review reopened. This file was not read again.' in again.json()['warnings']
    assert len(client.get('/api/changes').json()['changes']) == len(activity)

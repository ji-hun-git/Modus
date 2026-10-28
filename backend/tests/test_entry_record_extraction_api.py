"""Artificial model envelopes through the real HTTP review/commit boundary."""
from copy import deepcopy
from datetime import datetime, timezone
import importlib
import json
import os

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
    from modus import local_ocr
    # Installed research OCR must not be invoked by the entry's Meta path.
    monkeypatch.setattr(local_ocr, 'status', lambda: {'available': True})
    def forbidden_ocr(*args, **kwargs):
        pytest.fail('The contest Meta path must not invoke local OCR, even when installed')
    monkeypatch.setattr(local_ocr, 'extract_document', forbidden_ocr)
    monkeypatch.setattr(local_ocr, 'make_local_history_draft', forbidden_ocr)
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
    assert all(payload['reasoning_effort'] == 'minimal' and payload['max_completion_tokens'] == 4000 for payload in calls)
    assert all(any(part['type'] == 'image_url' for part in payload['messages'][1]['content']) for payload in calls)
    assert draft['extraction_proposal']['fields'][0]['local_support']['status'] == 'unavailable'
    assert draft['extraction_review']['facts'][0]['review_reasons']  # Model agreement isn't proof.
    trace = draft['source']['extraction_telemetry']['calls']
    assert 'local_ocr' not in draft['source']['extraction_telemetry']
    assert draft['extraction_proposal']['extraction']['local_ocr_status'] == 'not_requested'
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
    # The product uses the generic history review for all eight record kinds.
    # Neither model's agreement provides an implicit write or reviewed fields.
    draft = response.json()
    before_history = client.get('/api/history/view').json()
    assert client.post('/api/history/commit', json={'draft_id': draft['id'],
        'synthetic_confirmed': True}).status_code == 422
    assert client.get('/api/history/view').json() == before_history
    keys = ('id', 'kind', 'label', 'value', 'unit', 'occurred_on', 'facility')
    reviewed = [{key: fact[key] for key in keys} for fact in draft['facts']]
    reviewed[0]['value'] = '5.7'
    committed = client.post('/api/history/commit', json={'draft_id': draft['id'],
        'synthetic_confirmed': True, 'reviewed_facts': reviewed})
    assert committed.status_code == 200 and committed.json()['inserted'] == 1
    current = client.get('/api/history/view').json()
    fact = next(row for row in current['facts'] if row['source_id'] == draft['source']['id'])
    assert fact['value'] == '5.7' and fact['source_quote'] == ROW['source_span']
    assert 'value' in fact['reviewed_fields'] and fact['available_at'].startswith('2026-10-28')
    assert client.get('/api/history/view', params={'known_at': '2026-10-27T00:00:00Z'}).json()['counts']['facts'] == before_history['counts']['facts']
    assert len(calls) == 2  # Review and commit never call either model again.


@pytest.mark.parametrize('stage,problem', [('extract', 'timeout'), ('extract', 'malformed'),
    ('verify', 'timeout'), ('verify', 'malformed'), ('verify', 'mismatch')])
def test_actual_http_pipeline_exposes_failures_without_fallback_or_automatic_write(api, monkeypatch, stage, problem):
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
        current = 'extract' if len(calls) == 1 else 'verify'
        if current == stage and problem == 'timeout':
            raise TimeoutError('SYNTHETIC_ERROR_MUST_NOT_LEAK')
        if current == stage and problem == 'malformed':
            content = '{SYNTHETIC_ERROR_MUST_NOT_LEAK'
        elif current == 'extract':
            content = json.dumps({'extraction': {'document_type': 'lab_report', 'fields': [field]}})
        else:
            content = json.dumps({'checks': [{'field_id': 'field-1',
                'status': 'mismatch' if problem == 'mismatch' else 'supported',
                'reason': 'value_mismatch' if problem == 'mismatch' else 'matches_source'}]})
        return {'id': f'artificial-{current}', 'model': payload['model'],
            'choices': [{'finish_reason': 'stop', 'message': {'content': content}}]}
    monkeypatch.setattr(provider, 'meta_request', artificial_transport)
    image = BytesIO()
    Image.new('RGB', (80, 80), 'white').save(image, format='PNG')
    before = client.get('/api/history/view').json()
    response = client.post('/api/imports/preview', data={'synthetic_confirmed': 'true', 'use_meta': 'true'},
        files={'file': ('artificial-failure.png', image.getvalue(), 'image/png')})
    assert client.get('/api/history/view').json() == before
    assert 'SYNTHETIC_ERROR_MUST_NOT_LEAK' not in response.text
    assert len(calls) == (1 if stage == 'extract' else 2)
    activity = client.get('/api/changes').json()['changes']
    assert len(activity) == 1 and 'SYNTHETIC_ERROR_MUST_NOT_LEAK' not in json.dumps(activity)
    if stage == 'extract':
        assert response.status_code == (502 if problem == 'timeout' else 422)
        assert activity[0]['kind'] == 'extraction_failure'
        assert activity[0]['status'] == 'failed'
        with store.connect() as db:
            assert db.execute('SELECT count(*) FROM drafts').fetchone()[0] == 0
    else:
        assert response.status_code == 200
        draft = response.json()
        assert draft['extraction_review']['review_required'] is True
        assert draft['extraction_review']['verification_status'] == ('completed' if problem == 'mismatch' else 'unavailable')
        reason = 'The second reading disagrees with this field.' if problem == 'mismatch' else 'The second reading could not confirm this field.'
        assert reason in draft['extraction_review']['facts'][0]['review_reasons']
        stored = store.draft(draft['id'])
        assert stored['extraction_proposal']['fields'][0]['value'] == '5.6'
        assert activity[0]['status'] == 'review_required'
        trace = activity[0]['telemetry']['calls']
        assert [call['stage'] for call in trace] == ['ExtractRecordedFields', 'VerifyRecordedFields']
        assert trace[-1]['result_validation'] == ('passed' if problem == 'mismatch' else 'failed')


def test_pytest_disables_dotenv_before_parsing_any_credential_file(tmp_path, monkeypatch):
    import dotenv
    import dotenv.main
    # This is a newly authored canary file, never the workspace credential file.
    canary = tmp_path / 'credential-canary.env'
    canary.write_text('MODEL_API_KEY=ARTIFICIAL_CANARY\nMODUS_TEST_SECRET_CANARY=do-not-load\n', encoding='utf-8')
    monkeypatch.delenv('MODUS_TEST_SECRET_CANARY', raising=False)
    assert os.environ['PYTHON_DOTENV_DISABLED'] == '1'
    assert os.environ['MODEL_API_KEY'] == ''
    def prohibited(*args, **kwargs):
        pytest.fail('Tests must not open or parse dotenv credential files')
    monkeypatch.setattr(dotenv.main.DotEnv, '_get_stream', prohibited)
    assert dotenv.load_dotenv(canary, override=True) is False
    assert os.environ['MODEL_API_KEY'] == ''
    assert 'MODUS_TEST_SECRET_CANARY' not in os.environ

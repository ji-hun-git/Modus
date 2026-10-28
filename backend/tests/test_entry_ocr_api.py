"""Retired entry OCR route and preserved legacy evidence; no model inference."""
from copy import deepcopy
from datetime import datetime, timezone
import importlib
import json

import pytest
from fastapi.testclient import TestClient

from modus.ingest import make_draft
from modus import local_ocr


NOW = datetime(2026, 10, 27, 12, 0, tzinfo=timezone.utc)
SENTINEL = 'ARTIFICIAL_FUTURE_OCR_SENTINEL'
RAW = b'artificial image bytes; fake OCR only'


@pytest.fixture
def ocr_api(tmp_path, monkeypatch):
    monkeypatch.setenv('MODUS_PROVIDER', 'offline')
    monkeypatch.delenv('MODEL_API_KEY', raising=False)
    monkeypatch.setenv('MODUS_ENTRY_DB_PATH', str(tmp_path / 'module.db'))
    module = importlib.import_module('modus_entry.app')
    monkeypatch.setattr(local_ocr, 'status', lambda: {'available': True, 'mode': 'local-teleocr',
        'model': 'artificial-pinned-model', 'revision': 'artificial-revision'})
    calls = []
    def fake_draft(raw, filename):
        calls.append((raw, filename))
        rows = [{'metric': 'egfr', 'value': 71, 'unit': 'mL/min/1.73m2', 'date': '2021-04-08',
            'source_span': 'eGFR 71 mL/min/1.73m2 2021-04-08', 'page': 1}]
        draft = make_draft(filename, raw, extracted=rows, extraction_mode='local-teleocr')
        draft['source'].update(content='Unverified synthetic local OCR text.',
            ocr_pages=[{'page': 1, 'text': rows[0]['source_span']}],
            ocr_execution={'model': 'artificial-pinned-model', 'revision': 'artificial-revision'})
        draft['telemetry'] = {'mode': 'local-teleocr', 'status': 'completed',
            'model': 'artificial-pinned-model', 'revision': 'artificial-revision',
            'input_tokens': 10, 'output_tokens': 5}
        draft['warnings'].append('Unverified synthetic model transcription; review every field.')
        return draft
    monkeypatch.setattr(local_ocr, 'make_local_history_draft', fake_draft)
    async def forbidden_provider(*args, **kwargs):
        pytest.fail('The explicit local OCR path called Meta')
    monkeypatch.setattr(module, 'extract_record_document', forbidden_provider)
    app = module.create_entry_app(tmp_path / 'entry.db', clock=lambda: NOW)
    with TestClient(app) as client:
        yield client, app.state.store, module, calls, fake_draft


def preview(client, **flags):
    return client.post('/api/imports/preview', data={'synthetic_confirmed': 'true', **flags},
        files={'file': ('artificial.png', RAW, 'image/png')})


def records(client, as_of='2026-10-27', known_at=None):
    params = {'as_of': as_of}
    if known_at:
        params['known_at'] = known_at
    response = client.get('/api/records/view', params=params)
    assert response.status_code == 200
    return response.json()


def reviewed(draft):
    return [{key: row[key] for key in ('id', 'metric', 'value', 'unit', 'date')}
        for row in draft['observations']]


def test_health_reports_retired_ocr_even_when_shared_research_model_is_installed(ocr_api):
    client, _, _, calls, _ = ocr_api
    health = client.get('/api/health').json()
    assert health['local_ocr']['available'] is False
    assert health['local_ocr']['mode'] == 'disabled'
    assert 'retired' in health['local_ocr']['reason']
    assert health['provider']['mode'] == 'offline'
    assert calls == []


def test_two_model_selections_reject_before_inference_or_draft(ocr_api):
    client, store, _, calls, _ = ocr_api
    before = records(client)
    response = preview(client, use_meta='true', use_local_ocr='true')
    assert response.status_code == 422
    assert calls == [] and store.history() == []
    assert records(client)['observations'] == before['observations']


def test_local_text_is_default_and_image_needs_explicit_model(ocr_api):
    client, _, _, calls, _ = ocr_api
    assert preview(client).status_code == 422
    csv = client.post('/api/imports/preview', data={'synthetic_confirmed': 'true'},
        files={'file': ('artificial.csv', b'metric,value,unit,date\negfr,71,mL/min/1.73m2,2021-04-08\n', 'text/csv')})
    assert csv.status_code == 200
    assert csv.json()['extraction_mode'] == 'local'
    assert calls == []


def test_local_ocr_preview_is_rejected_without_draft_or_commit(ocr_api):
    client, store, _, calls, _ = ocr_api
    before = records(client)
    response = preview(client, use_local_ocr='true')
    assert response.status_code == 422
    assert calls == []
    assert records(client)['observations'] == before['observations']
    with store.connect() as db:
        assert db.execute('SELECT count(*) FROM drafts').fetchone()[0] == 0


@pytest.mark.parametrize('error_class', ['LocalOCRError', 'RuntimeError', 'ValueError'])
def test_retired_ocr_never_runs_worker_or_fallback_even_if_worker_would_fail(ocr_api, monkeypatch, error_class):
    client, store, module, _, _ = ocr_api
    before = records(client)
    cls = local_ocr.LocalOCRError if error_class == 'LocalOCRError' else RuntimeError if error_class == 'RuntimeError' else ValueError
    def failed(*args):
        raise cls('ARTIFICIAL_PRIVATE_WORKER_ERROR')
    monkeypatch.setattr(local_ocr, 'make_local_history_draft', failed)
    monkeypatch.setattr(module, 'make_draft', lambda *args: pytest.fail('OCR failure silently used text parser'))
    response = preview(client, use_local_ocr='true')
    assert response.status_code == 422
    assert 'ARTIFICIAL_PRIVATE_WORKER_ERROR' not in response.text
    assert records(client)['observations'] == before['observations']
    changes = client.get('/api/changes').json()['changes']
    assert changes == []
    assert 'ARTIFICIAL_PRIVATE_WORKER_ERROR' not in json.dumps(store.history())


def test_ocr_requires_synthetic_attestation_before_inference(ocr_api):
    client, _, _, calls, _ = ocr_api
    response = client.post('/api/imports/preview', data={'use_local_ocr': 'true'},
        files={'file': ('artificial.png', RAW, 'image/png')})
    assert response.status_code == 400 and calls == []


def test_legacy_ocr_draft_review_remains_idempotent_and_historical(ocr_api):
    client, store, _, _, fake = ocr_api
    before = records(client, '2021-12-31', '2021-12-31T23:59:59Z')
    draft = store.add_draft(fake(RAW, 'artificial.png'), raw=RAW, filename='artificial.png', mime='image/png')
    rows = reviewed(draft)
    rows[0]['value'] = 72
    payload = {'draft_id': draft['id'], 'synthetic_confirmed': True, 'reviewed_observations': rows}
    first = client.post('/api/imports/commit', json=payload)
    retry = client.post('/api/imports/commit', json=payload)
    assert first.status_code == retry.status_code == 200
    assert first.json()['inserted'] == 1 and retry.json()['inserted'] == 0
    assert first.json()['available_at'] == retry.json()['available_at']
    assert records(client, '2021-12-31', '2021-12-31T23:59:59Z')['observations'] == before['observations']
    current = records(client, '2021-12-31')
    accepted = next(row for row in current['observations'] if row['source_id'] == draft['id'])
    assert accepted['value'] == 72 and 'value' in accepted['reviewed_fields']
    assert client.get(f"/api/drafts/{draft['id']}/original").status_code == 404
    assert client.get(f"/api/records/{draft['id']}/original", params={'as_of': '2021-12-31',
        'known_at': '2021-12-31T23:59:59Z'}).status_code == 404


@pytest.mark.parametrize('exclude_future', [False, True])
def test_partial_source_never_exposes_future_nested_ocr(ocr_api, monkeypatch, exclude_future):
    client, store, module, _, fake = ocr_api
    def mixed(raw, name):
        draft = fake(raw, name)
        future = deepcopy(draft['observations'][0])
        future.update(id=draft['id'] + '-future', value=99, date='2030-01-01', source_span=SENTINEL)
        draft['observations'].append(future)
        draft['source'].update(date='2030-01-01', content=SENTINEL,
            ocr_pages=[{'page': 1, 'text': SENTINEL}],
            ocr_execution={'nested': {'text': SENTINEL}})
        draft['telemetry']['nested'] = {'pages': [{'text': SENTINEL}]}
        return draft
    # Historical stored proposals can be reviewed; this does not re-enable an OCR API.
    draft = store.add_draft(mixed(RAW, 'artificial.png'), raw=RAW, filename='artificial.png', mime='image/png')
    rows = reviewed(draft)[:1] if exclude_future else reviewed(draft)
    response = client.post('/api/imports/commit', json={'draft_id': draft['id'],
        'synthetic_confirmed': True, 'reviewed_observations': rows})
    assert response.status_code == 200
    partial_sources = store.sources('2021-12-31')
    partial = next(source for source in partial_sources if source['id'] == draft['id'])
    assert not partial['original_available']
    assert not any(key in partial for key in ('ocr_pages', 'ocr_execution', 'extraction_telemetry', 'review'))
    assert SENTINEL not in json.dumps(partial_sources)
    response = records(client, '2021-12-31')
    assert SENTINEL not in json.dumps(response)
    exported = client.post('/api/records/export', json={'as_of': '2021-12-31',
        'known_at': response['scope']['known_at']})
    assert exported.status_code == 200 and SENTINEL not in exported.text
    assert client.get(f"/api/records/{draft['id']}/original", params={'as_of': '2021-12-31',
        'known_at': response['scope']['known_at']}).status_code == 404
    full = next(source for source in store.sources('2030-12-31') if source['id'] == draft['id'])
    assert SENTINEL in json.dumps(full)  # Original evidence is preserved, not erased.


@pytest.mark.parametrize('empty_result', [False, True])
def test_legacy_failed_or_empty_ocr_activity_retains_bounded_costs_without_text(ocr_api, monkeypatch, empty_result):
    client, store, _, _, _ = ocr_api
    telemetry = {'mode':'local-teleocr','status':'completed' if empty_result else 'failed',
            'input_tokens':30,'output_tokens':12,'usage_verified':True,'raw_text':'ARTIFICIAL_HIDDEN_TEXT',
            'attempts':[{'attempt':1,'resolution':'primary','status':'failed','input_tokens':20,'output_tokens':8,
                'diagnostic':{'kind':'layout_output','text':'ARTIFICIAL_HIDDEN_TEXT'}},
                {'attempt':2,'resolution':'fallback','status':'completed' if empty_result else 'failed','input_tokens':10,'output_tokens':4}]}
    store.save_run({'schema':'modus-entry-change-v1','kind':'extraction_failure',
        'status':'failed','mode':'local-teleocr','telemetry':telemetry})
    changes = client.get('/api/changes').json()['changes']
    telemetry = changes[0]['telemetry']
    assert telemetry['input_tokens']==30 and telemetry['output_tokens']==12
    assert len(telemetry['local_attempts'])==2 and telemetry['local_attempts'][0]['status']=='failed'
    assert 'ARTIFICIAL_HIDDEN_TEXT' not in json.dumps(changes)

"""Offline HTTP review and commit regression using an explicitly artificial transport."""
from datetime import datetime, timezone
import importlib

from fastapi.testclient import TestClient
import pytest

from modus import provider, record_extraction
from modus.record_history_models import ReviewedFact
from test_record_extraction import pdf
from test_record_row_inventory import ArtificialInventoryReader, SOURCE, MISSING_QUOTE


@pytest.fixture
def service(tmp_path, monkeypatch):
    monkeypatch.setenv('MODUS_ENTRY_DB_PATH', str(tmp_path / 'module.db'))
    module = importlib.import_module('modus_entry.app')
    transport = ArtificialInventoryReader()
    monkeypatch.setattr(module, 'provider_status', lambda: {'mode':'meta','model':'muse-spark-1.3'})
    async def forbidden(*args, **kwargs):
        pytest.fail('Offline inventory flow cannot invoke a live provider')
    monkeypatch.setattr(provider, 'meta_request', forbidden)
    async def extract(raw, name, mime, telemetry, **kwargs):
        return await record_extraction.extract_record_document(raw, name, mime, telemetry, request=transport, **kwargs)
    monkeypatch.setattr(module, 'extract_record_document', extract)
    app = module.create_entry_app(tmp_path / 'records.db', clock=lambda: datetime(2026,11,3,9,tzinfo=timezone.utc))
    with TestClient(app) as client:
        yield client, app.state.store, transport


def upload(client, raw):
    return client.post('/api/imports/preview', data={'synthetic_confirmed':'true','use_meta':'true'},
        files={'file':('authored-omission.pdf',raw,'application/pdf')})


def test_omission_flag_is_visible_preserved_and_never_an_implicit_commit(service):
    client, store, transport = service
    raw = pdf(SOURCE)
    before = client.get('/api/history/view').json()['counts']
    reply = upload(client, raw)
    assert reply.status_code == 200, reply.text
    draft = reply.json()
    check = draft['extraction_review']['completeness_check']
    omitted, = check['omissions']
    assert omitted['source_quote'] == MISSING_QUOTE and omitted['page'] == 1
    assert len(draft['facts']) == 1 and len(draft['observations']) == 1
    assert client.get('/api/history/view').json()['counts'] == before
    assert client.get(f"/api/drafts/{draft['id']}/original").content == raw
    fields = [{k:f.get(k) for k in ReviewedFact.model_fields} for f in draft['facts']]
    body = {'draft_id':draft['id'], 'synthetic_confirmed':True, 'reviewed_facts':fields}
    forged = {**fields[0], 'id':omitted['id'], 'label':'Ferritin', 'value':'29.40', 'unit':'ng/mL'}
    rejected = client.post('/api/history/commit', json={**body, 'reviewed_facts':fields + [forged]})
    assert rejected.status_code == 422
    assert client.get('/api/history/view').json()['counts'] == before
    assert client.post('/api/history/commit', json={**body, 'completeness_check':{'status':'complete'}}).status_code == 422
    receipt = client.post('/api/history/commit', json=body)
    assert receipt.status_code == 200 and receipt.json()['inserted'] == 1
    saved = client.get('/api/history/view').json()
    assert saved['counts']['facts'] == before['facts'] + 1
    own_facts = [f for f in saved['facts'] if f['source_id'] == draft['id']]
    assert len(own_facts) == 1 and own_facts[0]['label'] == 'HbA1c'
    assert client.get('/api/history/sources/'+draft['id']+'/original',
        params={'known_at':saved['scope']['known_at']}).content == raw
    # A missing row's occurrence date is unreviewed. A dated view cannot use the
    # extracted row's date to authorize disclosure of the whole original file.
    assert store.draft(draft['id'])['source']['unresolved_row_inventory'] is True
    dated = client.get('/api/history/view', params={'as_of':'2024-12-31'}).json()
    selected = next(s for s in dated['sources'] if s['id'] == draft['id'])
    assert selected['original_available'] is False
    assert client.get('/api/history/sources/'+draft['id']+'/original',
        params={'as_of':'2024-12-31','known_at':saved['scope']['known_at']}).status_code == 404
    reopened = upload(client, raw).json()
    assert reopened['already_committed'] and reopened['extraction_review']['completeness_check'] == check
    assert store.draft(draft['id'])['extraction_proposal']['row_inventory'][0]['rows'][1]['source_quote'] == MISSING_QUOTE
    assert len(transport.calls) == 3  # Neither review, commit nor reopen spends again.
    assert client.post('/api/history/commit',json=body).json()['duplicate'] is True


def test_failed_inventory_keeps_proposal_and_original_available_for_review(service):
    client, _, transport = service
    transport.inventory_output = TimeoutError('PRIVATE_FAILURE')
    raw = pdf(SOURCE)
    reply = upload(client,raw)
    assert reply.status_code == 200
    draft = reply.json()
    assert draft['extraction_review']['completeness_check']['status'] == 'unavailable'
    assert len(draft['facts']) == 1 and 'PRIVATE_FAILURE' not in reply.text
    assert client.get(f"/api/drafts/{draft['id']}/original").content == raw
    calls = client.get('/api/changes').json()['changes'][0]['telemetry']['calls']
    assert calls[-1]['stage'] == 'InventoryReportRows' and calls[-1]['error_kind'] == 'timeout'
    assert len(transport.calls) == 3


def test_zero_field_proposal_retains_omissions_but_has_no_savable_rows(service):
    client, _, transport = service
    transport.proposed = []
    reply = upload(client, pdf(SOURCE))
    assert reply.status_code == 200
    draft = reply.json()
    assert draft['facts'] == [] and len(draft['extraction_review']['completeness_check']['omissions']) == 2
    assert client.post('/api/history/commit', json={'draft_id':draft['id'],
        'synthetic_confirmed':True, 'reviewed_facts':[]}).status_code == 422
    assert len(transport.calls) == 2

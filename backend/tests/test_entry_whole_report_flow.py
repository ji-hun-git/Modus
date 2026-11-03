"""Actual HTTP import/review boundary with explicitly artificial model transport."""
from copy import deepcopy
from datetime import datetime, timezone
import importlib

from fastapi.testclient import TestClient
import pytest

from modus import provider, record_extraction
from modus_entry.report_coverage import public_coverage
from test_whole_report_reader import ArtificialReader, pdf, response


@pytest.fixture
def api(tmp_path, monkeypatch):
    monkeypatch.setenv('MODUS_ENTRY_DB_PATH', str(tmp_path / 'module.db'))
    module = importlib.import_module('modus_entry.app')
    monkeypatch.setattr(module, 'provider_status', lambda: {'mode':'meta','model':'muse-spark-1.3'})
    transport = ArtificialReader()
    async def forbidden(*args, **kwargs):
        pytest.fail('Offline whole-report integration must never use a live transport')
    monkeypatch.setattr(provider, 'meta_request', forbidden)
    async def extract(raw, name, mime, telemetry, **kwargs):
        return await record_extraction.extract_record_document(raw, name, mime, telemetry, request=transport, **kwargs)
    monkeypatch.setattr(module, 'extract_record_document', extract)
    app = module.create_entry_app(tmp_path / 'history.db', clock=lambda: datetime(2026,10,29,9,tzinfo=timezone.utc))
    with TestClient(app) as client:
        yield client, app.state.store, transport


def upload(client, raw):
    return client.post('/api/imports/preview', data={'synthetic_confirmed':'true','use_meta':'true'},
                       files={'file':('authored-whole-report.pdf', raw, 'application/pdf')})


def test_whole_report_review_save_original_and_duplicate_flow(api):
    client, store, transport = api
    raw = pdf(4)
    before = client.get('/api/history/view').json()['counts']
    draft_response = upload(client, raw)
    assert draft_response.status_code == 200, draft_response.text
    draft = draft_response.json()
    coverage = draft['extraction_review']['coverage']
    assert coverage['processed_pages'] == coverage['page_count'] == 4
    assert coverage['completeness'] == 'not_established'
    assert coverage['request_count'] == len(transport.calls) == 6
    assert [row['page'] for row in draft['facts']] == [1,2,3,4]
    assert client.get('/api/history/view').json()['counts'] == before
    assert client.get(f"/api/drafts/{draft['id']}/original").content == raw
    assert upload(client, raw).status_code == 200 and len(transport.calls) == 6
    rows = [{key: row[key] for key in ('id','kind','label','value','unit','occurred_on','facility')} for row in draft['facts']]
    rows[3]['value'] = '74.50'
    body = {'draft_id':draft['id'],'synthetic_confirmed':True,'reviewed_facts':rows}
    saved = client.post('/api/history/commit',json=body)
    assert saved.status_code == 200 and saved.json()['inserted'] == 4
    view = client.get('/api/history/view').json()
    fourth = next(row for row in view['facts'] if row['id']==saved.json()['fact_ids'][3])
    assert fourth['page']==4 and fourth['value']=='74.50' and '74.00' in fourth['source_quote']
    original = f"/api/history/sources/{saved.json()['source_id']}/original"
    assert client.get(original, params={'known_at':view['scope']['known_at']}).content == raw
    assert client.post('/api/history/commit',json=body).json()['duplicate'] is True
    assert store.draft(draft['id'])['extraction_proposal']['coverage']['page_count']==4


def test_failed_middle_group_exposes_only_processing_ledger_and_saves_nothing(api):
    client, store, transport = api
    def fail(stage, pages, content):
        if stage=='ExtractRecordedFields' and pages==[4,5,6]:
            return response('invalid output containing private-provider-body')
    transport.change = fail
    before = client.get('/api/history/view').json()['counts']
    result = upload(client, pdf(7))
    assert result.status_code == 422
    detail = result.json()['detail']
    assert detail['report_coverage']['processed_pages'] == 3
    assert [row['status'] for row in detail['report_coverage']['pages']] == ['processed']*3 + ['failed']*3 + ['not_run']
    assert 'private-provider-body' not in result.text
    assert client.get('/api/history/view').json()['counts'] == before
    changes = client.get('/api/changes').json()['changes']
    failure = next(change for change in changes if change['kind']=='extraction_failure')
    assert failure['telemetry']['report_coverage'] == detail['report_coverage']


def test_empty_report_retains_original_and_coverage_but_cannot_commit(api):
    client, store, transport = api
    transport.change = lambda stage, pages, content: response({'extraction':{'document_type':'other','fields':[]}}) if stage == 'ExtractRecordedFields' else None
    raw = pdf(4)
    result = upload(client, raw)
    assert result.status_code == 200, result.text
    draft = result.json()
    assert draft['facts']==[] and len(transport.calls)==4
    assert len(draft['extraction_review']['completeness_check']['omissions']) == 4
    assert all(page['status']=='no_fields' for page in draft['extraction_review']['coverage']['pages'])
    assert client.get(f"/api/drafts/{draft['id']}/original").content==raw
    assert client.post('/api/history/commit',json={'draft_id':draft['id'],'synthetic_confirmed':True,'reviewed_facts':[]}).status_code==422


def test_public_coverage_drops_provider_content_and_rejects_inconsistent_ledgers():
    value = {'version':'whole-report-v1','status':'completed','page_count':1,'request_count':1,
        'completeness':'clinically_proven','secret':'private','groups':[{'error_kind':'private'}],
        'pages':[{'page':1,'status':'no_fields','field_count':0,'verification_status':'not_run',
                  'readability':'image_only','text_available':False,'vision_supplied':True,'raw_text':'private'}]}
    clean = public_coverage(value)
    assert clean['completeness']=='not_established' and 'private' not in str(clean)
    wrong = deepcopy(value); wrong['pages'][0]['page']=True
    assert public_coverage(wrong) is None
    wrong = deepcopy(value); wrong['pages'][0]['status']='not_run'
    assert public_coverage(wrong) is None

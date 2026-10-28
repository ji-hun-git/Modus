"""Fresh authored record-to-brief HTTP flow; no remote inference or held-outs."""
from datetime import datetime, timezone
import importlib
import json
from pathlib import Path

from fastapi.testclient import TestClient
import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def brief_api(tmp_path, monkeypatch):
    monkeypatch.setenv('MODUS_ENTRY_DB_PATH', str(tmp_path / 'module.db'))
    module = importlib.import_module('modus_entry.app')
    clock = [datetime(2026, 10, 28, 10, tzinfo=timezone.utc)]
    app = module.create_entry_app(tmp_path / 'brief.db', clock=lambda: clock[0])
    with TestClient(app) as client:
        for name in ('01-childhood.csv','02-visit-and-report.csv','03-laboratory.csv','04-later-copy.csv'):
            raw = (ROOT / 'data/synthetic/brief-demo' / name).read_bytes()
            response = client.post('/api/imports/preview', data={'synthetic_confirmed':'true'},
                files={'file': (name, raw, 'text/csv')})
            assert response.status_code == 200, response.text
            draft = response.json()
            keys = ('id','kind','label','value','unit','occurred_on','facility')
            receipt = client.post('/api/history/commit', json={'draft_id':draft['id'],
                'synthetic_confirmed':True, 'reviewed_facts':[{key:r[key] for key in keys} for r in draft['facts']]})
            assert receipt.status_code == 200, receipt.text
        yield client, app.state.store, clock


def request_for(client):
    view = client.get('/api/history/view').json()
    rows = view['facts'] + view['undated_facts']
    chosen = [r['id'] for r in rows if r['label'] in {'MMR','Cetirizine','Left knee radiology report'}
        or r['label']=='Ferritin' and r['value']=='32.0']
    return {'as_of':None,'known_at':view['scope']['known_at'],'selected_fact_ids':chosen,
        'title':'Records for my next appointment','owner_note':'Please help me check the two laboratory copies.'}


def test_review_export_preserves_selected_facts_conflict_sources_and_store(brief_api):
    client, store, clock = brief_api
    before = client.get('/api/history/view').json()['counts']
    body = request_for(client)
    preview = client.post('/api/briefs/preview',json=body)
    assert preview.status_code == 200, preview.text
    brief = preview.json()
    assert brief['counts']['selected']==4 and brief['counts']['conflict_companions']==1
    ferritin = [r for r in brief['entries'] if r['label']=='Ferritin']
    assert {r['value'] for r in ferritin}=={'32.0','29.5'}
    assert {r['unit'] for r in ferritin}=={'ng/mL'}
    vaccine = next(r for r in brief['entries'] if r['label']=='MMR')
    assert vaccine['occurred_on']=='2008' and vaccine['date'] is None
    clock[0] = datetime(2026,10,28,11,tzinfo=timezone.utc)
    export = client.post('/api/briefs/export',json={**body,'preview_id':brief['preview_id'],'reviewed':True,'format':'html'})
    assert export.status_code==200, export.text
    assert 'text/html' in export.headers['content-type']
    assert 'attachment' in export.headers['content-disposition']
    assert export.headers['cache-control']=='no-store'
    assert "default-src 'none'" in export.headers['content-security-policy']
    assert '<script' not in export.text.lower()
    for text in ('32.0','29.5','2008','Cetirizine','Please help me check the two laboratory copies.'):
        assert text in export.text
    structured = client.post('/api/briefs/export',json={**body,'preview_id':brief['preview_id'],'reviewed':True,'format':'json'})
    assert structured.status_code==200
    assert {r['id'] for r in structured.json()['entries']}=={r['id'] for r in brief['entries']}
    assert client.get('/api/history/view').json()['counts']==before
    assert not any(r.get('kind')=='question' for r in store.history())


@pytest.mark.parametrize('change',[{'title':'Changed after review'},{'owner_note':'Unreviewed note'},
    {'preview_id':'sha256:'+'0'*64}])
def test_export_rejects_content_changed_after_preview(brief_api,change):
    client,_,_=brief_api
    body=request_for(client)
    brief=client.post('/api/briefs/preview',json=body).json()
    response=client.post('/api/briefs/export',json={**body,'preview_id':brief['preview_id'],'reviewed':True,'format':'html',**change})
    assert response.status_code==409, response.text


@pytest.mark.parametrize('reviewed',[False,1,'true',None])
def test_export_requires_explicit_boolean_review(brief_api,reviewed):
    client,_,_=brief_api
    body=request_for(client)
    brief=client.post('/api/briefs/preview',json=body).json()
    response=client.post('/api/briefs/export',json={**body,'preview_id':brief['preview_id'],'reviewed':reviewed,'format':'html'})
    assert response.status_code==422


def test_late_or_invented_selection_cannot_enter_a_brief(brief_api):
    client,_,_=brief_api
    body=request_for(client)
    assert client.post('/api/briefs/preview',json={**body,'known_at':'2026-10-27T23:59:59Z'}).status_code==422
    assert client.post('/api/briefs/preview',json={**body,'selected_fact_ids':['invented-id']}).status_code==422
    assert client.post('/api/briefs/preview',json={**body,'source_text':'forged evidence'}).status_code==422


def test_profile_revision_does_not_leak_or_invalidate_selected_brief(brief_api):
    client,_,clock=brief_api
    body=request_for(client)
    brief=client.post('/api/briefs/preview',json=body).json()
    clock[0]=datetime(2026,10,28,11,tzinfo=timezone.utc)
    assert client.put('/api/profile',json={'date_of_birth':'1991-07-23'}).status_code==200
    response=client.post('/api/briefs/export',json={**body,'preview_id':brief['preview_id'],'reviewed':True,'format':'json'})
    assert response.status_code==200,response.text
    assert '1991-07-23' not in response.text and 'source_proposal' not in response.text

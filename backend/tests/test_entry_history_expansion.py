"""T2 service regressions: new authored records, no evaluation sets or providers."""
from datetime import datetime, timezone
import importlib

from fastapi.testclient import TestClient
import pytest

from modus.ingest import make_draft
from modus.record_history_models import proposed_facts

NOW = datetime(2026, 10, 29, 9, tzinfo=timezone.utc)
HISTORY = ("kind,label,value,unit,date,facility\n"
    "measurement,Pulse,72.00,bpm,2016-06-02,Example clinic\n"
    "measurement,Pulse,75,bpm,2024-02-03,Example clinic\n"
    "measurement,Pulse,76,bpm,2024-02-03,Example clinic\n"
    "measurement,Glucose,95,mg/dL,2016-06-02,Example lab\n"
    "measurement,Glucose,5.3,mmol/L,2024-02-03,Example lab\n"
    "measurement,ALT,<5,U/L,2024-02-03,Example lab\n"
    "measurement,Weight,62.00,kg,2024,Example clinic\n"
    "measurement,Blood pressure,100/65,mmHg,2016-06-02,Example clinic\n"
    "measurement,Custom assay,negative,,,Example lab\n"
    "encounter,Annual visit,Visit documented,,2024-02-03,Example clinic\n"
    "prescription,Prescription entry,Historical wording only,,2024-02-03,Example clinic\n"
    "vaccination,Vaccination entry,Dose documented,,2012,Example clinic\n"
    "procedure,Procedure entry,Procedure documented,,2020-02-03,Example clinic\n"
    "imaging_text,Imaging report,Verbatim imaging text,,,Example clinic\n"
    "recorded_diagnosis,Provider wording,Recorded statement,,2020-02-03,Example clinic\n"
    "recorded_text,Appointment note,As printed in the note,,,Example clinic\n").encode()


@pytest.fixture
def api(tmp_path, monkeypatch):
    monkeypatch.setenv('MODUS_ENTRY_DB_PATH', str(tmp_path / 'module.db'))
    module = importlib.import_module('modus_entry.app')
    async def no_provider(*args, **kwargs):
        raise AssertionError('T2 regression cannot invoke a provider')
    monkeypatch.setattr(module, 'extract_record_document', no_provider)
    app = module.create_entry_app(tmp_path / 't2.db', clock=lambda: NOW)
    with TestClient(app) as client:
        yield client, app.state.store


def review(fields):
    return [{key: row[key] for key in ('id','kind','label','value','unit','occurred_on','facility')}
            for row in fields]


@pytest.mark.parametrize('proposal', [{'facts': []}, {'extraction_proposal': {'fields': []}}])
def test_explicitly_empty_proposal_cannot_fall_back_to_legacy_observations(proposal):
    draft = make_draft('old.csv', b'metric,value,unit,date\nHbA1c,5.60,%,2024-02-03\n')
    assert draft['observations']
    draft.update(proposal)
    with pytest.raises(ValueError, match='1 to 1,000 source facts'):
        proposed_facts(draft)


def test_mixed_history_preview_review_commit_and_source_bytes(api):
    client, _ = api
    before = client.get('/api/history/view').json()
    response = client.post('/api/imports/preview', data={'synthetic_confirmed':'true'},
        files={'file':('T2-authored-history.csv', HISTORY, 'text/csv')})
    assert response.status_code == 200, response.text
    draft = response.json()
    assert len(draft['facts']) == 16 and draft['observations'] == []
    assert len({f['label'] for f in draft['facts'] if f['kind']=='measurement'}) == 6
    assert client.get('/api/history/view').json()['counts'] == before['counts']
    reviewed = review(draft['facts'])
    reviewed[0]['value'] = '73.00'
    body = {'draft_id':draft['id'], 'synthetic_confirmed':True, 'reviewed_facts':reviewed}
    saved = client.post('/api/history/commit', json=body)
    assert saved.status_code == 200, saved.text
    assert saved.json()['inserted'] == 16 and saved.json()['observation_ids'] == []
    view = client.get('/api/history/view').json()
    all_facts = {f['id']:f for f in [*view['facts'], *view['undated_facts']]}
    imported = [f for f in all_facts.values() if f['source_id']==draft['source']['id']]
    assert len(imported) == 16
    assert len({f['kind'] for f in imported}) == 8
    pulse = next(f for f in imported if f['label']=='Pulse' and f['date']=='2016-06-02')
    assert pulse['value']=='73.00' and '72.00' in pulse['source_quote']
    assert pulse['source_proposal']['value']=='72.00' and 'value' in pulse['reviewed_fields']
    assert {f['unit'] for f in imported if f['label']=='Glucose'} == {'mg/dL','mmol/L'}
    assert next(f for f in imported if f['label']=='ALT')['value']=='<5'
    assert next(f for f in imported if f['label']=='Weight')['date'] is None
    assert next(f for f in imported if f['label']=='Weight')['occurred_on']=='2024'
    assert any(len(c['fact_ids'])==2 and set(c['fact_ids']) <= {f['id'] for f in imported if f['label']=='Pulse'} for c in view['conflicts'])
    original = f"/api/history/sources/{draft['source']['id']}/original"
    assert client.get(original, params={'known_at':NOW.isoformat()}).content == HISTORY
    assert client.get(original, params={'known_at':NOW.isoformat(),'as_of':'2016-06-02'}).status_code==404
    past = client.get('/api/history/view',params={'known_at':'2026-10-28T00:00:00Z'}).json()
    assert draft['source']['id'] not in {s['id'] for s in past['sources']}
    again=client.post('/api/history/commit',json=body)
    assert again.status_code==200 and again.json()['duplicate'] is True
    assert again.json()['available_at']==saved.json()['available_at']


def test_reopened_legacy_draft_uses_full_review_without_reextraction(api):
    client, store = api
    raw=b'metric,value,unit,date\nHbA1c,5.60,%,2024-02-03\n'
    old=make_draft('old.csv',raw)
    store.add_draft(old,raw=raw,filename='old.csv',mime='text/csv')
    original_proposal=store.draft(old['id'])
    reopened=client.post('/api/imports/preview', data={'synthetic_confirmed':'true','use_meta':'true'},
        files={'file':('old.csv',raw,'text/csv')})
    assert reopened.status_code==200, reopened.text
    field=reopened.json()['facts'][0]
    assert field['id']==old['observations'][0]['id']
    assert field['source_quote']==old['observations'][0]['source_span']
    rows=review([field]);rows[0]['label']='Owner-corrected recorded name'
    result=client.post('/api/history/commit',json={'draft_id':old['id'],'synthetic_confirmed':True,'reviewed_facts':rows})
    assert result.status_code==200, result.text
    saved=next(f for f in client.get('/api/history/view').json()['facts'] if f['source_id']==old['source']['id'])
    assert saved['label']=='Owner-corrected recorded name'
    assert saved['source_quote']==field['source_quote']
    assert saved['source_proposal']['label']==old['observations'][0]['metric']
    current_proposal=store.draft(old['id'])
    assert {k:v for k,v in current_proposal.items() if k!='already_committed'} == {k:v for k,v in original_proposal.items() if k!='already_committed'}

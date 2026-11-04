"""T2 service regressions: new authored records, no evaluation sets or providers."""
from datetime import datetime, timezone
import importlib

from fastapi.testclient import TestClient
import pytest

from modus.ingest import make_draft
from modus.record_history_models import proposed_facts
from pathlib import Path

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


def test_starter_checkup_has_open_labels_context_and_exact_scoped_original(api):
    client, _ = api
    view = client.get('/api/history/view').json()
    assert view['counts']['facts'] == 17
    assert len({fact['label'] for fact in view['facts']}) == 11
    source = next(source for source in view['sources'] if source['title'] == 'checkup-october-2026.csv')
    rows = [fact for fact in view['facts'] if fact['source_id'] == source['id']]
    assert {row['label'] for row in rows} == {'Glucose', 'Hemoglobin', 'White blood cells', 'Platelets', 'Ferritin', 'TSH', 'Vitamin D', 'ALT'}
    assert all(row['reference_range'] and row['specimen'] and row['test_method'] for row in rows)
    assert all(row['reviewer'] is None and row['extractor'] == 'authored_seed' for row in rows)
    raw = (Path(__file__).resolve().parents[2] / 'entry/frontend/public/examples/checkup-october-2026.csv').read_bytes()
    assert all(row['source_quote'] in raw.decode() for row in rows)
    url = f"/api/history/sources/{source['id']}/original"
    assert client.get(url, params={'known_at': NOW.isoformat()}).content == raw
    before_arrival = {'known_at': '2026-10-23T08:59:59Z'}
    assert client.get('/api/history/view', params=before_arrival).json()['counts']['facts'] == 9
    assert client.get(url, params=before_arrival).status_code == 404
    assert client.get(url, params={'known_at': NOW.isoformat(), 'as_of': '2026-10-21'}).status_code == 404
    # Even a Meta request for the same bytes reuses the fixture without a call,
    # a fabricated review, or an impossible second-save offer.
    reopened = client.post('/api/imports/preview', data={'synthetic_confirmed':'true', 'use_meta':'true'},
        files={'file':('checkup-october-2026.csv', raw, 'text/csv')})
    assert reopened.status_code == 200
    assert reopened.json()['already_committed'] is True
    assert reopened.json()['extraction_mode'] == 'authored_seed'
    assert 'No owner or model review' in ' '.join(reopened.json()['warnings'])
    assert client.get('/api/history/view').json()['counts']['facts'] == 17


def test_changed_demo_never_adds_to_an_existing_store(tmp_path):
    from modus.record_store import RecordStore
    from modus.record_history import history_view
    from modus_entry.seed import initial_data
    data = initial_data()
    path = tmp_path / 'existing.db'
    old = RecordStore(path, seed_provider=lambda: data[:2], clock=lambda: NOW)
    before = history_view(old)
    current = RecordStore(path, seed_provider=initial_data, clock=lambda: NOW)
    assert history_view(current) == before
    assert len(before['facts']) == 9
    # An explicit demo reset uses the complete current seed and keeps originals.
    current.reset()
    assert len(history_view(current)['facts']) == 17
    reopened = RecordStore(path, seed_provider=initial_data, clock=lambda: NOW)
    assert len(history_view(reopened)['facts']) == 17


@pytest.mark.parametrize('invalid', ['changed_bytes', 'invented_quote', 'not_synthetic'])
def test_invalid_demo_original_rolls_back_the_whole_seed(tmp_path, invalid):
    import sqlite3
    from modus.record_store import RecordStore
    from modus_entry.seed import initial_data
    data = initial_data()
    document = data[2][0]
    if invalid == 'changed_bytes':
        document['raw'] += b'changed'
    elif invalid == 'invented_quote':
        document['draft']['facts'][0]['source_quote'] = 'not present in the original'
    else:
        document['draft']['source']['synthetic'] = False
    path = tmp_path / 'rejected.db'
    with pytest.raises(ValueError):
        RecordStore(path, seed_provider=lambda: data)
    from modus.record_crypto import encrypted_connection
    from modus.record_keys import database_key
    with encrypted_connection(path, database_key(path)) as db:
        assert db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall() == []


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

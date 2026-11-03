"""Fresh authored archive fixtures; isolated databases and no model or eval inputs."""
from datetime import datetime, timezone
from pathlib import Path

from modus.record_history import history_view
from modus.record_history_models import ReviewedFact
from modus.record_store import RecordStore
from modus.temporal import instant
from modus_entry.seed import ARCHIVE_AVAILABLE_AT, ARCHIVE_FILES, initial_data
from modus_entry.history_agent import offline_chat
from modus_entry.history_tools import capture_history
from test_history_query_integration import query_service


NOW = datetime(2026, 11, 3, 9, tzinfo=timezone.utc)
EXAMPLES = Path(__file__).resolve().parents[2] / 'entry/frontend/public/examples'


def test_new_seed_has_56_archive_fields_12_tests_and_exact_originals(tmp_path):
    store = RecordStore(tmp_path/'fresh.db', seed_provider=initial_data, clock=lambda:NOW)
    view = history_view(store)
    assert view['counts']['facts'] == 73 and view['counts']['sources'] == 11
    documents = initial_data()[2]
    assert len(documents) == 8 and documents[0]['filename'] == 'checkup-october-2026.csv'
    archive_ids = {d['draft']['source']['id'] for d in documents[1:]}
    archive = [f for f in view['facts'] if f['source_id'] in archive_ids]
    assert len(archive) == 56 and len({f['label'] for f in archive}) == 12
    assert {f['occurred_on'][:4] for f in archive} == {'2010','2013','2016','2019','2022','2024','2025'}
    assert all(f['available_at'] == instant(ARCHIVE_AVAILABLE_AT) for f in archive)
    assert all(f['reviewer'] is None and f['reviewed_at'] is None and f['extractor'] == 'authored_seed' for f in archive)
    assert all(f['reference_range'] and f['specimen'] and f['test_method'] for f in archive)
    for doc in documents[1:]:
        raw = (EXAMPLES/doc['filename']).read_bytes()
        assert doc['raw'] == raw
        selected = [f for f in archive if f['source_id'] == doc['draft']['source']['id']]
        assert len(selected) == 8 and all(f['source_quote'] in raw.decode() for f in selected)
        with store.connect() as db:
            assert db.execute('SELECT raw FROM documents WHERE id=?', (doc['draft']['source']['id'],)).fetchone()[0] == raw


def test_archive_availability_is_separate_from_dates_and_scrubbing_changes_values(tmp_path):
    store = RecordStore(tmp_path/'timeline.db', seed_provider=initial_data, clock=lambda:NOW)
    assert history_view(store, known_at='2026-11-02T11:59:59Z')['counts']['facts'] == 17
    expected = {'2010':'24.8', '2013':'31.6', '2016':'27.4', '2019':'42.1',
                '2022':'36.8', '2024':'49.2', '2025':'53.0', '2026':'58.6'}
    for year, value in expected.items():
        context = capture_history(store, as_of=f'{year}-12-31')
        answer = offline_chat(context, 'What is my latest ferritin record?')
        assert answer['provider_requests_made'] == 0
        selected = answer['history_evidence']['facts']
        assert len(selected) == 1 and selected[0]['value'] == value
        assert selected[0]['occurred_on'][:4] == year
    # Historical availability replay cannot see archive files before their authored arrival.
    earlier = history_view(store, as_of='2016-12-31', known_at='2026-11-02T11:59:59Z')
    assert earlier['counts']['facts'] == 0


def test_existing_store_preserves_original_seed_until_explicit_reset(tmp_path):
    path = tmp_path/'existing.db'
    sources, observations, documents = initial_data()
    original = RecordStore(path, seed_provider=lambda:(sources, observations, documents[:1]), clock=lambda:NOW)
    before = history_view(original)
    with original.connect() as db:
        original_bytes = dict(db.execute('SELECT id,raw FROM documents').fetchall())
    reopened = RecordStore(path, seed_provider=initial_data, clock=lambda:NOW)
    assert history_view(reopened) == before and before['counts']['facts'] == 17
    with reopened.connect() as db:
        assert dict(db.execute('SELECT id,raw FROM documents').fetchall()) == original_bytes
    reopened.reset()
    assert history_view(reopened)['counts']['facts'] == 73
    assert RecordStore(path, seed_provider=initial_data, clock=lambda:NOW).history() == reopened.history()


def test_public_archive_files_import_through_review_with_actual_commit_availability(query_service):
    client, _, clock = query_service
    clock[0] = NOW
    assert client.get('/api/history/view').json()['counts']['facts'] == 0
    for filename in ARCHIVE_FILES:
        raw = (EXAMPLES/filename).read_bytes()
        preview = client.post('/api/imports/preview', data={'synthetic_confirmed':'true'},
            files={'file':(filename,raw,'text/csv')})
        assert preview.status_code == 200, preview.text
        draft = preview.json()
        assert len(draft['facts']) == 8
        payload = {'draft_id':draft['id'], 'synthetic_confirmed':True,
            'reviewed_facts':[{key:f.get(key) for key in ReviewedFact.model_fields} for f in draft['facts']]}
        committed = client.post('/api/history/commit', json=payload)
        assert committed.status_code == 200, committed.text
        receipt = committed.json()
        assert receipt['inserted'] == 8
        assert receipt['available_at'] == instant(NOW)
        assert receipt['available_at'] != instant(ARCHIVE_AVAILABLE_AT)
        original = client.get('/api/history/sources/'+receipt['source_id']+'/original', params={'known_at':NOW.isoformat()})
        assert original.status_code == 200 and original.content == raw
    view = client.get('/api/history/view').json()
    assert view['counts']['facts'] == 56 and view['counts']['sources'] == 7
    assert len({f['label'] for f in view['facts']}) == 12
    before_commit = client.get('/api/history/view', params={'known_at':ARCHIVE_AVAILABLE_AT}).json()
    assert before_commit['counts']['facts'] == 0

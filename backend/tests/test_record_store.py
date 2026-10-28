"""Isolation, frozen comparisons and transactional receipts for record stores."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
from threading import Event

import pytest

from modus.ingest import make_draft
from modus.record_models import ExtractedObservation, METRICS, Observation, ReviewedObservation
from modus.record_store import RecordStore
from modus.temporal import instant


EARLY = '2026-10-27T01:00:00Z'
COMMITTED = '2026-10-27T02:00:00Z'
LATER = '2026-10-27T03:00:00Z'


def seed():
    return ([{'id': 'authored-report', 'date': '2021-04-08', 'type': 'Lab report',
              'title': 'Authored laboratory document', 'synthetic': True,
              'content': 'SYNTHETIC. LDL 140 mg/dL; 2021-04-08.'}],
            [{'id': 'authored-row', 'source_id': 'authored-report', 'date': '2021-04-08',
              'metric': 'ldl', 'value': 140, 'unit': 'mg/dL',
              'source_span': 'LDL 140 mg/dL; 2021-04-08.', 'page': 1}])


def create_store(path, clock=lambda: EARLY):
    return RecordStore(path, seed_provider=seed, clock=clock)


def proposal(value=150):
    return make_draft('synthetic.csv',
                      f'metric,value,unit,date\nldl,{value},mg/dL,2021-04-08\n'.encode())


def reviews(draft):
    return [{key: row[key] for key in ('id', 'metric', 'value', 'unit', 'date')}
            for row in draft['observations']]


def test_neutral_store_import_closure_and_no_reference_bootstrap(tmp_path):
    backend = str(Path(__file__).resolve().parents[1])
    script = '''
import json, sys
sys.path.insert(0, sys.argv[1])
from modus.record_store import RecordStore
from modus.ingest import make_draft
from modus.record_models import METRICS
from modus.record_conflicts import conflicts
store = RecordStore(sys.argv[2], seed_provider=lambda: ([], []))
snapshot = store.snapshot()
blocked = [name for name in sys.modules if name in {
    'modus.models', 'modus.memory', 'modus.seed', 'modus.analysis', 'modus.agent', 'modus.app'}]
with store.connect() as db:
    tables = [row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")]
assert not blocked, blocked
assert not any('reference' in name for name in tables), tables
assert not hasattr(snapshot, '_memory') and not hasattr(snapshot, 'connect')
assert not hasattr(snapshot, 'reference_search') and not hasattr(store, 'references')
assert all('domain' not in metadata for metadata in METRICS.values())
print(json.dumps({'observations': snapshot.observations(), 'sources': snapshot.sources()}))
'''
    result = subprocess.run([sys.executable, '-I', '-c', script, backend, str(tmp_path / 'neutral.db')],
                            cwd=tmp_path, capture_output=True, text=True, check=True)
    assert json.loads(result.stdout) == {'observations': [], 'sources': []}


@pytest.mark.parametrize('kind', ['full', 'unmarked', 'wrong-schema', 'invalid-file'])
def test_incompatible_database_rejected_without_changing_bytes(tmp_path, kind):
    path = tmp_path / (kind + '.db')
    if kind == 'full':
        module = pytest.importorskip('modus.memory', reason='Full-product wrapper is intentionally absent from the entry extract')
        module.Memory(path)
    elif kind == 'unmarked':
        with sqlite3.connect(path) as db:
            db.execute('CREATE TABLE sources (id TEXT PRIMARY KEY, data TEXT NOT NULL)')
            db.execute('INSERT INTO sources VALUES (?,?)', ('legacy', json.dumps({'content': 'retained'})))
    elif kind == 'wrong-schema':
        store = create_store(path)
        with store.connect() as db:
            db.execute("UPDATE record_store_meta SET value='future-version' WHERE key='schema_version'")
    else:
        path.write_bytes(b'not a sqlite database; preserve this input')
    original = path.read_bytes()
    with pytest.raises(ValueError, match='Incompatible'):
        create_store(path)
    assert path.read_bytes() == original


def test_full_product_refuses_entry_identity_without_mutating_it(tmp_path):
    module = pytest.importorskip('modus.memory', reason='Full-product wrapper is intentionally absent from the entry extract')
    path = tmp_path / 'entry.db'
    create_store(path)
    original = path.read_bytes()
    with pytest.raises(ValueError, match='Incompatible'):
        module.Memory(path)
    assert path.read_bytes() == original


def test_reset_uses_only_explicit_seed_and_preserves_identity(tmp_path):
    store = create_store(tmp_path / 'reset.db')
    draft = proposal()
    store.add_draft(draft)
    store.commit_draft(draft['id'], reviews(draft))
    store.save_run({'kind': 'record_commit', 'source_id': draft['id']})
    store.reset()
    assert [row['id'] for row in store.sources()] == ['authored-report']
    assert [row['id'] for row in store.observations()] == ['authored-row']
    assert store.draft(draft['id']) is None and store.history() == []
    reopened = create_store(tmp_path / 'reset.db')
    assert reopened.sources() == store.sources()
    assert store.sources()[0]['availability_basis'] == 'authored_synthetic_timeline'
    assert all('domain' not in metadata for metadata in METRICS.values())


@pytest.mark.parametrize('invalid', ['omitted', 'empty', 'foreign', 'duplicate', 'authority', 'nonfinite'])
def test_review_rejection_leaves_no_partial_record_or_receipt(tmp_path, invalid):
    store = create_store(tmp_path / 'review.db')
    draft = proposal()
    store.add_draft(draft)
    rows = reviews(draft)
    if invalid == 'omitted':
        rows = None
    elif invalid == 'empty':
        rows = []
    elif invalid == 'foreign':
        rows[0]['id'] = 'not-from-this-draft'
    elif invalid == 'duplicate':
        rows += deepcopy(rows)
    elif invalid == 'authority':
        rows[0]['available_at'] = '2000-01-01T00:00:00Z'
    elif invalid == 'nonfinite':
        rows[0]['value'] = float('nan')
    with pytest.raises(ValueError):
        store.commit_draft(draft['id'], rows)
    assert [row['id'] for row in store.observations()] == ['authored-row']
    assert not store.draft(draft['id'])['already_committed']
    with store.connect() as db:
        assert db.execute('SELECT count(*) FROM record_commits').fetchone()[0] == 0


def test_receipt_retry_preserves_original_rows_time_and_conflicts(tmp_path):
    store = create_store(tmp_path / 'receipt.db', clock=lambda: COMMITTED)
    draft = proposal()
    store.add_draft(draft)
    result = store.commit_draft(draft['id'], reviews(draft))
    assert result['source_id'] == draft['source']['id']
    assert result['observation_ids'] == [row['id'] for row in draft['observations']]
    assert result['available_at'] == instant(COMMITTED)
    assert result['inserted'] == 1 and not result['duplicate']
    assert len(result['affected_conflicts']) == 1
    assert set(result['affected_conflicts'][0]['evidence_ids']) == {'authored-row', *result['observation_ids']}
    assert 'trend' not in result['affected_conflicts'][0]['reason']
    store.clock = lambda: LATER
    later = proposal(160)
    store.add_draft(later)
    store.commit_draft(later['id'], reviews(later))
    retry = store.commit_draft(draft['id'], reviews(draft))
    assert retry == {**result, 'inserted': 0, 'duplicate': True}
    assert store.draft(draft['id'])['already_committed']
    assert not any(row['source_id'] == draft['id'] for row in store.observations(known_at=EARLY))


def test_commit_conflicts_do_not_reveal_records_available_only_later(tmp_path):
    def delayed_seed():
        sources, observations = seed()
        sources[0]['available_at'] = LATER
        return sources, observations

    store = RecordStore(tmp_path / 'future-seed.db', seed_provider=delayed_seed, clock=lambda: COMMITTED)
    draft = proposal()
    store.add_draft(draft)
    result = store.commit_draft(draft['id'], reviews(draft))
    assert result['affected_conflicts'] == []
    assert len(store.observations()) == 1
    store.clock = lambda: LATER
    assert len(store.observations()) == 2


def test_comparison_captures_once_and_cannot_see_concurrent_commit(tmp_path):
    path = tmp_path / 'comparison.db'
    store = create_store(path)
    writer = create_store(path, clock=lambda: COMMITTED)
    draft = proposal()
    writer.add_draft(draft)
    capture_started, release_capture, writer_started = Event(), Event(), Event()

    def capture_clock():
        capture_started.set()
        assert release_capture.wait(5)
        return EARLY

    def commit():
        writer_started.set()
        return writer.commit_draft(draft['id'], reviews(draft))

    store.clock = capture_clock
    with ThreadPoolExecutor(max_workers=2) as pool:
        capturing = pool.submit(store.snapshot)
        try:
            assert capture_started.wait(5)
            committing = pool.submit(commit)
            assert writer_started.wait(5)
            assert not committing.done()
        finally:
            release_capture.set()
        captured = capturing.result(timeout=5)
        assert committing.result(timeout=5)['inserted'] == 1
    earlier = captured.narrow('2021-12-31T23:59:59Z')
    current = captured.narrow(LATER)
    assert earlier.captured_at == current.captured_at == instant(EARLY)
    assert current.known_at == instant(EARLY)
    assert earlier.observations() == current.observations()
    assert earlier.narrow(LATER).known_at == earlier.known_at
    assert len(writer.snapshot().observations()) == 2
    mutated_copy = current.observations()
    mutated_copy[0]['value'] = 999
    assert current.observations()[0]['value'] == 140
    with pytest.raises(ValueError, match='frozen'):
        captured.snapshot(LATER)


def test_concurrent_commit_result_cannot_include_later_upload_as_its_own(tmp_path):
    path = tmp_path / 'two-writers.db'
    first = create_store(path)
    second = create_store(path, clock=lambda: LATER)
    first_draft, second_draft = proposal(150), proposal(160)
    first.add_draft(first_draft)
    second.add_draft(second_draft)
    first_locked, release_first, second_started = Event(), Event(), Event()

    def first_clock():
        first_locked.set()
        assert release_first.wait(5)
        return COMMITTED

    def second_commit():
        second_started.set()
        return second.commit_draft(second_draft['id'], reviews(second_draft))

    first.clock = first_clock
    with ThreadPoolExecutor(max_workers=2) as pool:
        committing_first = pool.submit(first.commit_draft, first_draft['id'], reviews(first_draft))
        try:
            assert first_locked.wait(5)
            committing_second = pool.submit(second_commit)
            assert second_started.wait(5)
            assert not committing_second.done()
        finally:
            release_first.set()
        first_result = committing_first.result(timeout=5)
        second_result = committing_second.result(timeout=5)
    assert first_result['observation_ids'] == [first_draft['observations'][0]['id']]
    assert second_result['observation_ids'] == [second_draft['observations'][0]['id']]
    assert first_result['inserted'] == second_result['inserted'] == 1
    first_ids = set(first_result['affected_conflicts'][0]['evidence_ids'])
    assert first_ids == {'authored-row', first_draft['observations'][0]['id']}
    assert set(second_result['affected_conflicts'][0]['evidence_ids']) == first_ids | {second_draft['observations'][0]['id']}


def test_partial_event_projection_withholds_later_original_and_review(tmp_path):
    store = create_store(tmp_path / 'projection.db')
    raw = b'metric,value,unit,date\nldl,125,mg/dL,2020-01-01\nldl,199,mg/dL,2026-10-20\n'
    draft = store.add_draft(make_draft('multi-date.csv', raw), raw, 'multi-date.csv', 'text/csv')
    assert store.document(draft['id'])['raw'] == raw
    store.commit_draft(draft['id'], reviews(draft)[:1])
    source = next(row for row in store.snapshot().sources('2021-12-31') if row['id'] == draft['id'])
    assert source['historical_projection'] and not source['original_available']
    assert source['original_date'] == '2026-10-20'
    assert 'review' not in source and '199' not in json.dumps(source)


@pytest.mark.parametrize('schema', [Observation, ExtractedObservation, ReviewedObservation])
def test_record_units_reject_blank_text_without_rewriting_printed_units(schema):
    fields = {'id': 'row', 'source_id': 'source', 'source_span': 'printed row', 'page': 1,
              'metric': 'ldl', 'value': 3.1, 'unit': ' \t\n ', 'date': '2021-04-08'}
    payload = {key: value for key, value in fields.items() if key in schema.model_fields}
    with pytest.raises(ValueError, match='non-whitespace'):
        schema.model_validate(payload)
    payload['unit'] = ' mmol/L '
    assert schema.model_validate(payload).unit == ' mmol/L '


def test_partial_document_span_cannot_reveal_later_rows_and_original_is_preserved(tmp_path):
    store = create_store(tmp_path / 'spans.db')
    raw = b'metric,value,unit,date,source_span\nldl,140,mg/dL,2021-04-08,"2021 LDL 140; 2030 LDL 991"\nldl,991,mg/dL,2030-01-01,"2030 LDL 991"\n'
    draft = store.add_draft(make_draft('synthetic.csv', raw))
    store.commit_draft(draft['id'], reviews(draft)[:1])
    snapshot = store.snapshot()
    old = next(row for row in snapshot.observations('2021-12-31') if row['source_id'] == draft['id'])
    assert old['source_span_withheld']
    assert '991' not in old['source_span'] and '2030' not in old['source_span']
    full = next(row for row in snapshot.observations('2030-12-31') if row['source_id'] == draft['id'])
    assert not full['source_span_withheld']
    assert full['source_span'] == '2021 LDL 140; 2030 LDL 991'
    assert store.draft(draft['id'])['observations'][0]['source_span'] == full['source_span']


def test_commit_event_and_receipt_are_atomic_and_duplicate_does_not_reemit(tmp_path):
    calls = []

    def event_factory(receipt):
        calls.append(receipt)
        return {'kind': 'record_commit', 'source_id': receipt['source_id'],
                'observation_ids': receipt['observation_ids']}

    store = RecordStore(tmp_path / 'atomic-event.db', seed_provider=seed,
                        clock=lambda: COMMITTED, commit_event_factory=event_factory)
    draft = store.add_draft(proposal())
    result = store.commit_draft(draft['id'], reviews(draft))
    assert len(calls) == 1
    history = store.history()
    assert len(history) == 1
    assert history[0]['created_at'] == result['available_at']
    assert history[0]['observation_ids'] == result['observation_ids']
    store.commit_draft(draft['id'], reviews(draft))
    assert len(calls) == 1 and store.history() == history


def test_failed_commit_event_rolls_back_rows_receipt_and_draft_status(tmp_path):
    def failing_event(receipt):
        raise ValueError('Cannot create the commit event')

    store = RecordStore(tmp_path / 'failed-event.db', seed_provider=seed,
                        clock=lambda: COMMITTED, commit_event_factory=failing_event)
    draft = store.add_draft(proposal())
    with pytest.raises(ValueError, match='commit event'):
        store.commit_draft(draft['id'], reviews(draft))
    assert [row['id'] for row in store.observations()] == ['authored-row']
    assert not store.draft(draft['id'])['already_committed']
    assert store.history() == []
    with store.connect() as db:
        assert db.execute('SELECT count(*) FROM record_commits').fetchone()[0] == 0

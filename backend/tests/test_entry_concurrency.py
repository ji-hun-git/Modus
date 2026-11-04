"""New offline transaction/recovery regressions; no evaluation corpus access."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event, get_ident
from datetime import timedelta
import importlib
import json
import sqlite3

import pytest

from test_entry_amendments import service, prepare, save, fact, START, CSV
from modus.record_amendments import revision_history
from modus.record_history_view import history_views
from modus.record_store import packed_json_rows


def test_packed_rows_preserve_exact_json_and_order():
    with sqlite3.connect(':memory:') as db:
        db.execute('CREATE TABLE example (id INTEGER, data TEXT)')
        values = [{'id': 1, 'value': '한글 "quoted",\n[new]'}, {'id': 2, 'value': None}]
        db.executemany('INSERT INTO example VALUES (?,?)', [(v['id'], json.dumps(v)) for v in values])
        assert json.loads(packed_json_rows(db, 'SELECT data FROM example ORDER BY id DESC')) == values[::-1]
        assert json.loads(packed_json_rows(db, 'SELECT data FROM example WHERE id=?', (999,))) == []


@pytest.mark.parametrize('projection', ['history', 'revisions', 'snapshot'])
def test_projection_does_not_hold_database_writer_lock(service, monkeypatch, projection):
    client, store, clock, identity, _ = service
    body = prepare(client, identity, value='5.8')
    entered, release = Event(), Event()
    worker_id = []
    if projection == 'snapshot':
        owner, attribute = store, '_build_snapshot'
        read = store.snapshot
    elif projection == 'revisions':
        owner, attribute = importlib.import_module('modus.record_amendments'), '_decode_history_rows'
        read = lambda: revision_history(store, identity)
    else:
        owner, attribute = importlib.import_module('modus.record_history_view'), '_decode_history_rows'
        read = lambda: history_views(store, known_ats=(START, None))
    original = getattr(owner, attribute)
    def delayed(*args, **kwargs):
        if get_ident() == worker_id[0]:
            entered.set()
            assert release.wait(5), 'Projection was never released'
        return original(*args, **kwargs)
    monkeypatch.setattr(owner, attribute, delayed)
    def reader():
        worker_id.append(get_ident())
        return read()
    with ThreadPoolExecutor(max_workers=2) as pool:
        future = pool.submit(reader)
        try:
            assert entered.wait(5)
            # Writer must finish while a captured read is deliberately paused.
            clock[0] += timedelta(seconds=1)
            receipt = pool.submit(save, client, body).result(timeout=3)
            assert receipt['revision_id'] != body['expected_revision_id']
        finally:
            release.set()
        captured = future.result(timeout=5)
    if projection == 'history':
        assert [next(f['value'] for f in view['facts'] if f['id'] == identity) for view in captured] == ['5.6', '5.6']
        assert captured[0]['scope']['captured_at'] == captured[1]['scope']['captured_at']
    elif projection == 'revisions':
        assert [v['fact']['value'] for v in captured['versions']] == ['5.6']
    else:
        assert any(o['value'] == 5.6 for o in captured.observations())
    assert fact(client, identity)['value'] == '5.8'


def test_concurrent_lost_ack_retries_create_one_revision_and_preserve_evidence(service):
    client, store, clock, identity, source = service
    before = fact(client, identity)
    body = prepare(client, identity, value='5.8')
    save(client, body)  # Server committed; imagine this response never reached the tab.
    with ThreadPoolExecutor(max_workers=8) as pool:
        receipts = list(pool.map(lambda _: save(client, body), range(24)))
    assert len({r['amendment_id'] for r in receipts}) == 1
    versions = revision_history(store, identity)['versions']
    assert [v['fact']['value'] for v in versions] == ['5.6', '5.8']
    assert fact(client, identity, known_at=START.isoformat()) == before
    assert fact(client, identity)['source_quote'] == before['source_quote']
    scope = client.get('/api/history/view').json()['scope']
    assert client.get(f'/api/records/{source}/original', params={'as_of': '2026-10-30', 'known_at': scope['known_at']}).content == CSV
    with store.connect() as db:
        assert db.execute('SELECT count(*) FROM history_amendments').fetchone()[0] == 1


def test_external_database_lock_is_retryable_and_changes_nothing(service, monkeypatch):
    client, store, _, identity, _ = service
    body = prepare(client, identity, value='5.8')
    import sqlcipher3
    from modus.record_crypto import encrypted_connection
    connect = sqlcipher3.connect
    def impatient(*args, **kwargs):
        return connect(*args, **{**kwargs, 'timeout': 0.02})
    with encrypted_connection(store.path, store._key) as holder:
        holder.execute('BEGIN IMMEDIATE')
        monkeypatch.setattr(sqlcipher3, 'connect', impatient)
        response = client.post('/api/history/amendments/commit', json=body)
        assert response.status_code == 503
        assert response.headers['retry-after'] == '1'
        assert 'busy' in response.json()['detail']
    assert fact(client, identity)['value'] == '5.6'
    save(client, body)
    assert fact(client, identity)['value'] == '5.8'


def test_offline_analysis_and_audit_write_run_outside_event_loop(service, monkeypatch):
    client, store, _, _, _ = service
    module = importlib.import_module('modus_entry.app')
    import asyncio
    seen = []
    analyze, write = module.history_agent.offline_chat, store.save_run
    def worker_only(name, function):
        def wrapped(*args, **kwargs):
            with pytest.raises(RuntimeError, match='no running event loop'):
                asyncio.get_running_loop()
            seen.append(name)
            return function(*args, **kwargs)
        return wrapped
    monkeypatch.setattr(module.history_agent, 'offline_chat', worker_only('analysis', analyze))
    monkeypatch.setattr(store, 'save_run', worker_only('audit', write))
    assert client.post('/api/history/chat', json={'message': 'Show my HbA1c records'}).status_code == 200
    assert seen == ['analysis', 'audit']

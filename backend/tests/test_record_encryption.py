"""Real encrypted pages and failure recovery; only new synthetic test records."""
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path
import secrets
import sqlite3

import pytest

from modus import record_encryption_migration as migration, record_keys
from modus.record_crypto import StorageError, database_lock, encrypted_connection, verify_integrity
from modus.record_store import RecordStore
from modus_entry.app import create_entry_app
from test_entry_amendments import service, prepare, save


def plain_copy(store, path):
    with store.connect() as db:
        expected=migration.logical_snapshot(db)
        db.execute("ATTACH DATABASE ? AS plain KEY ''",(str(path),))
        db.execute("SELECT sqlcipher_export('plain')")
        for name,value in expected['versions'].items():
            db.execute('PRAGMA plain.'+name+'='+str(value))
        db.commit(); db.execute('DETACH DATABASE plain')
    return expected


def test_migration_preserves_originals_corrections_and_every_stored_value(service,tmp_path):
    client,store,_,identity,_=service
    save(client,prepare(client,identity,value='5.8'))
    path=tmp_path/'plain.db'
    expected=plain_copy(store,path)
    before=path.read_bytes()
    assert before.startswith(b'SQLite format 3')
    result=migration.migrate_database(path)
    assert result['verified']==expected
    assert not path.read_bytes().startswith(b'SQLite format 3')
    with pytest.raises(sqlite3.DatabaseError), sqlite3.connect(path) as db:
        db.execute('SELECT * FROM documents').fetchall()
    reopened=create_entry_app(path).state.store
    with reopened.connect() as db:
        assert migration.logical_snapshot(db)==expected
        originals=[tuple(row) for row in db.execute('SELECT id,raw FROM documents ORDER BY id')]
    with store.connect() as db:
        assert [tuple(row) for row in db.execute('SELECT id,raw FROM documents ORDER BY id')]==originals
    backup=Path(result['backup'])
    with closing(encrypted_connection(backup,record_keys.database_key(backup),readonly=True)) as db:
        verify_integrity(db)
        assert migration.logical_snapshot(db)==expected
    encrypted_before=path.read_bytes()
    assert migration.migrate_database(path)['status']=='already_encrypted'
    assert path.read_bytes()==encrypted_before
    assert not list(tmp_path.glob('plain.db.encrypting-*'))


def test_runtime_never_opens_or_automatically_migrates_plaintext(tmp_path):
    store=create_entry_app(tmp_path/'encrypted.db').state.store
    path=tmp_path/'plain.db'; plain_copy(store,path)
    before=path.read_bytes()
    with pytest.raises(StorageError,match='plaintext'):
        create_entry_app(path)
    assert path.read_bytes()==before
    assert not record_keys.key_metadata_path(path).exists()


@pytest.mark.parametrize('problem',['metadata','key','wrong-key','malformed-metadata','missing-database'])
def test_missing_or_wrong_key_never_replaces_existing_history(tmp_path,problem):
    path=tmp_path/'records.db'; create_entry_app(path)
    metadata_path=record_keys.key_metadata_path(path)
    metadata=json.loads(metadata_path.read_text())
    vault=record_keys.system_keyring()
    if problem=='metadata': metadata_path.unlink()
    elif problem=='key': vault.entries.pop((record_keys.SERVICE,metadata['key_id']))
    elif problem=='wrong-key': vault.entries[record_keys.SERVICE,metadata['key_id']]='modus_db_key_'+secrets.token_hex(32)
    elif problem=='malformed-metadata': metadata_path.write_text('{"format":"private-canary"}')
    else: path.unlink()
    before=path.read_bytes() if path.exists() else None
    with pytest.raises(StorageError) as error:
        create_entry_app(path)
    assert 'private-canary' not in str(error.value)
    assert (path.read_bytes() if path.exists() else None)==before


def test_tampered_page_fails_before_any_startup_write(tmp_path):
    path=tmp_path/'records.db'; create_entry_app(path)
    data=bytearray(path.read_bytes()); data[5000]^=1; path.write_bytes(data)
    before=bytes(data)
    with pytest.raises((StorageError,ValueError)):
        create_entry_app(path)
    assert path.read_bytes()==before


def test_records_and_wal_pages_hide_canaries_and_use_memory_temp_storage(tmp_path):
    path=tmp_path/'records.db'; store=create_entry_app(path).state.store
    canary='AUTHORED_PRIVATE_STORAGE_CANARY_'+secrets.token_hex(8)
    with store.connect() as reader:
        assert reader.execute('PRAGMA temp_store').fetchone()[0]==2
        assert reader.execute('PRAGMA journal_mode=WAL').fetchone()[0]=='wal'
        reader.execute('BEGIN'); reader.execute('SELECT count(*) FROM runs').fetchone()
        with store.connect() as writer:
            writer.execute('INSERT INTO runs(created_at,data) VALUES(?,?)',('2026-11-04T00:00:00Z',json.dumps({'value':canary})))
        wal=Path(str(path)+'-wal')
        assert wal.is_file() and wal.stat().st_size>0
        assert canary.encode() not in wal.read_bytes()
        assert canary.encode() not in path.read_bytes()
    with store.connect() as db:
        assert canary in db.execute('SELECT data FROM runs ORDER BY id DESC LIMIT 1').fetchone()[0]
        verify_integrity(db)


def test_unavailable_os_vault_never_falls_back_to_file_keys(tmp_path,monkeypatch):
    class Unavailable:
        def set_password(self,*args): raise RuntimeError('PRIVATE_BACKEND_CANARY')
    monkeypatch.setattr(record_keys,'system_keyring',lambda:Unavailable())
    path=tmp_path/'records.db'
    with pytest.raises(StorageError) as error:
        create_entry_app(path)
    assert 'PRIVATE_BACKEND_CANARY' not in str(error.value)
    assert not path.exists() and not record_keys.key_metadata_path(path).exists()


def test_large_upload_does_not_spool_plaintext_to_disk(tmp_path,monkeypatch):
    import tempfile
    from fastapi.testclient import TestClient
    app=create_entry_app(tmp_path/'records.db')
    def forbidden(*args,**kwargs):
        pytest.fail('Accepted upload bytes must remain in memory')
    monkeypatch.setattr(tempfile.SpooledTemporaryFile,'rollover',forbidden)
    with TestClient(app) as client:
        response=client.post('/api/imports/preview',data={'synthetic_confirmed':'true'},
            files={'file':('unaccepted.json',b'AUTHORED_PRIVATE_UPLOAD\n'*70000,'application/json')})
    assert response.status_code==422


def test_failed_atomic_replace_preserves_plain_source_and_encrypted_recovery(tmp_path,monkeypatch):
    store=create_entry_app(tmp_path/'encrypted.db').state.store
    path=tmp_path/'plain.db'; expected=plain_copy(store,path); before=path.read_bytes()
    def fail(*args): raise OSError('authored replace failure')
    with monkeypatch.context() as changes:
        changes.setattr(migration.os,'replace',fail)
        with pytest.raises(OSError,match='replace failure'):
            migration.migrate_database(path)
    assert path.read_bytes()==before
    backups=list(tmp_path.glob('plain.db.encrypted-backup-*'))
    backups=[p for p in backups if not p.name.endswith('.modus-vault.json')]
    assert len(backups)==1
    with closing(encrypted_connection(backups[0],record_keys.database_key(backups[0]),readonly=True)) as db:
        assert migration.logical_snapshot(db)==expected
    assert migration.migrate_database(path)['verified']==expected


def test_copy_verification_failure_never_replaces_source(tmp_path,monkeypatch):
    store=create_entry_app(tmp_path/'encrypted.db').state.store
    path=tmp_path/'plain.db'; plain_copy(store,path); before=path.read_bytes()
    actual=migration.logical_snapshot
    def unequal(db):
        value=actual(db)
        if '.encrypting-' in db.execute('PRAGMA database_list').fetchone()[2]: value['sha256']='mismatch'
        return value
    monkeypatch.setattr(migration,'logical_snapshot',unequal)
    with pytest.raises(StorageError,match='does not exactly match'):
        migration.migrate_database(path)
    assert path.read_bytes()==before


@pytest.mark.parametrize('busy',['lease','journal','foreign'])
def test_migration_refuses_busy_or_foreign_storage(tmp_path,busy):
    path=tmp_path/'plain.db'
    if busy=='foreign':
        with sqlite3.connect(path) as db: db.execute('CREATE TABLE foreign_data(value TEXT)')
    else:
        store=create_entry_app(tmp_path/'encrypted.db').state.store; plain_copy(store,path)
    before=path.read_bytes()
    if busy=='lease':
        with database_lock(path), pytest.raises(StorageError,match='in use'):
            migration.migrate_database(path)
    else:
        if busy=='journal': Path(str(path)+'-wal').write_bytes(b'uncheckpointed synthetic state')
        with pytest.raises(StorageError): migration.migrate_database(path)
    assert path.read_bytes()==before
    assert not record_keys.key_metadata_path(path).exists()

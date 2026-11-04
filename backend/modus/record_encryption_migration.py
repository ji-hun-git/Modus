"""Explicit stopped-service migration with verified encrypted recovery copies."""
from contextlib import closing
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import struct
import uuid

import sqlcipher3 as sqlite

from .local_files import secure_file
from .record_crypto import (StorageError, database_lock, encrypted_connection,
                            is_plaintext, ordinary_path, verify_integrity)
from .record_keys import database_key, key_metadata_path, write_new_metadata


def _identifier(value):
    return '"'+value.replace('"','""')+'"'


def logical_snapshot(db):
    """Bounded row-at-a-time digest, including exact BLOB bytes and row identities."""
    schema = [tuple(row) for row in db.execute(
        "SELECT type,name,tbl_name,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_stat%' ORDER BY type,name")]
    digest = sha256(json.dumps(schema,ensure_ascii=False,separators=(',',':')).encode())
    tables = {}
    for kind,name,_,sql in schema:
        if kind != 'table':
            continue
        quoted = _identifier(name)
        # Modus uses rowid tables. Retain a deterministic path for WITHOUT ROWID
        # tables so verification does not silently omit their primary keys.
        without_rowid = bool(sql and 'WITHOUT ROWID' in sql.upper())
        if without_rowid:
            primary = sorted((row[5],row[1]) for row in db.execute('PRAGMA table_info('+quoted+')') if row[5])
            order = ','.join(_identifier(column) for _,column in primary)
            query = 'SELECT * FROM '+quoted+' ORDER BY '+order
        else:
            query = 'SELECT rowid,* FROM '+quoted+' ORDER BY rowid'
        rows = 0
        digest.update(name.encode()+b'\x00')
        for row in db.execute(query):
            rows += 1
            digest.update(b'row\x00')
            for value in row:
                if value is None: tag,payload=b'n',b''
                elif isinstance(value,bytes): tag,payload=b'b',value
                elif isinstance(value,int): tag,payload=b'i',str(value).encode()
                elif isinstance(value,float): tag,payload=b'f',struct.pack('!d',value)
                else: tag,payload=b's',value.encode('utf-8')
                digest.update(tag+len(payload).to_bytes(8,'big')+payload)
        tables[name] = rows
    versions = {name:db.execute('PRAGMA '+name).fetchone()[0] for name in ('user_version','application_id')}
    digest.update(json.dumps(versions,sort_keys=True).encode())
    return {'sha256':digest.hexdigest(),'tables':tables,'versions':versions}


def _record_identity(db):
    try:
        metadata = dict(db.execute('SELECT key,value FROM record_store_meta'))
    except sqlite.DatabaseError:
        raise StorageError('Only an identified Modus record database can be migrated.') from None
    if metadata.get('application_id') != 'modus-records-v1' or metadata.get('schema_version') != '1':
        raise StorageError('The database has an incompatible application or schema identity.')


def _sync_file(path):
    # Windows FlushFileBuffers requires a writable handle even when all data
    # was already written through SQLite. Opening r+b does not alter bytes.
    with Path(path).open('r+b') as stream:
        os.fsync(stream.fileno())


def _sync_directory(path):
    if os.name != 'nt':
        descriptor = os.open(path,os.O_RDONLY | getattr(os,'O_DIRECTORY',0))
        try: os.fsync(descriptor)
        finally: os.close(descriptor)


def migrate_database(path):
    """No plaintext recovery copy, key export, automatic restore or fallback."""
    path = ordinary_path(path)
    if not path.is_file() or not path.stat().st_size:
        raise StorageError('Choose an existing Modus record database.')
    with database_lock(path,exclusive=True,timeout=1):
        if not is_plaintext(path):
            key = database_key(path)
            with closing(encrypted_connection(path,key,readonly=True)) as db:
                verify_integrity(db); _record_identity(db)
                snapshot = logical_snapshot(db)
            return {'status':'already_encrypted','verified':snapshot}
        # Do not discard hot journals or WAL data. A normal stopped Modus store
        # has none; recovery/checkpointing is a separate operator action.
        if any(Path(str(path)+suffix).exists() for suffix in ('-wal','-shm','-journal')):
            raise StorageError('Database journal files remain. Close the owning service cleanly before migration; no journal was removed.')
        nonce = uuid.uuid4().hex
        staged = ordinary_path(str(path)+'.encrypting-'+nonce)
        backup = ordinary_path(str(path)+'.encrypted-backup-'+nonce)
        db = sqlite.connect(path.as_uri()+'?mode=rw',uri=True,timeout=1)
        try:
            db.execute('PRAGMA temp_store=MEMORY')
            db.execute('PRAGMA synchronous=FULL')
            db.execute('PRAGMA locking_mode=EXCLUSIVE')
            db.execute('BEGIN EXCLUSIVE')
            _record_identity(db)
            if [tuple(row) for row in db.execute('PRAGMA integrity_check')] != [('ok',)]:
                raise StorageError('Source database integrity verification failed.')
            before = logical_snapshot(db)
            key = database_key(path,create=True)
            db.execute('ATTACH DATABASE ? AS encrypted KEY ?', (str(staged),"x'"+key.hex()+"'"))
            db.execute("SELECT sqlcipher_export('encrypted')").fetchone()
            for name,value in before['versions'].items():
                db.execute('PRAGMA encrypted.'+name+'='+str(int(value)))
            db.commit()
            db.execute('DETACH DATABASE encrypted')
            secure_file(staged)
            with closing(encrypted_connection(staged,key,readonly=True)) as candidate:
                verify_integrity(candidate)
                if logical_snapshot(candidate) != before:
                    raise StorageError('Encrypted copy does not exactly match the source. The source was not replaced.')
            # Keep a second, independently reopened encrypted copy before the
            # atomic replacement. Metadata is opaque, never a raw database key.
            with staged.open('rb') as source, backup.open('xb') as output:
                shutil.copyfileobj(source,output,1024*1024)
                output.flush(); os.fsync(output.fileno())
            secure_file(backup)
            write_new_metadata(key_metadata_path(backup),json.loads(key_metadata_path(path).read_text(encoding='utf-8')))
            with closing(encrypted_connection(backup,key,readonly=True)) as recovery:
                verify_integrity(recovery)
                if logical_snapshot(recovery) != before:
                    raise StorageError('Encrypted recovery verification failed. The source was not replaced.')
            if logical_snapshot(db) != before:
                raise StorageError('Source records changed during migration. The source was not replaced.')
            _sync_file(staged)
            db.close(); db = None
            if any(Path(str(path)+suffix).exists() for suffix in ('-wal','-shm','-journal')):
                raise StorageError('A database journal appeared. The source was not replaced.')
            os.replace(staged,path)
            _sync_directory(path.parent)
            return {'status':'encrypted','backup':str(backup),'verified':before}
        except sqlite.DatabaseError:
            raise StorageError('Database migration could not complete. Close Modus and verify the source before retrying.') from None
        finally:
            if db is not None: db.close()
            # Only our encrypted staging file can be removed. The source and
            # verified recovery copy are never deleted on an error.
            if staged.exists():
                ordinary_path(staged).unlink()

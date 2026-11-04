"""SQLCipher connections. No plaintext fallback, model authority or key logging."""
from contextlib import contextmanager
from pathlib import Path
import portalocker
import sqlcipher3 as sqlite

from .local_files import _ordinary, secure_file


class StorageError(ValueError):
    pass


def ordinary_path(path):
    path = Path(path).absolute()
    for parent in (path.parent, *path.parent.parents):
        if parent.exists():
            _ordinary(parent, directory=True)
    if path.exists() or path.is_symlink():
        _ordinary(path)
    return path


@contextmanager
def database_lock(path, *, exclusive=False, timeout=15):
    path = ordinary_path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    lock_path = ordinary_path(str(path)+'.modus-lock')
    flags = (portalocker.LOCK_EX if exclusive else portalocker.LOCK_SH) | portalocker.LOCK_NB
    try:
        with portalocker.Lock(str(lock_path), mode='a+b', flags=flags, timeout=timeout):
            secure_file(lock_path)
            yield
    except portalocker.exceptions.LockException:
        raise StorageError('Record storage is in use. Close Modus before migrating or restoring it.') from None


def is_plaintext(path):
    path = ordinary_path(path)
    if not path.exists():
        return False
    with path.open('rb') as stream:
        return stream.read(16) == b'SQLite format 3\x00'


def encrypted_connection(path, key, *, readonly=False, create=False, timeout=15):
    path = ordinary_path(path)
    if not isinstance(key, bytes) or len(key) != 32:
        raise StorageError('A 256-bit database key is required.')
    if is_plaintext(path):
        raise StorageError('Incompatible plaintext record database. Stop Modus and run the encryption migration first.')
    mode = 'ro' if readonly else ('rwc' if create else 'rw')
    db = sqlite.connect(path.as_uri()+'?mode='+mode, uri=True, timeout=timeout)
    try:
        # Only server-generated, fixed-length hex is interpolated. Never enable
        # SQL tracing/profiling on connections that carry keys.
        db.execute('PRAGMA key = "x\''+key.hex()+'\'"')
        version = db.execute('PRAGMA cipher_version').fetchone()
        if not version or not version[0].startswith('4.'):
            raise StorageError('The required SQLCipher runtime is unavailable.')
        db.execute('PRAGMA cipher_memory_security=ON')
        db.execute('PRAGMA temp_store=MEMORY')
        db.execute('PRAGMA foreign_keys=ON')
        db.execute('PRAGMA synchronous=FULL')
        db.execute('SELECT count(*) FROM sqlite_master').fetchone()
        db.row_factory = sqlite.Row
        if create:
            secure_file(path)
        return db
    except sqlite.DatabaseError as error:
        db.close()
        if getattr(error,'sqlite_errorcode',0) & 0xff in (sqlite.SQLITE_BUSY,sqlite.SQLITE_LOCKED):
            raise
        raise StorageError('The encrypted record database cannot be opened. Its key may be wrong or its data damaged.') from None
    except Exception:
        db.close()
        raise


def verify_integrity(db):
    if list(db.execute('PRAGMA cipher_integrity_check')):
        raise StorageError('Encrypted record integrity verification failed.')
    if [tuple(row) for row in db.execute('PRAGMA integrity_check')] != [('ok',)]:
        raise StorageError('Record database integrity verification failed.')
    if list(db.execute('PRAGMA foreign_key_check')):
        raise StorageError('Record relationships failed integrity verification.')

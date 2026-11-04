"""Per-database random keys in explicitly selected native OS credential storage."""
import json
import os
from pathlib import Path
import re
import secrets
import sys
import uuid

from .local_files import secure_file
from .record_crypto import StorageError, ordinary_path

SERVICE = 'modus-records-storage-v1'
FORMAT = 'modus-record-key-v1'


def system_keyring():
    # Configurable/default and plaintext alternative keyrings are not accepted.
    try:
        if sys.platform == 'win32':
            from keyring.backends.Windows import WinVaultKeyring
            backend = WinVaultKeyring()
        elif sys.platform == 'darwin':
            from keyring.backends.macOS import Keyring
            backend = Keyring()
        elif sys.platform == 'linux':
            from keyring.backends.SecretService import Keyring
            backend = Keyring()
        else:
            raise StorageError('This operating system has no supported secure key store.')
        if backend.priority <= 0:
            raise StorageError('Unlock the OS credential store before opening Modus.')
        return backend
    except Exception:
        raise StorageError('Secure OS credential storage is unavailable. Unlock it before opening Modus; no plaintext fallback is used.') from None


def key_metadata_path(path):
    return ordinary_path(str(Path(path).absolute())+'.modus-vault.json')


def write_new_metadata(path, metadata):
    path = ordinary_path(path)
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os,'O_NOFOLLOW',0)
    with os.fdopen(os.open(path,flags,0o600),'w',encoding='utf-8') as stream:
        json.dump(metadata,stream,sort_keys=True)
        stream.flush(); os.fsync(stream.fileno())
    secure_file(path)


def database_key(path, *, create=False):
    """Caller holds the exclusive database lease when allowing key creation.

    Metadata contains only an opaque key ID. Missing/invalid existing material
    never causes key rotation, replacement of history or a plaintext open.
    """
    metadata_path = key_metadata_path(path)
    backend = system_keyring()
    try:
        if metadata_path.exists():
            if metadata_path.stat().st_size > 1024:
                raise StorageError('Invalid database key metadata.')
            metadata = json.loads(metadata_path.read_text(encoding='utf-8'))
            if (not isinstance(metadata,dict) or set(metadata) != {'format','key_id'}
                    or metadata['format'] != FORMAT or not isinstance(metadata['key_id'],str)
                    or not re.fullmatch('[0-9a-f]{32}',metadata['key_id'])):
                raise StorageError('Invalid database key metadata.')
            stored = backend.get_password(SERVICE,metadata['key_id'])
            if not isinstance(stored,str) or not re.fullmatch(r'modus_db_key_[0-9a-f]{64}',stored):
                raise StorageError('The database key is unavailable. Restore its OS key-store entry; existing records were not changed.')
            return bytes.fromhex(stored.removeprefix('modus_db_key_'))
        if not create:
            raise StorageError('Database key metadata is missing. Existing records were not changed.')
        metadata = {'format':FORMAT,'key_id':uuid.uuid4().hex}
        key = secrets.token_bytes(32)
        stored = 'modus_db_key_'+key.hex()
        backend.set_password(SERVICE,metadata['key_id'],stored)
        if backend.get_password(SERVICE,metadata['key_id']) != stored:
            raise StorageError('The OS credential store did not retain the database key.')
        write_new_metadata(metadata_path,metadata)
        return key
    except StorageError:
        raise
    except Exception:
        raise StorageError('The database key could not be loaded or created. Existing records were not changed.') from None

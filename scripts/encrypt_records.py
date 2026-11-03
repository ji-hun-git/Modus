"""Explicit local migration; never reads model credentials or evaluation files."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from offline_environment import offline_environment

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))


def main():
    parser=argparse.ArgumentParser(description='Encrypt a stopped Modus record store and verify an encrypted recovery copy.')
    parser.add_argument('database',type=Path)
    parser.add_argument('--execute',action='store_true',help='Confirm the owning service has been stopped')
    parser.add_argument('--child',action='store_true',help=argparse.SUPPRESS)
    args=parser.parse_args()
    if not args.execute:
        parser.error('Stop the owning service, then pass --execute. No database was changed.')
    path=args.database.absolute()
    if any(part.lower() in {'eval','evaluation'} or 'heldout' in part.lower() or 'holdout' in part.lower() for part in path.parts):
        parser.error('Protected evaluation paths cannot be migrated by this command.')
    if not args.child:
        python=ROOT/'.venv'/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
        if not python.is_file():
            parser.error('Run python scripts/setup_entry.py first.')
        return subprocess.run([str(python),str(Path(__file__).resolve()),str(path),'--execute','--child'],
                              cwd=ROOT,env=offline_environment()).returncode
    clean=offline_environment()
    os.environ.clear(); os.environ.update(clean)
    from modus.record_crypto import StorageError
    from modus.record_encryption_migration import migrate_database
    try:
        print(json.dumps(migrate_database(path),indent=2))
    except (StorageError,OSError) as error:
        print('Encryption migration stopped: '+str(error),file=sys.stderr)
        return 1
    return 0


if __name__=='__main__':
    raise SystemExit(main())

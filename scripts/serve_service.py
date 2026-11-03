"""Run the checked offline development build without reading release/eval gates."""
import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import re
import subprocess
import sys

from check_service import inputs, build_inputs, protected
from offline_environment import offline_environment, local_connection
from private_storage import secure_runtime_directory
from local_access_file import publish_access_file

ROOT = Path(__file__).resolve().parents[1]


def verify_service(root=ROOT):
    report = json.loads((root/'release/service-check/report.json').read_text(encoding='utf-8'))
    if report.get('status') != 'passed' or report.get('checks') != {
            'backend':0, 'frontend-tests':0, 'frontend-build':0}:
        raise ValueError('Run python scripts/check_service.py successfully first')
    if report.get('source_sha256') != inputs(root) or report.get('build_sha256') != build_inputs(root):
        raise ValueError('Source or build changed. Run python scripts/check_service.py again')


def configure_offline():
    clean_environment = offline_environment()
    os.environ.clear()
    os.environ.update(clean_environment)
    os.environ['MODUS_ENTRY_PROVIDER'] = 'offline'


def runtime_directory(root=ROOT, rehearsal=None):
    if rehearsal is None:
        return root/'release/offline-service'
    if not isinstance(rehearsal, str) or not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,47}', rehearsal):
        raise ValueError('Use a rehearsal name of 1–48 lowercase letters, numbers or hyphens, starting with a letter or number.')
    return root/'release'/('rehearsal-'+rehearsal)


@contextmanager
def workspace_lease(root=ROOT, rehearsal=None):
    # The parent launcher must run with plain Python before delegating to .venv.
    from modus.record_crypto import database_lock, ordinary_path
    directory = runtime_directory(root, rehearsal)
    ordinary_path(directory/'records.db')  # Validate ancestors before changing permissions.
    secure_runtime_directory(directory)
    # Keep a second launcher from replacing the access file for a live service.
    # This lease does not replace the database's own read/write/migration leases.
    with database_lock(directory/'service', exclusive=True, timeout=0):
        yield directory


def child(port, ui_port=None, rehearsal=None):
    configure_offline()
    with workspace_lease(ROOT, rehearsal) as directory:
        run_server(port, ui_port, directory)


def run_server(port, ui_port, directory):
    os.environ['MODUS_ENTRY_DB_PATH'] = str(directory/'records.db')
    if os.name != 'nt':
        os.umask(0o077)  # New SQLite journals and databases inherit owner-only access.

    def guard(event, args):
        if event == 'open' and args and isinstance(args[0], (str, bytes, os.PathLike)):
            path = Path(os.fsdecode(args[0])).absolute()
            try:
                name = path.relative_to(ROOT).as_posix()
            except ValueError:
                return
            if protected(name):
                raise PermissionError('Offline service preview excludes evaluation and secret files')
        if event == 'socket.connect' and not local_connection(args[0], args[1]):
            raise PermissionError('Offline service preview forbids external network')

    sys.addaudithook(guard)
    sys.path.insert(0, str(ROOT/'backend'))
    from modus_entry.app import app
    access_file = publish_access_file(app, directory, port, ui_port=ui_port)
    print(f'Open this file in the Modus unlock screen: {access_file}', flush=True)
    import uvicorn
    uvicorn.run(app, host='127.0.0.1', port=port, proxy_headers=False, access_log=False, server_header=False)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8011, choices=range(1024,65536), metavar='1024..65535')
    parser.add_argument('--ui-port', type=int, choices=range(1024,65536), metavar='1024..65535',
                        help='Bind access to a local Vite proxy port instead of the backend port')
    parser.add_argument('--child', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--rehearsal', metavar='NAME',
                        help='Use a separate persistent encrypted demo workspace; a new name starts a fresh take without resetting another store')
    args = parser.parse_args()
    try:
        directory = runtime_directory(ROOT, args.rehearsal)
    except ValueError as error:
        parser.error(str(error))
    verify_service()
    if args.child:
        child(args.port, args.ui_port, args.rehearsal)
        return
    python = ROOT/'.venv'/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
    if not python.is_file():
        raise ValueError('Run python scripts/setup_entry.py first')
    print(f'Checked offline development preview: http://127.0.0.1:{args.port}/ (not a final release qualification)', flush=True)
    print(f'Record workspace: {directory}', flush=True)
    command = [str(python), str(Path(__file__).resolve()), '--child', '--port', str(args.port)]
    if args.ui_port is not None:
        command += ['--ui-port', str(args.ui_port)]
    if args.rehearsal is not None:
        command += ['--rehearsal', args.rehearsal]
    subprocess.run(command,
                   cwd=ROOT, env=offline_environment(), check=True)


if __name__ == '__main__':
    main()

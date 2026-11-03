"""Run the checked offline development build without reading release/eval gates."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

from check_service import inputs, build_inputs, protected
from offline_environment import offline_environment
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


def child(port, ui_port=None):
    configure_offline()
    os.environ['MODUS_ENTRY_DB_PATH'] = str(ROOT/'release/offline-service/records.db')
    secure_runtime_directory(ROOT/'release/offline-service')
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
        if event == 'socket.connect' and (not isinstance(args[1], tuple) or args[1][0] not in ('127.0.0.1','::1','localhost')):
            raise PermissionError('Offline service preview forbids external network')

    sys.addaudithook(guard)
    sys.path.insert(0, str(ROOT/'backend'))
    from modus_entry.app import app
    access_file = publish_access_file(app, ROOT/'release/offline-service', port, ui_port=ui_port)
    print(f'Open this file in the Modus unlock screen: {access_file}', flush=True)
    import uvicorn
    uvicorn.run(app, host='127.0.0.1', port=port, proxy_headers=False, access_log=False, server_header=False)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8011, choices=range(1024,65536), metavar='1024..65535')
    parser.add_argument('--ui-port', type=int, choices=range(1024,65536), metavar='1024..65535',
                        help='Bind access to a local Vite proxy port instead of the backend port')
    parser.add_argument('--child', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    verify_service()
    if args.child:
        child(args.port, args.ui_port)
        return
    python = ROOT/'.venv'/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
    if not python.is_file():
        raise ValueError('Run python scripts/setup_entry.py first')
    print(f'Checked offline development preview: http://127.0.0.1:{args.port}/ (not a final release qualification)', flush=True)
    command = [str(python), str(Path(__file__).resolve()), '--child', '--port', str(args.port)]
    if args.ui_port is not None:
        command += ['--ui-port', str(args.ui_port)]
    subprocess.run(command,
                   cwd=ROOT, env=offline_environment(), check=True)


if __name__ == '__main__':
    main()

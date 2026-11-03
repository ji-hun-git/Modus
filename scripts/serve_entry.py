"""Serve the independent, verified record application on loopback."""
import argparse
import os
from pathlib import Path
import subprocess
import sys
from entry_release import assert_current
from local_access_file import publish_access_file

root = Path(__file__).resolve().parents[1]


def run_server(port):
    sys.path.insert(0, str(root/'backend'))
    from modus_entry.app import app
    # Keep the established database path; only the access file is new.
    access_file = publish_access_file(app, root/'release/entry-service-access', port)
    print(f'Open this file in the Modus unlock screen: {access_file}', flush=True)
    import uvicorn
    uvicorn.run(app, host='127.0.0.1', port=port, proxy_headers=False,
                access_log=False, server_header=False)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8011, choices=range(1024,65536), metavar='1024..65535')
    parser.add_argument('--child', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    python = root / '.venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    if not python.exists():
        sys.exit('Run python scripts/setup_entry.py first')
    assert_current(root, require_build=True)
    if args.child:
        run_server(args.port)
        return
    print(f'Modus Records: http://127.0.0.1:{args.port}', flush=True)
    subprocess.run([str(python), str(Path(__file__).resolve()), '--child', '--port', str(args.port)], cwd=root, check=True)


if __name__ == '__main__':
    main()

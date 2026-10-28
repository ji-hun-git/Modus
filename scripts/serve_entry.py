"""Serve the independent, verified record application on loopback."""
import argparse
import os
from pathlib import Path
import subprocess
import sys
from entry_release import assert_current

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--port', type=int, default=8011)
args = parser.parse_args()
python = root / '.venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
if not python.exists():
    sys.exit('Run python scripts/setup_entry.py first')
assert_current(root, require_build=True)
print(f'Modus Records: http://127.0.0.1:{args.port}', flush=True)
subprocess.run([str(python), '-m', 'uvicorn', 'modus_entry.app:app', '--host', '127.0.0.1', '--port', str(args.port)], cwd=root / 'backend', check=True)

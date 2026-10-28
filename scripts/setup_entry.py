"""Install only the independent entry's locked local dependencies."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
from offline_environment import offline_environment

root = Path(__file__).resolve().parents[1]
venv = root / '.venv'
python = venv / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
uv = shutil.which('uv')
env = offline_environment()
if not python.exists():
    subprocess.run([uv, 'venv', str(venv)] if uv else [sys.executable, '-m', 'venv', str(venv)], check=True, env=env)
requirements = root / 'backend/requirements.lock.txt'
subprocess.run([uv, 'pip', 'install', '--system-certs', '--python', str(python), '-r', str(requirements)] if uv else [str(python), '-m', 'pip', 'install', '-r', str(requirements)], check=True, env=env)
npm = shutil.which('npm.cmd' if os.name == 'nt' else 'npm')
if not npm:
    sys.exit('Install Node.js with npm, then rerun setup.')
subprocess.run([npm, 'ci'], cwd=root / 'entry/frontend', check=True, env=env)
print('Ready. Run python scripts/check_entry.py, then python scripts/serve_entry.py')

"""Verify the independent entry in the workspace or a clean extracted package."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from entry_release import inputs, build_hashes, STAMP, identity

root = Path(__file__).resolve().parents[1]
python = root / '.venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
if not python.exists():
    python = Path(sys.executable)  # Explicit current interpreter supports extraction verification.
npm = shutil.which('npm.cmd' if os.name == 'nt' else 'npm')
if not npm:
    sys.exit('Install Node.js/npm first')
stamp = root / STAMP
stamp.unlink(missing_ok=True)
before = inputs(root)
tests = sorted(str(p.relative_to(root / 'backend')) for p in (root / 'backend/tests').glob('test_entry*.py'))
for name in ('test_record_store.py', 'test_record_history.py', 'test_record_units.py', 'test_history_ingest.py', 'test_history_audit.py', 'test_record_extraction.py', 'test_benchmark_harness.py', 'test_extraction_layouts.py', 'test_local_ocr.py', 'test_development_comparison.py', 'test_ontology.py', 'test_record_retrieval.py', 'test_ontology_rag_evaluation.py'):
    if (root / 'backend/tests' / name).is_file():
        tests.append('tests/' + name)
if not tests:
    sys.exit('Entry tests are missing')
env = {**os.environ, 'MODUS_PROVIDER': 'offline', 'MODEL_API_KEY': ''}
commands = [('tests', [str(python), '-m', 'pytest', '-q', *tests], root / 'backend'),
    ('evaluation', [str(python), str(root / 'scripts/evaluate_entry.py')], root),
    ('frontend_tests', [npm, 'test'], root / 'entry/frontend'),
    ('frontend_build', [npm, 'run', 'build'], root / 'entry/frontend')]
for _, command, cwd in commands:
    subprocess.run(command, cwd=cwd, env=env, check=True)
if inputs(root) != before:
    raise ValueError('Entry inputs changed during verification')
build = build_hashes(root)
if 'entry/frontend/dist/index.html' not in build:
    raise ValueError('Entry frontend build is missing')
stamp.parent.mkdir(parents=True, exist_ok=True)
stamp.write_text(json.dumps({'format': 'modus-entry-gate-v1', 'status': 'passed',
    'checked_at': datetime.now(timezone.utc).isoformat(), 'bundle_id': identity(before),
    'checks': {name: 'passed' for name, _, _ in commands}, 'files_sha256': before, 'build_sha256': build,
    'scope': 'Local deterministic/mocked tests and frontend build; live Meta and organizer eligibility unverified.'}, indent=2) + '\n', encoding='utf-8')
print('Independent entry gate passed.')

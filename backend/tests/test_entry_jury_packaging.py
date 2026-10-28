"""Public evaluator integration, using a temporary package and mocked gate only."""
import json
from pathlib import Path
import runpy
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from entry_release import inputs


JURY_FILES = {
    'eval/judges/' + name for name in (
        '__init__.py', 'aggregate.py', 'budget.py', 'cli.py', 'code_checks.py',
        'prompts.py', 'repro.py', 'runner.py', 'schema.py', 'transport.py',
        'models.yaml', 'PROTOCOL.md',
    )
} | {'backend/tests/' + name for name in (
    'test_jury_harness.py', 'test_jury_aggregation.py', 'test_jury_code_checks.py', 'test_jury_transport.py',
)}


def test_public_evaluator_allowlist_is_exact_and_hash_bound(tmp_path):
    manifest = json.loads((ROOT / 'entry/config/source_manifest.json').read_text(encoding='utf-8'))
    selected = [row for row in manifest['files'] if row['source'].startswith('eval/judges/')
                or row['source'].startswith('backend/tests/test_jury')]
    assert {row['source'] for row in selected} == JURY_FILES
    assert len(selected) == len(JURY_FILES)
    assert all(row['behavior'] and row['source'] == row['destination'] for row in selected)
    target = tmp_path / 'entry/config/source_manifest.json'
    target.parent.mkdir(parents=True)
    target.write_text(json.dumps({'files': selected}), encoding='utf-8')
    for row in selected:
        path = tmp_path / row['source']
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('synthetic package input\n', encoding='utf-8')
    before = inputs(tmp_path)
    assert set(before) == JURY_FILES
    for name in ('eval/judges/runner.py', 'eval/judges/models.yaml', 'eval/judges/PROTOCOL.md'):
        (tmp_path / name).write_text('changed synthetic package input\n', encoding='utf-8')
        assert inputs(tmp_path)[name] != before[name]


def test_entry_gate_runs_packaged_jury_tests_with_no_provider_credentials(tmp_path, monkeypatch):
    # Run the actual gate script against only newly authored temporary inputs.
    script = tmp_path / 'scripts/check_entry.py'
    script.parent.mkdir()
    shutil.copyfile(ROOT / 'scripts/check_entry.py', script)
    tests = tmp_path / 'backend/tests'
    tests.mkdir(parents=True)
    expected = ['test_entry_sample.py', 'test_jury_harness.py', 'test_jury_aggregation.py', 'test_jury_code_checks.py']
    for name in expected:
        (tests / name).write_text('# synthetic selected test\n', encoding='utf-8')
    config = tmp_path / 'entry/config/source_manifest.json'
    config.parent.mkdir(parents=True)
    config.write_text(json.dumps({'files': []}), encoding='utf-8')
    credentials = ('MODEL_API_KEY', 'MODUS_META_KEY', 'ANTHROPIC_API_KEY', 'OPENAI_API_KEY')
    for name in credentials:
        monkeypatch.setenv(name, 'artificial-public-integration-canary')
    calls = []
    def child(command, **kwargs):
        assert all(name not in kwargs['env'] for name in credentials)
        assert kwargs['env']['MODUS_PROVIDER'] == 'offline'
        assert kwargs['env']['PYTHON_DOTENV_DISABLED'] == '1'
        calls.append(command)
        if command[-2:] == ['run', 'build']:
            output = tmp_path / 'entry/frontend/dist/index.html'
            output.parent.mkdir(parents=True)
            output.write_text('synthetic built page', encoding='utf-8')
    monkeypatch.setattr(shutil, 'which', lambda _: 'synthetic-npm')
    monkeypatch.setattr(subprocess, 'run', child)
    runpy.run_path(str(script), run_name='__main__')
    assert len(calls) == 4
    assert calls[0][1:4] == ['-m', 'pytest', '-q']
    assert {Path(name).as_posix() for name in calls[0][4:]} == {'tests/' + name for name in expected}
    assert json.loads((tmp_path / 'entry/eval/release-gate.json').read_text())['status'] == 'passed'

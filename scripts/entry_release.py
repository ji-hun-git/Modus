"""Exact entry allowlist and local tested-source/build gate. Not a signature."""
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from modus.bundle import hashes, identity

STAMP = 'entry/eval/release-gate.json'


def entries(root=ROOT):
    root = Path(root).resolve()
    manifest = json.loads((root / 'entry/config/source_manifest.json').read_text(encoding='utf-8'))
    for item in manifest['files']:
        path = root / item['source']
        if not path.exists():
            path = root / item['destination']  # Root readme/env mapping in a clean extract.
        target = Path(item['destination'])
        if path.is_symlink() or not path.resolve().is_relative_to(root) or target.is_absolute() or '..' in target.parts:
            raise ValueError('Entry manifest path is outside the project')
        if not path.is_file():
            raise ValueError('Missing entry source: ' + item['source'])
        yield path, target, item.get('behavior', False)


def inputs(root=ROOT):
    root = Path(root)
    return {target.as_posix(): next(iter(hashes(root, [path]).values()))
            for path, target, behavior in entries(root) if behavior}


def build_hashes(root=ROOT):
    root = Path(root)
    return hashes(root, [p for p in (root / 'entry/frontend/dist').rglob('*') if p.is_file()])


def assert_current(root=ROOT, require_build=False):
    root = Path(root)
    try:
        report = json.loads((root / STAMP).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        raise ValueError('Run python scripts/check_entry.py before serving or packaging') from None
    current = inputs(root)
    if report.get('status') != 'passed' or report.get('checks') != {'tests': 'passed', 'evaluation': 'passed', 'frontend_tests': 'passed', 'frontend_build': 'passed'} or report.get('files_sha256') != current or report.get('bundle_id') != identity(current):
        raise ValueError('Entry sources differ from the tested version; rerun scripts/check_entry.py')
    if require_build and (not report.get('build_sha256') or report['build_sha256'] != build_hashes(root)):
        raise ValueError('Entry build differs from the tested version; rerun scripts/check_entry.py')
    return report

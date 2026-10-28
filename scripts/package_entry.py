"""Create a fresh, bounded entry directory from an exact allowlist. Never push."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
from entry_release import ROOT, entries, assert_current, STAMP


def package(destination, include_build=False):
    assert_current(ROOT, require_build=include_build)
    destination = Path(destination).resolve()
    if destination.exists():
        raise ValueError('Choose a new destination; no existing checkout is overwritten')
    selected = list(entries(ROOT))
    selected += [(ROOT / name, Path(name), False) for name in (STAMP, 'entry/eval/results.json')]
    if include_build:
        selected += [(p, p.relative_to(ROOT), False) for p in (ROOT / 'entry/frontend/dist').rglob('*') if p.is_file()]
    names = [rel.as_posix() for _, rel, _ in selected]
    if len(names) != len(set(names)):
        raise ValueError('Duplicate entry export destination')
    destination.mkdir(parents=True)
    manifest = {}
    for path, relative, _ in selected:
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        manifest[relative.as_posix()] = hashlib.sha256(target.read_bytes()).hexdigest()
    (destination / 'PACKAGE_MANIFEST.json').write_text(json.dumps({'format': 'modus-record-entry-v1', 'files_sha256': manifest,
        'scope': 'Independent synthetic record-reconciliation candidate; eligibility/publication unconfirmed.'}, indent=2) + '\n', encoding='utf-8')
    assert_current(destination, require_build=include_build)
    print(json.dumps({'status': 'prepared', 'files': len(manifest), 'destination': str(destination), 'published': False}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--include-build', action='store_true')
    args = parser.parse_args()
    package(args.out, args.include_build)

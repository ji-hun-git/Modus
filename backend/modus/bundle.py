"""Content identity for the loaded research runtime; no credentials or records.

Source text hashes normalize CRLF to LF for cross-platform Git checkouts.
This is provenance, not a signature, clinical validation or exact model replay.
Restart after backend/prompt/config edits: the process captures its bundle once.
"""
import hashlib
import json
from importlib import metadata
from pathlib import Path
import platform

ROOT = Path(__file__).resolve().parents[2]
TEXT_SUFFIXES = {'.py', '.md', '.json', '.jsonl', '.ts', '.tsx', '.css', '.html',
                 '.txt', '.toml', '.yaml', '.yml', '.csv', '.jinja'}


def content_hash(path):
    raw = path.read_bytes()
    if path.suffix.lower() in TEXT_SUFFIXES:
        raw = raw.replace(b'\r\n', b'\n')
    return hashlib.sha256(raw).hexdigest()


def identity(value):
    return 'sha256:' + hashlib.sha256(json.dumps(value, sort_keys=True,
        separators=(',', ':'), ensure_ascii=False).encode('utf-8')).hexdigest()


def hashes(root, paths):
    result = {}
    for path in sorted(set(paths)):
        if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
            raise ValueError('Bundle input must be a regular file inside the project')
        if path.is_file():
            result[path.relative_to(root).as_posix()] = content_hash(path)
    return result


def source_bundle(root=ROOT):
    root = Path(root)
    paths = [*(root / 'backend/modus').rglob('*.py'),
             *(root / 'prompts').glob('*.md'), *(root / 'prompts').glob('*.json')]
    paths += [root / name for name in ('config/agent-policy.json', 'config/models.json',
                                      'backend/requirements.lock.txt', 'config/teleocr.json',
                                      'scripts/teleocr_runtime.py', 'scripts/teleocr_document_worker.py',
                                      'scripts/teleocr_assets.py', 'scripts/requirements-ocr.lock.txt') if (root / name).is_file()]
    inputs = hashes(root, paths)
    return {'format': 'modus-runtime-bundle-v1', 'id': identity(inputs), 'files_sha256': inputs,
            'hash_policy': 'SHA256; text CRLF normalized to LF; relative POSIX paths'}


PROCESS_BUNDLE = source_bundle()


def installed_environment():
    dependencies = {}
    for line in (ROOT / 'backend/requirements.lock.txt').read_text(encoding='utf-8').splitlines():
        if not line.strip() or line.startswith('#'):
            continue
        name = line.split('==', 1)[0]
        try:
            dependencies[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            dependencies[name] = None
    return {'python': platform.python_version(), 'platform': platform.system(), 'dependencies': dependencies}

from datetime import datetime, timezone
import json
from pathlib import Path
from uuid import uuid4
from modus.bundle import hashes, identity, installed_environment
from modus.policy import POLICY

ROOT = Path(__file__).resolve().parents[2]

def runtime_bundle(root=ROOT):
    """Use the entry allowlist as the source of truth for runtime Python files.

    The former hand-maintained list omitted the current two-pass extractor,
    page preparation and generic history import. Tests and research-only code
    are deliberately outside this runtime identity; the release gate covers
    test and UI inputs separately.
    """
    root = Path(root)
    manifest = json.loads((root / 'entry/config/source_manifest.json').read_text(encoding='utf-8'))
    paths = [root / item['source'] for item in manifest['files']
        if item.get('behavior') and item['source'].endswith('.py')
        and item['source'].startswith(('backend/modus/', 'backend/modus_entry/'))]
    paths += [root / name for name in ('prompts/extract.md', 'entry/prompts/records.md',
        'entry/prompts/history.md', 'config/agent-policy.json', 'backend/requirements.lock.txt',
        'config/teleocr.json', 'scripts/teleocr_runtime.py', 'scripts/teleocr_document_worker.py',
        'scripts/teleocr_assets.py', 'scripts/requirements-ocr.lock.txt')]
    if any(not path.is_file() for path in paths):
        raise ValueError('An allowlisted entry runtime input is missing')
    return hashes(root, paths)


BUNDLE_ID = identity(runtime_bundle())
ENVIRONMENT = installed_environment()


def execution_context(mode, model=None):
    return {'run_id': str(uuid4()), 'bundle_id': BUNDLE_ID,
        'config_id': identity({'mode': mode, 'model': model, 'policy': POLICY.model_dump(), 'runtime': ENVIRONMENT}),
        'started_at': datetime.now(timezone.utc).isoformat(), 'mode': mode, 'requested_model': model,
        'model_version_basis': 'mutable provider identifier; immutable version unverified' if model else 'no model call',
        'runtime': ENVIRONMENT}

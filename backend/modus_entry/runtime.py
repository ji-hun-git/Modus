from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from modus.bundle import hashes, identity, installed_environment
from modus.policy import POLICY

ROOT = Path(__file__).resolve().parents[2]
SHARED = ('__init__.py', 'record_models.py', 'record_store.py', 'record_conflicts.py', 'ontology.py', 'record_retrieval.py', 'local_ocr.py', 'ocr_text.py',
          'ingest.py', 'temporal.py', 'policy.py', 'bundle.py', 'provider.py', 'extraction.py')
paths = [ROOT / 'backend/modus' / name for name in SHARED]
paths += list((ROOT / 'backend/modus_entry').glob('*.py'))
paths += [ROOT / 'prompts/extract.md', ROOT / 'entry/prompts/records.md', ROOT / 'config/agent-policy.json', ROOT / 'backend/requirements.lock.txt']
paths += [ROOT / name for name in ('config/teleocr.json', 'scripts/teleocr_runtime.py',
    'scripts/teleocr_document_worker.py', 'scripts/teleocr_assets.py', 'scripts/requirements-ocr.lock.txt')]
BUNDLE_ID = identity(hashes(ROOT, paths))
ENVIRONMENT = installed_environment()


def execution_context(mode, model=None):
    return {'run_id': str(uuid4()), 'bundle_id': BUNDLE_ID,
        'config_id': identity({'mode': mode, 'model': model, 'policy': POLICY.model_dump(), 'runtime': ENVIRONMENT}),
        'started_at': datetime.now(timezone.utc).isoformat(), 'mode': mode, 'requested_model': model,
        'model_version_basis': 'mutable provider identifier; immutable version unverified' if model else 'no model call',
        'runtime': ENVIRONMENT}

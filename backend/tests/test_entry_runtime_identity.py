"""Runtime provenance follows all allowlisted code used by real ingestion."""
from pathlib import Path
import shutil

import pytest

from modus.bundle import identity
from modus_entry.runtime import ROOT, runtime_bundle


def test_current_ingestion_and_guard_are_bound_but_research_app_is_not():
    files = runtime_bundle()
    for name in ('record_extraction.py', 'record_extraction_models.py',
                 'record_document_input.py', 'history_ingest.py'):
        assert 'backend/modus/' + name in files
    assert 'backend/modus_entry/document_guard.py' in files
    assert 'backend/modus/app.py' not in files
    assert not any(name.startswith('backend/tests/') for name in files)
    assert not any(name.startswith('eval/judges/') for name in files)


@pytest.mark.parametrize('name', ['record_extraction.py', 'record_document_input.py', 'history_ingest.py'])
def test_shared_runtime_change_invalidates_identity_in_an_isolated_copy(tmp_path, name):
    files = runtime_bundle()
    for relative in [*files, 'entry/config/source_manifest.json']:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
    before = identity(runtime_bundle(tmp_path))
    target = tmp_path / 'backend/modus' / name
    target.write_text(target.read_text(encoding='utf-8') + '\n# isolated provenance mutation\n', encoding='utf-8')
    assert identity(runtime_bundle(tmp_path)) != before
    assert identity(runtime_bundle()) == before

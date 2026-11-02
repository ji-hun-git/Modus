"""Offline preview cannot present a stale source or frontend as checked."""
import json
from pathlib import Path
import sys
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'scripts'))
from check_service import inputs, build_inputs
from serve_service import verify_service, configure_offline


@pytest.fixture
def checked_preview(tmp_path):
    (tmp_path/'entry/config').mkdir(parents=True)
    (tmp_path/'entry/frontend/dist').mkdir(parents=True)
    (tmp_path/'release/service-check').mkdir(parents=True)
    (tmp_path/'source.py').write_text('checked source')
    (tmp_path/'entry/frontend/dist/index.html').write_text('<main>checked build</main>')
    (tmp_path/'entry/config/source_manifest.json').write_text(json.dumps({'files':[
        {'source':'source.py','destination':'source.py','behavior':True}]}))
    report = {'status':'passed','checks':{'backend':0,'frontend-tests':0,'frontend-build':0},
              'source_sha256':inputs(tmp_path),'build_sha256':build_inputs(tmp_path)}
    (tmp_path/'release/service-check/report.json').write_text(json.dumps(report))
    return tmp_path


def test_checked_preview_without_release_or_evaluation_artifacts(checked_preview):
    verify_service(checked_preview)


def test_direct_child_mode_removes_inherited_credentials(monkeypatch):
    import os
    keys = ('MODUS_META_KEY','MODEL_API_KEY','ANTHROPIC_API_KEY','OPENAI_API_KEY')
    for key in keys:
        monkeypatch.setenv(key, 'synthetic-test-canary')
    configure_offline()
    assert all(key not in os.environ for key in keys)
    assert os.environ['MODUS_PROVIDER'] == os.environ['MODUS_ENTRY_PROVIDER'] == 'offline'


@pytest.mark.parametrize('path', ['source.py','entry/frontend/dist/index.html','entry/frontend/dist/new.js'])
def test_changed_source_or_build_is_rejected(checked_preview, path):
    (checked_preview/path).write_text('not checked')
    with pytest.raises(ValueError, match='changed'):
        verify_service(checked_preview)


def test_passing_label_cannot_hide_failed_tests(checked_preview):
    path=checked_preview/'release/service-check/report.json'
    report=json.loads(path.read_text())
    report['checks']['backend']=1
    path.write_text(json.dumps(report))
    with pytest.raises(ValueError, match='successfully'):
        verify_service(checked_preview)

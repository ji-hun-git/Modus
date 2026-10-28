"""Only artificial key canaries are used; no network or real credential file."""
import asyncio
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from modus import provider

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from offline_environment import MODEL_CREDENTIALS, offline_environment


def test_test_collection_has_cleared_every_model_credential():
    assert all(os.environ.get(name) == '' for name in MODEL_CREDENTIALS)
    assert os.environ['MODUS_PROVIDER'] == 'offline'
    assert os.environ['PYTHON_DOTENV_DISABLED'] == '1'


def test_clean_child_environment_removes_all_aliases_without_mutating_caller():
    source = {name: 'artificial-canary' for name in MODEL_CREDENTIALS}
    source.update(PATH='safe-path', MODUS_PROVIDER='meta', PYTHON_DOTENV_DISABLED='0',
        openai_api_key='artificial-case-canary')
    clean = offline_environment(source)
    assert not any(key.upper() in MODEL_CREDENTIALS for key in clean)
    assert clean == {'PATH': 'safe-path', 'MODUS_PROVIDER': 'offline', 'PYTHON_DOTENV_DISABLED': '1'}
    assert source['MODUS_META_KEY'] == 'artificial-canary' and source['MODUS_PROVIDER'] == 'meta'


def test_real_child_process_receives_no_provider_credential_canaries():
    source = {**os.environ, **{name: 'artificial-child-canary' for name in MODEL_CREDENTIALS}}
    code = 'import json,os; print(json.dumps({"present": [k for k in ' + repr(sorted(MODEL_CREDENTIALS)) + ' if k in os.environ], "dotenv_disabled":os.getenv("PYTHON_DOTENV_DISABLED"), "mode":os.getenv("MODUS_PROVIDER")}))'
    result = subprocess.run([sys.executable, '-c', code], env=offline_environment(source),
        check=True, capture_output=True, text=True)
    assert json.loads(result.stdout) == {'present': [], 'dotenv_disabled': '1', 'mode': 'offline'}


def test_pytest_collection_rejects_inherited_canaries_before_test_module_import(tmp_path):
    (tmp_path / 'conftest.py').write_text((ROOT / 'backend/tests/conftest.py').read_text(encoding='utf-8'), encoding='utf-8')
    (tmp_path / 'test_child.py').write_text('import os\nNAMES=' + repr(sorted(MODEL_CREDENTIALS))
        + '\nassert all(os.environ.get(name) == "" for name in NAMES)\n'
        + 'assert os.environ["PYTHON_DOTENV_DISABLED"] == "1"\n'
        + 'def test_isolated():\n    assert os.environ["MODUS_PROVIDER"] == "offline"\n', encoding='utf-8')
    source = {**os.environ, **{name: 'artificial-inherited-canary' for name in MODEL_CREDENTIALS},
        'MODUS_PROVIDER': 'meta', 'PYTHON_DOTENV_DISABLED': '0'}
    result = subprocess.run([sys.executable, '-m', 'pytest', '-q', str(tmp_path / 'test_child.py')],
        cwd=tmp_path, env=source, check=True, capture_output=True, text=True)
    assert '1 passed' in result.stdout and 'artificial-inherited-canary' not in result.stdout


@pytest.mark.parametrize('preferred,legacy,expected', [
    ('artificial-preferred', 'artificial-legacy', 'artificial-preferred'),
    ('', 'artificial-legacy', 'artificial-legacy'),
])
def test_meta_transport_uses_preferred_alias_with_legacy_fallback(monkeypatch, preferred, legacy, expected):
    monkeypatch.setenv('MODUS_META_KEY', preferred)
    monkeypatch.setenv('MODEL_API_KEY', legacy)
    monkeypatch.setenv('ANTHROPIC_API_KEY', 'artificial-evaluation-only-a')
    monkeypatch.setenv('OPENAI_API_KEY', 'artificial-evaluation-only-b')
    monkeypatch.setenv('MODUS_PROVIDER', 'meta')
    sent = []
    class FakeResponse:
        status_code = 200
        headers = {'x-request-id': 'artificial-request'}
        def json(self): return {'choices': [{'message': {'content': '{}'}, 'finish_reason': 'stop'}]}
    class FakeClient:
        def __init__(self, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): return False
        async def post(self, url, headers, json):
            sent.append((url, headers))
            return FakeResponse()
    monkeypatch.setattr(provider.httpx, 'AsyncClient', FakeClient)
    status = provider.provider_status()
    assert status['mode'] == 'meta' and status['key_configured'] is True
    asyncio.run(provider.meta_request({'model': 'muse-spark-1.3'}))
    assert sent == [('https://api.meta.ai/v1/chat/completions', {'Authorization': 'Bearer ' + expected})]
    assert 'artificial-' not in json.dumps(status)


def test_evaluation_keys_never_enable_product_meta_provider(monkeypatch):
    monkeypatch.setenv('MODUS_PROVIDER', 'meta')
    monkeypatch.setenv('ANTHROPIC_API_KEY', 'artificial-evaluation-only-a')
    monkeypatch.setenv('OPENAI_API_KEY', 'artificial-evaluation-only-b')
    assert provider.meta_credential() is None or provider.meta_credential() == ''
    assert provider.provider_status()['mode'] == 'offline'
    with pytest.raises(ValueError, match='not configured'):
        asyncio.run(provider.meta_request({'model': 'muse-spark-1.3'}))

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
from offline_environment import MODEL_CREDENTIALS, offline_environment, local_connection


def test_offline_boundary_allows_native_ipc_but_rejects_external_tcp():
    from types import SimpleNamespace
    import socket
    inet = SimpleNamespace(family=socket.AF_INET)
    assert local_connection(inet, ('127.0.0.1', 8031))
    assert not local_connection(inet, ('192.0.2.1', 443))
    assert not local_connection(inet, ('api.meta.ai', 443))
    assert not local_connection(inet, '/run/user/1000/bus')
    if hasattr(socket, 'AF_UNIX'):
        native = SimpleNamespace(family=socket.AF_UNIX)
        assert local_connection(native, '/run/user/1000/bus')
        assert local_connection(native, b'\x00authored-session-bus')


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


@pytest.mark.parametrize('status', [200, 301, 302, 307, 308])
def test_meta_transport_never_inherits_proxy_settings_or_follows_redirects(monkeypatch, status):
    monkeypatch.setenv('MODUS_META_KEY', 'artificial-transport-canary')
    monkeypatch.setenv('HTTPS_PROXY', 'http://untrusted.invalid:8080')
    calls, options = [], []
    class Response:
        status_code = status
        headers = {'location': 'https://untrusted.invalid/collect'}
        def json(self): return {'choices': []}
    class Client:
        def __init__(self, **kwargs): options.append(kwargs)
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def post(self, url, **kwargs):
            calls.append(url)
            return Response()
    monkeypatch.setattr(provider.httpx, 'AsyncClient', Client)
    if status == 200:
        asyncio.run(provider.meta_request({'model': 'muse-spark-1.3'}))
    else:
        with pytest.raises(provider.MetaRequestError) as failure:
            asyncio.run(provider.meta_request({'model': 'muse-spark-1.3'}))
        assert failure.value.http_status == status
    assert calls == ['https://api.meta.ai/v1/chat/completions']
    assert options[0]['trust_env'] is False and options[0]['follow_redirects'] is False
    assert options[0]['verify'].check_hostname

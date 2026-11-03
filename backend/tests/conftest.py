"""Ordinary pytest runs never inherit the developer's live provider credentials."""
import os

import pytest


# Set these before test collection imports application modules and loads .env.
# Live verification belongs in explicit opt-in smoke commands, not pytest.
os.environ['MODUS_PROVIDER'] = 'offline'
MODEL_CREDENTIALS = ('MODEL_API_KEY', 'MODUS_META_KEY', 'ANTHROPIC_API_KEY', 'OPENAI_API_KEY')
for name in MODEL_CREDENTIALS:
    os.environ[name] = ''
# Importing either application must not read credentials from the developer's
# .env, even when a test deletes an environment variable or uses override=True.
# python-dotenv 1.2.4 checks this before opening or parsing the file.
os.environ['PYTHON_DOTENV_DISABLED'] = '1'


@pytest.fixture(autouse=True)
def isolated_provider_environment(monkeypatch):
    monkeypatch.setenv('MODUS_PROVIDER', 'offline')
    for name in MODEL_CREDENTIALS:
        monkeypatch.setenv(name, '')
    monkeypatch.setenv('PYTHON_DOTENV_DISABLED', '1')


@pytest.fixture(autouse=True)
def local_service_client_defaults(monkeypatch):
    """Exercise the production boundary with a real loopback origin/peer.

    Explicit test overrides still work; no production test-host bypass exists.
    Security tests remove the write header to exercise missing-header rejection.
    """
    from starlette.testclient import TestClient
    original = TestClient.__init__
    def initialize(self, app, *args, **kwargs):
        if not args:
            kwargs.setdefault('base_url', 'http://127.0.0.1')
        kwargs.setdefault('client', ('127.0.0.1', 50000))
        kwargs.setdefault('headers', {'X-Modus-Request': '1'})
        original(self, app, *args, **kwargs)
    monkeypatch.setattr(TestClient, '__init__', initialize)

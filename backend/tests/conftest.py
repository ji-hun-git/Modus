"""Ordinary pytest runs never inherit the developer's live provider credentials."""
import os

import pytest


# Set these before test collection imports application modules and loads .env.
# Live verification belongs in explicit opt-in smoke commands, not pytest.
os.environ['MODUS_PROVIDER'] = 'offline'
os.environ['MODEL_API_KEY'] = ''


@pytest.fixture(autouse=True)
def isolated_provider_environment(monkeypatch):
    monkeypatch.setenv('MODUS_PROVIDER', 'offline')
    monkeypatch.setenv('MODEL_API_KEY', '')

"""Credential-free child environments for installs, tests and offline checks.

Live evaluation runners intentionally do not use this helper. No values are
logged, and the caller's environment is left unchanged.
"""
import os


MODEL_CREDENTIALS = frozenset({'MODEL_API_KEY', 'MODUS_META_KEY', 'ANTHROPIC_API_KEY', 'OPENAI_API_KEY'})


def offline_environment(base=None):
    source = os.environ if base is None else base
    result = {key: value for key, value in source.items() if key.upper() not in MODEL_CREDENTIALS}
    result.update(MODUS_PROVIDER='offline', PYTHON_DOTENV_DISABLED='1')
    return result

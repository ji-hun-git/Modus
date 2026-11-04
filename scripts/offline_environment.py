"""Credential-free child environments for installs, tests and offline checks.

Live evaluation runners intentionally do not use this helper. No values are
logged, and the caller's environment is left unchanged.
"""
import os
import socket


def local_connection(connection, address):
    """Loopback HTTP and local OS IPC only; Linux Secret Service uses D-Bus."""
    if isinstance(address, tuple):
        return address[0] in ('127.0.0.1', '::1', 'localhost')
    return (getattr(connection, 'family', None) == getattr(socket, 'AF_UNIX', object())
            and isinstance(address, (str, bytes)))


MODEL_CREDENTIALS = frozenset({'MODEL_API_KEY', 'MODUS_META_KEY', 'ANTHROPIC_API_KEY', 'OPENAI_API_KEY'})


def offline_environment(base=None):
    source = os.environ if base is None else base
    result = {key: value for key, value in source.items() if key.upper() not in MODEL_CREDENTIALS}
    result.update(MODUS_PROVIDER='offline', PYTHON_DOTENV_DISABLED='1')
    return result

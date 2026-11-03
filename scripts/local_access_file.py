"""Publish a launch-specific access file to a protected, service-owned directory."""
import json
import os
from pathlib import Path

from private_storage import secure_runtime_directory


def publish_access_file(app, directory, port, *, ui_port=None):
    if ui_port is not None:
        port = ui_port
    if type(port) is not int or not 1024 <= port <= 65535:
        raise ValueError('Use a valid local service port')
    directory = secure_runtime_directory(directory)
    target = directory / f'Modus-{port}.modus-access'
    material = app.state.local_access.configure(f'http://127.0.0.1:{port}')
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, 'O_NOFOLLOW', 0)
    with os.fdopen(os.open(target, flags, 0o600), 'w', encoding='utf-8') as stream:
        json.dump(material, stream)
    # Existing files were validated/restricted before writing; new Windows files
    # inherit the protected directory ACL. Never print the material or use a URL.
    return Path(target)

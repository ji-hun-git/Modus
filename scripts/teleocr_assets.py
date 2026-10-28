"""Fixed, hash-checked public TeleOCR snapshot. No fetch unless --download.

This is an operator CLI, never a model tool. Model files stay out of packages.
"""
import argparse
import hashlib
import json
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / 'config/teleocr.json'


def spec():
    return json.loads(CONFIG.read_text(encoding='utf-8'))


def snapshot_dir():
    return ROOT / 'release/models' / ('teleocr-' + spec()['revision'])


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def verify(directory=None):
    directory = Path(directory) if directory is not None else snapshot_dir()
    failures = []
    for item in spec()['files']:
        path = directory / item['name']
        if path.is_symlink() or not path.is_file():
            failures.append({'file': item['name'], 'reason': 'missing_or_symlink'})
        elif path.stat().st_size != item['bytes'] or digest(path) != item['sha256']:
            failures.append({'file': item['name'], 'reason': 'hash_or_size_mismatch'})
    allowed = {item['name'] for item in spec()['files']}
    if directory.exists():
        failures.extend({'file': p.name, 'reason': 'unlisted_model_file'}
                        for p in directory.iterdir() if p.name not in allowed)
    return failures


def download():
    config, target = spec(), snapshot_dir()
    target.mkdir(parents=True, exist_ok=True)
    for item in config['files']:
        path = target / item['name']
        if path.exists():
            if path.is_symlink() or path.stat().st_size != item['bytes'] or digest(path) != item['sha256']:
                raise ValueError('Existing snapshot file fails integrity: ' + item['name'])
            continue
        part = path.with_name(path.name + '.partial')
        url = f"https://huggingface.co/{config['model']}/resolve/{config['revision']}/{item['name']}"
        print('Fetching pinned ' + item['name'], flush=True)
        with urllib.request.urlopen(url, timeout=90) as response, part.open('wb') as output:
            count = 0
            while chunk := response.read(4 * 1024 * 1024):
                count += len(chunk)
                if count > item['bytes']:
                    raise ValueError('Download exceeded pinned file size')
                output.write(chunk)
        if count != item['bytes'] or digest(part) != item['sha256']:
            raise ValueError('Downloaded snapshot fails integrity: ' + item['name'])
        part.replace(path)
    failures = verify()
    if failures:
        raise ValueError(f'Snapshot verification failed: {failures}')
    print('Pinned snapshot verified. No model code executed.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--download', action='store_true')
    args = parser.parse_args()
    if args.download:
        download()
    else:
        print(json.dumps({'model': spec()['model'], 'revision': spec()['revision'],
                          'status': 'verified' if not verify() else 'not_ready',
                          'files': verify(), 'network_requests': 0}, indent=2))

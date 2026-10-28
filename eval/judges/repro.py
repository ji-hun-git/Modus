"""Local evaluator identity; no dataset, credentials or network discovery."""
from hashlib import sha256
import os
from pathlib import Path
import re
import subprocess

from .prompts import RUBRICS, SYSTEM, prompt
from .schema import fingerprint, output_schema


def snapshot(cases, rubric_version):
    folder = Path(__file__).resolve().parent
    sources = {p.name: sha256(p.read_bytes()).hexdigest() for p in sorted(folder.glob('*.py'))}
    commit = None
    # Only the evaluator's explicit HTTP adapter may receive these credentials.
    blocked = {'MODEL_API_KEY', 'MODUS_META_KEY', 'ANTHROPIC_API_KEY', 'OPENAI_API_KEY'}
    child_env = {k: v for k, v in os.environ.items() if k.upper() not in blocked}
    child_env.update(MODUS_PROVIDER='offline', PYTHON_DOTENV_DISABLED='1')
    try:
        result = subprocess.run(['git', 'rev-parse', '--verify', 'HEAD'], cwd=folder.parents[1],
            capture_output=True, text=True, timeout=3, check=False, shell=False, env=child_env)
        candidate = result.stdout.strip()
        if result.returncode == 0 and re.fullmatch(r'[0-9a-f]{40}|[0-9a-f]{64}', candidate):
            commit = candidate
    except (OSError, subprocess.TimeoutExpired):
        pass
    return {'evaluator_sources_sha256': sources, 'source_commit': commit,
        'source_identity_note': 'File hashes describe this run, including uncommitted changes; commit alone does not.',
        'rubrics_sha256': fingerprint(RUBRICS), 'system_prompt_sha256': sha256(SYSTEM.encode('utf-8')).hexdigest(),
        'case_prompts': [{'case_id': case.id,
            'user_prompt_sha256': sha256(prompt(case, images, rubric_version)[1].encode('utf-8')).hexdigest(),
            'output_schema_sha256': fingerprint(output_schema(prompt(case, images, rubric_version)[2]))}
            for case, images in cases]}

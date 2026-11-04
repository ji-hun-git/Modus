"""Public-source hygiene: keep private notes and credential material out of Git.

This is a deterministic publication check, not a complete secret detector or a
history scrubber. Protected evaluation contents are never opened by this tool.
Only filenames and finding categories are reported, never matched content.
"""
from dataclasses import asdict, dataclass
import json
from pathlib import Path, PurePosixPath
import re
import subprocess

PUBLIC_DOCS = frozenset({
    'README.md', 'AGENTS.md', 'SCOREBOARD.md', 'THIRD_PARTY_NOTICES.md',
    'entry/README.md', 'entry/AGENTS.md', 'entry/THIRD_PARTY_NOTICES.md',
    'docs/RECORD_UNIT_RULES.md', 'docs/ONTOLOGY_RAG_EVALUATION.md',
    'entry/docs/PRODUCT.md', 'entry/docs/API_CONTRACT.md', 'entry/docs/AGENT_WORKFLOW.md',
    'entry/docs/DATA.md', 'entry/docs/CONTRIBUTIONS.md', 'entry/docs/VERIFICATION.md',
    'entry/docs/WHOLE_HISTORY_AGENT.md', 'entry/docs/TERMINOLOGY_RETRIEVAL.md',
    'entry/docs/RECORD_BRIEF.md', 'entry/docs/BENCHMARK.md',
    'entry/docs/OPEN_SOURCE.md', 'backend/tests/fixtures/garak/NOTICE.md',
    'entry/frontend/README.md', 'data/synthetic/brief-demo/README.md',
    'entry/demo/longitudinal/README.md',
    'entry/prompts/records.md', 'entry/prompts/history.md', 'prompts/extract.md',
})
TEXT_SUFFIXES = {'.py','.ts','.tsx','.js','.mjs','.json','.md','.txt','.yaml','.yml','.toml','.html','.css','.svg'}
PRIVATE_DIRS = {'private','private-notes','notes','handoff','attachments','references'}
PRIVATE_NAMES = {'kickoff.txt','metaapi.txt','claude-key.txt','openai-key.txt',
                 'progress.md','start_here.md','competition_checklist.md'}
SECRET = re.compile(r'(?<![A-Za-z0-9_-])(?:sk-(?:proj-)?[A-Za-z0-9_-]{24,}|hf_[A-Za-z0-9]{24,}|gh[pousr]_[A-Za-z0-9]{25,}|github_pat_[A-Za-z0-9_]{30,})|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----')
PERSONAL_DOC = re.compile(r'\b(?:Jason|Astra)\b|C:\\Users\\|C:/Users/|/Users/[^/\s]+/|\.codex[/\\]attachments|<send_user_message_question_reply>|# MASTER PROMPT',re.I)


@dataclass(frozen=True)
class Finding:
    path: str
    code: str
    line: int | None = None


def protected(name):
    lower=name.replace('\\','/').lower()
    return lower.startswith(('eval/','evaluation/','entry/eval/')) or 'heldout' in lower or 'holdout' in lower


def path_problem(name):
    if any(part in name.lower() for part in ('.modus-vault.json','.modus-lock','.encrypting-','.encrypted-backup-')):
        return 'credential_or_runtime_file'
    normalized=name.replace('\\','/')
    path=PurePosixPath(normalized)
    lower=normalized.lower()
    if path.is_absolute() or '..' in path.parts or re.match(r'^[A-Za-z]:',normalized):
        return 'outside_repository'
    if any(p.lower() in PRIVATE_DIRS for p in path.parts) or path.name.lower() in PRIVATE_NAMES:
        return 'private_working_material'
    if (path.name.lower().startswith('.env') and path.name != '.env.example'
            or path.suffix.lower() in {'.key','.pem','.p12','.pfx','.db','.sqlite','.sqlite3','.safetensors','.modus-access'}):
        return 'credential_or_runtime_file'
    if path.suffix.lower()=='.md' and normalized not in PUBLIC_DOCS:
        if not lower.startswith('data/licenses/'):
            return 'unreviewed_public_document'
    return None


def content_findings(name, text):
    found=[]
    for number,line in enumerate(text.splitlines(),1):
        if SECRET.search(line) or re.search(r'modus_(?:local|session)_[A-Za-z0-9_-]{43}|modus_db_key_[0-9a-f]{64}', line):
            found.append(Finding(name,'credential_pattern',number))
        if (name.endswith('.md') and not name.startswith(('data/licenses/','entry/prompts/','prompts/'))
                and name not in {'SCOREBOARD.md','docs/ONTOLOGY_RAG_EVALUATION.md','entry/docs/BENCHMARK.md'}
                and PERSONAL_DOC.search(line)):
            found.append(Finding(name,'personal_working_context',number))
    return found


def manifest_items(root):
    return json.loads((root/'entry/config/source_manifest.json').read_text(encoding='utf-8'))['files']


def audit(root, *, selection_only=False):
    root=Path(root).resolve()
    items=manifest_items(root)
    names={item[key] for item in items for key in ('source','destination')}
    if not selection_only:
        try:
            names.update(subprocess.check_output(['git','ls-files','-z'],cwd=root).decode('utf-8').split('\0'))
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass  # A fresh source extract has the exact manifest instead of Git.
    findings=[]; inspected=0; skipped=0
    for item in items:
        for key in ('source','destination'):
            name=item[key]
            if protected(name): continue
            issue=path_problem(name)
            if issue: findings.append(Finding(name,issue))
    for name in sorted(names-{''}):
        if protected(name):
            skipped+=1
            continue  # Do not stat, open, parse or hash protected artifacts.
        issue=path_problem(name)
        candidate=root/name
        if not candidate.exists(): continue  # Mapped source paths and staged removals.
        if issue:
            findings.append(Finding(name,issue))
            continue
        if candidate.is_symlink() or not candidate.resolve().is_relative_to(root):
            findings.append(Finding(name,'outside_repository'))
            continue
        if candidate.suffix.lower() not in TEXT_SUFFIXES or name.startswith('data/licenses/'):
            continue
        if candidate.stat().st_size>2_000_000:
            findings.append(Finding(name,'text_requires_manual_review'))
            continue
        try:
            content=candidate.read_text(encoding='utf-8')
        except UnicodeError:
            findings.append(Finding(name,'text_requires_manual_review'))
            continue
        inspected+=1
        findings.extend(content_findings(name,content))
    return {'status':'failed' if findings else 'passed','inspected_text_files':inspected,
        'protected_paths_skipped':skipped,'findings':[asdict(f) for f in dict.fromkeys(findings)],
        'scope':'Current public source selection only; no protected data or Git history contents read.'}


def require_public(root, *, selection_only=False):
    report=audit(root,selection_only=selection_only)
    if report['findings']:
        details=', '.join(f"{f['path']} ({f['code']})" for f in report['findings'])
        raise ValueError('Public source check failed: '+details)
    return report


if __name__=='__main__':
    result=audit(Path(__file__).resolve().parents[1])
    print(json.dumps(result,indent=2))
    raise SystemExit(0 if result['status']=='passed' else 1)

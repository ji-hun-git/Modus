"""Frozen synthetic evaluation data and enforceable pre-request budgets."""
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path, PurePosixPath


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


def fingerprint(value):
    return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()


def safe_path(root, name):
    root = Path(root).resolve()
    if not isinstance(name, str) or not name:
        raise ValueError('Unsafe benchmark path')
    relative = PurePosixPath(name)
    if not isinstance(name, str) or '\\' in name or ':' in name or relative.is_absolute() or '..' in relative.parts:
        raise ValueError('Unsafe benchmark path')
    current = root
    for part in relative.parts:
        current /= part
        if current.is_symlink():
            raise ValueError('Benchmark symlinks are not allowed')
    if not current.resolve().is_relative_to(root) or not current.is_file():
        raise ValueError('Missing or unsafe benchmark file')
    return current


def verify_files(root, files):
    for name, digest in files.items():
        if hashlib.sha256(safe_path(root, name).read_bytes()).hexdigest() != digest:
            raise ValueError('Frozen benchmark hash mismatch: ' + name)


def unique(values, label):
    if len(values) != len(set(values)):
        raise ValueError('Duplicate ' + label)


def validate_suite(root, kind, *, selected_split=None):
    root = Path(root)
    if kind not in {'workflow', 'documents'}:
        raise ValueError('Unknown benchmark kind')
    raw = safe_path(root, 'freeze.json').read_bytes()
    freeze = json.loads(raw)
    files = freeze['files_sha256']
    if not {'dev.json', 'holdout.json'} <= set(files):
        raise ValueError('Both benchmark splits must be frozen')
    if selected_split not in {None, 'dev', 'holdout'}:
        raise ValueError('Unknown benchmark split')
    # Full cross-split validation is for corpus creation/self-tests. Development
    # execution must not open, stat or hash any held-out input or annotation.
    if selected_split is None:
        verify_files(root, files)
    selected_files = {}
    splits, identities, signatures = {}, {}, {}
    for split in ((selected_split,) if selected_split else ('dev', 'holdout')):
        selected_files[split + '.json'] = files[split + '.json']
        verify_files(root, {split + '.json': files[split + '.json']})
        data = json.loads(safe_path(root, split + '.json').read_text(encoding='utf-8'))
        if data['split'] != split or not data.get('version') or not data['cases']:
            raise ValueError('Invalid benchmark split')
        unique([c['id'] for c in data['cases']], 'case IDs')
        if kind == 'workflow':
            scenarios = data['scenarios']
            unique([s['id'] for s in scenarios], 'scenario IDs')
            unique([s['family_id'] for s in scenarios], 'scenario family IDs')
            unique([s['profile_id'] for s in scenarios], 'scenario profile IDs')
            by_id = {s['id']: s for s in scenarios}
            for scenario in scenarios:
                unique([s['id'] for s in scenario['sources']], 'source IDs')
                unique([o['id'] for o in scenario['observations']], 'observation IDs')
                source_ids = {s['id'] for s in scenario['sources']}
                if any(o['source_id'] not in source_ids for o in scenario['observations']):
                    raise ValueError('Unknown observation source')
            for case in data['cases']:
                if case['scenario_id'] not in by_id or not case.get('question'):
                    raise ValueError('Unknown scenario or empty question')
                expected = case['expected']
                if expected['intent'] not in {'inventory', 'conflicts', 'arrivals', 'abstain'}:
                    raise ValueError('Unknown expected intent')
                unique(expected['evidence_ids'], 'gold evidence IDs')
                all_ids = {o['id'] for o in by_id[case['scenario_id']]['observations']}
                if not set(expected['evidence_ids']) <= all_ids:
                    raise ValueError('Gold evidence has unknown IDs')
            identities[split] = ({s['family_id'] for s in scenarios}, {s['profile_id'] for s in scenarios})
            facts = []
            for scenario in scenarios:
                source_times = {s['id']: s['available_at'] for s in scenario['sources']}
                facts.append(fingerprint(sorted((o['metric'], o['value'], o['unit'], o['date'], source_times[o['source_id']]) for o in scenario['observations'])))
            signatures[split] = set(facts)
        else:
            identities[split] = ({c['family_id'] for c in data['cases']}, {c['profile_id'] for c in data['cases']})
            signatures[split] = set()
            unique([c['file'] for c in data['cases']], 'document paths')
            for case in data['cases']:
                if files.get(case['file']) != case['sha256']:
                    raise ValueError('Document is not covered by frozen hashes')
                if selected_split and (case['file'].casefold() == ('holdout.json' if split == 'dev' else 'dev.json') or ('holdout' if split == 'dev' else 'dev') in [part.casefold() for part in PurePosixPath(case['file']).parts]):
                    raise ValueError('Document crosses the selected split directory')
                selected_files[case['file']] = case['sha256']
                verify_files(root, {case['file']: case['sha256']})
                if case['mime'] not in {'application/pdf', 'image/png', 'image/jpeg'} or case['pages'] != len(case['page_text']):
                    raise ValueError('Invalid document annotation')
                signatures[split].add(case['sha256'])
        splits[split] = data
    if selected_split:
        return {**splits, 'freeze_id': hashlib.sha256(raw).hexdigest(),
                'files_sha256': selected_files, 'validation_scope': selected_split + '_only; cross-split audit belongs to the preserved corpus freeze'}
    if any(identities['dev'][i] & identities['holdout'][i] for i in (0, 1)):
        raise ValueError('Development and holdout families/profiles overlap')
    if signatures['dev'] & signatures['holdout']:
        raise ValueError('Development and holdout content overlap')
    if {c['id'] for c in splits['dev']['cases']} & {c['id'] for c in splits['holdout']['cases']}:
        raise ValueError('Cross-split case IDs overlap')
    return {**splits, 'freeze_id': hashlib.sha256(raw).hexdigest(), 'files_sha256': files}


class BudgetExceeded(RuntimeError):
    pass


@dataclass
class Budget:
    max_requests: int
    max_output_tokens: int
    max_context_bytes: int = 128000
    calls: int = 0
    output_reserved: int = 0

    def reserve(self, payload):
        tokens = payload.get('max_completion_tokens')
        if type(tokens) is not int or tokens <= 0:
            raise BudgetExceeded('Explicit output-token limit required')
        size = len(canonical(payload).encode('utf-8'))
        if size > self.max_context_bytes:
            raise BudgetExceeded('Serialized request exceeds the context-byte cap')
        if self.calls + 1 > self.max_requests or self.output_reserved + tokens > self.max_output_tokens:
            raise BudgetExceeded('Request or reserved-output budget exhausted')
        self.calls += 1
        self.output_reserved += tokens


def event(path, value):
    with Path(path).open('a', encoding='utf-8') as stream:
        stream.write(canonical(value) + '\n')
        stream.flush()


def require_execution(args):
    if not args.execute:
        return
    if args.split == 'holdout' and (not args.unlock_holdout or not args.holdout_reason.strip()):
        raise ValueError('Held-out execution requires --unlock-holdout and --holdout-reason')
    if any(m.startswith('meta') for m in args.methods) and (not args.allow_network or args.max_requests <= 0 or args.max_output_tokens <= 0):
        raise ValueError('Live execution requires --allow-network and positive request/output budgets')

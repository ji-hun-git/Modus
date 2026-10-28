"""Artificial comparison/isolation fixtures only; no project evaluation data."""
import asyncio
from copy import deepcopy
import hashlib
import importlib
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
common = importlib.import_module('benchmark_common')
grading = importlib.import_module('benchmark_grading')
comparison = importlib.import_module('compare_development')
runner = importlib.import_module('benchmark_runner')


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding='utf-8')


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def plan_identity(plan):
    plan['plan_id'] = common.fingerprint({k: v for k, v in plan.items() if k != 'plan_id'})
    return plan


@pytest.fixture
def artificial_comparison(tmp_path):
    suite = tmp_path / 'evaluation/documents_v1'
    document = suite / 'dev/artificial.png'
    document.parent.mkdir(parents=True)
    document.write_bytes(b'Artificial comparison bytes; never decoded or inferred.')
    digest = hashlib.sha256(document.read_bytes()).hexdigest()
    row = {'metric': 'egfr', 'value': 71, 'unit': 'mL/min/1.73m2', 'date': '2026-01-01',
        'page': 1, 'source_span': 'eGFR 71 mL/min/1.73m2'}
    case = {'id': 'artificial-case', 'family_id': 'artificial-family', 'profile_id': 'artificial-profile',
        'file': 'dev/artificial.png', 'sha256': digest, 'mime': 'image/png', 'pages': 1,
        'page_text': ['eGFR 71 mL/min/1.73m2'], 'expected': [row]}
    save(suite / 'dev.json', {'version': 'artificial-v1', 'split': 'dev', 'cases': [case]})
    files = {'dev.json': hashlib.sha256((suite / 'dev.json').read_bytes()).hexdigest(),
        'dev/artificial.png': digest, 'holdout.json': '0' * 64, 'holdout/never-open.png': '1' * 64}
    save(suite / 'freeze.json', {'files_sha256': files})
    # Held-out files deliberately do not exist. A selected dev run has no need to probe them.
    freeze_id = hashlib.sha256((suite / 'freeze.json').read_bytes()).hexdigest()
    frozen = tmp_path / 'evaluation/baseline-v2/source'
    source_file = frozen / 'backend/modus/artificial.py'
    source_file.parent.mkdir(parents=True)
    source_file.write_text('# Artificial frozen source\n', encoding='utf-8')
    source_hashes = comparison.hashes(frozen, [source_file])
    candidate_source = tmp_path / 'backend/modus_entry/artificial.py'
    candidate_source.parent.mkdir(parents=True)
    candidate_source.write_text('# Artificial candidate source\n', encoding='utf-8')
    candidate_hashes = runner.source_hashes(tmp_path)
    save(tmp_path / 'evaluation/baseline-v2/protocol.json', {'source_sha256': source_hashes})
    baseline = tmp_path / comparison.BASELINES['documents']
    candidate = tmp_path / 'candidate'
    for folder in (baseline, candidate):
        schedule = [{'case_id': case['id'], 'repeat': 1, 'method': 'local_parser'}]
        plan = plan_identity({'format': 'modus-benchmark-plan-v1', 'kind': 'documents', 'split': 'dev',
            'freeze_id': freeze_id, 'dataset_files_sha256': {**files, 'freeze.json': freeze_id},
            'methods': ['local_parser'], 'repeats': 1, 'schedule': schedule,
            'source_sha256': source_hashes if folder == baseline else candidate_hashes})
        attempt = {**schedule[0], 'attempt_id': 'artificial-attempt', 'status': 'completed',
            'result': {'mode': 'local deterministic parser', 'observations': [deepcopy(row)]},
            'grade': grading.grade_document(case, [row]), 'duration_ms': 1, 'usage': None}
        save(folder / 'plan.json', plan)
        save(folder / 'summary.json', {'status': 'completed', 'plan_id': plan['plan_id'],
            'source_unchanged': True, 'dataset_unchanged': True, 'global_budget_exhausted': False,
            'summary': grading.aggregate(schedule, [attempt])})
        (folder / 'events.jsonl').write_text(json.dumps({'event': 'attempt_started', **schedule[0],
            'attempt_id': 'artificial-attempt'}) + '\n' + json.dumps({'event': 'attempt_finished', **attempt}) + '\n', encoding='utf-8')
    return tmp_path, suite, baseline, candidate


def test_selected_dev_never_probes_nonexistent_heldout_paths(artificial_comparison, monkeypatch):
    _, suite, _, _ = artificial_comparison
    def guarded(original):
        def invoke(path, *args, **kwargs):
            if path.name.lower() == 'holdout.json' or 'holdout' in [part.lower() for part in path.parts]:
                pytest.fail('Selected development operation touched a held-out path')
            return original(path, *args, **kwargs)
        return invoke
    for method in ('read_bytes', 'read_text', 'stat', 'exists', 'is_file', 'is_symlink'):
        monkeypatch.setattr(Path, method, guarded(getattr(Path, method)))
    selected = common.validate_suite(suite, 'documents', selected_split='dev')
    assert set(selected['files_sha256']) == {'dev.json', 'dev/artificial.png'}
    assert 'holdout' not in selected
    common.verify_files(suite, {**selected['files_sha256'], 'freeze.json': selected['freeze_id']})


@pytest.mark.parametrize('forbidden_path', ['holdout/never-open.png', 'HOLDOUT/never-open.png'])
def test_split_directory_alias_rejects_before_filesystem_probe(artificial_comparison, monkeypatch, forbidden_path):
    _, suite, _, _ = artificial_comparison
    data = read(suite / 'dev.json')
    data['cases'][0].update(file=forbidden_path, sha256='1' * 64)
    save(suite / 'dev.json', data)
    freeze = read(suite / 'freeze.json')
    freeze['files_sha256'].update({forbidden_path: '1' * 64,
        'dev.json': hashlib.sha256((suite / 'dev.json').read_bytes()).hexdigest()})
    save(suite / 'freeze.json', freeze)
    original = Path.is_symlink
    def guarded(path):
        if 'holdout' in [part.lower() for part in path.parts]:
            pytest.fail('Case-insensitive held-out alias reached filesystem')
        return original(path)
    monkeypatch.setattr(Path, 'is_symlink', guarded)
    with pytest.raises(ValueError, match='split'):
        common.validate_suite(suite, 'documents', selected_split='dev')


def test_saved_baseline_and_candidate_regrade_identically(artificial_comparison):
    root, _, _, candidate = artificial_comparison
    result = comparison.compare('documents', candidate, root=root)
    assert result['baseline_outcomes_unchanged'] is True
    assert result['summary']['methods']['baseline_local_parser']['passed'] == 1
    assert result['summary']['methods']['candidate_local_parser']['passed'] == 1
    assert result['paired'][0]['both_passed'] == 1


@pytest.mark.parametrize('fault', ['source_freeze', 'annotation_hash', 'repetitions', 'case_schedule',
    'missing_attempt', 'duplicated_attempt', 'outcome_change'])
def test_comparison_rejects_unmatched_evidence(artificial_comparison, fault):
    root, _, baseline, candidate = artificial_comparison
    plan = read(candidate / 'plan.json')
    if fault == 'source_freeze':
        (root / 'evaluation/baseline-v2/source/backend/modus/artificial.py').write_text('# Changed\n', encoding='utf-8')
    elif fault == 'annotation_hash':
        plan['dataset_files_sha256']['dev.json'] = 'wrong'
        save(candidate / 'plan.json', plan_identity(plan))
    elif fault == 'repetitions':
        plan['repeats'] = 2
        save(candidate / 'plan.json', plan_identity(plan))
    elif fault == 'case_schedule':
        plan['schedule'][0]['case_id'] = 'not-in-data'
        save(candidate / 'plan.json', plan_identity(plan))
    else:
        lines = (baseline / 'events.jsonl').read_text(encoding='utf-8').splitlines()
        if fault == 'missing_attempt':
            lines = lines[:1]
        elif fault == 'duplicated_attempt':
            lines.append(lines[-1])
        else:
            attempt = json.loads(lines[-1])
            attempt['grade']['passed'] = False
            lines[-1] = json.dumps(attempt)
        (baseline / 'events.jsonl').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    with pytest.raises(ValueError):
        comparison.compare('documents', candidate, root=root)


@pytest.mark.parametrize('fault', ['plan_fingerprint', 'summary_identity', 'budget_exhaustion', 'empty_methods'])
def test_comparison_rejects_unverified_run_identity(artificial_comparison, fault):
    root, _, _, candidate = artificial_comparison
    if fault in ('summary_identity', 'budget_exhaustion'):
        summary = read(candidate / 'summary.json')
        summary['plan_id' if fault == 'summary_identity' else 'global_budget_exhausted'] = 'wrong' if fault == 'summary_identity' else True
        save(candidate / 'summary.json', summary)
    else:
        plan = read(candidate / 'plan.json')
        if fault == 'plan_fingerprint':
            plan['plan_id'] = 'forged-identity'
        else:
            plan['methods'] = []
            plan_identity(plan)
            summary = read(candidate / 'summary.json')
            summary['plan_id'] = plan['plan_id']
            save(candidate / 'summary.json', summary)
        save(candidate / 'plan.json', plan)
    with pytest.raises(ValueError):
        comparison.compare('documents', candidate, root=root)


def test_ocr_mock_run_cannot_claim_real_model_measurement(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, 'source_hashes', lambda: {'artificial': 'fixed'})
    monkeypatch.setattr(runner, 'installed_environment', lambda: {})
    plan = runner.make_plan('documents', {'freeze_id': 'fake', 'files_sha256': {}}, 'dev',
        [{'id': 'artificial'}], ['local_hybrid'], 1, 'artificial-model',
        {'max_requests': 0, 'max_output_tokens': 0, 'max_context_bytes': 1000, 'per_request_output_tokens': 10})
    folder = runner.prepare_run(tmp_path, plan)
    async def fake_transport(payload):
        pytest.fail('Local OCR must not call the provider')
    async def execute(spec, request):
        return {'mode': 'local-teleocr', 'telemetry': {'status': 'completed', 'input_tokens': 12, 'output_tokens': 8}}, {'passed': True}
    report = asyncio.run(runner.execute_schedule(plan, folder, execute, transport=fake_transport))
    assert report['execution_class'] == 'mock_transport_test'
    assert report['model_performance_measured'] is False


@pytest.mark.parametrize('counts', [(12, 8), (None, 8), (True, 8), (-1, 8)])
def test_local_model_usage_preserves_known_and_unknown_tokens(tmp_path, monkeypatch, counts):
    monkeypatch.setattr(runner, 'source_hashes', lambda: {'artificial': 'fixed'})
    monkeypatch.setattr(runner, 'installed_environment', lambda: {})
    plan = runner.make_plan('documents', {'freeze_id': 'fake', 'files_sha256': {}}, 'dev',
        [{'id': 'artificial'}], ['local_hybrid'], 1, 'artificial-model',
        {'max_requests': 0, 'max_output_tokens': 0, 'max_context_bytes': 1000, 'per_request_output_tokens': 10})
    folder = runner.prepare_run(tmp_path, plan)
    async def execute(spec, request):
        return {'mode': 'local-teleocr', 'telemetry': {'status': 'completed',
            'input_tokens': counts[0], 'output_tokens': counts[1]}}, {'passed': True}
    report = asyncio.run(runner.execute_schedule(plan, folder, execute))
    usage = report['summary']['methods']['local_hybrid']['usage']
    assert report['requests_reserved'] == 0
    assert usage['total_tokens'] == (20 if counts == (12, 8) else None)


@pytest.fixture
def artificial_workflow(artificial_comparison):
    root, _, _, _ = artificial_comparison
    suite = root / 'evaluation/workflow_v1'
    source = {'id': 'artificial-source', 'title': 'Artificial source', 'provider': 'Synthetic',
        'type': 'lab', 'date': '2021-04-08', 'available_at': '2022-01-01T00:00:00Z',
        'availability_basis': 'authored_synthetic_fixture', 'content': 'Artificial row.', 'synthetic': True}
    observation = {'id': 'artificial-row', 'source_id': source['id'], 'metric': 'egfr', 'value': 71,
        'unit': 'mL/min/1.73m2', 'date': '2021-04-08', 'source_span': 'Artificial row.'}
    scenario = {'id': 'artificial-scenario', 'family_id': 'artificial-family', 'profile_id': 'artificial-person',
        'sources': [source], 'observations': [observation]}
    case = {'id': 'artificial-arrivals', 'scenario_id': scenario['id'], 'question': 'What records arrived?',
        'as_of': '2021-12-31', 'known_at': '2023-01-01T00:00:00Z', 'compare_from': '2021-12-31T23:59:59Z',
        'expected': {'intent': 'arrivals', 'evidence_ids': ['artificial-row'], 'added_count': 1, 'unchanged_count': 0}}
    save(suite / 'dev.json', {'version': 'artificial-workflow-v1', 'split': 'dev',
        'scenarios': [scenario], 'cases': [case]})
    files = {'dev.json': hashlib.sha256((suite / 'dev.json').read_bytes()).hexdigest(), 'holdout.json': '0' * 64}
    save(suite / 'freeze.json', {'files_sha256': files})
    freeze_id = hashlib.sha256((suite / 'freeze.json').read_bytes()).hexdigest()
    original_hashes = read(root / 'evaluation/baseline-v2/protocol.json')['source_sha256']
    original_bundle = comparison.identity({p: digest for p, digest in original_hashes.items() if not p.startswith('scripts/')})
    assert original_bundle != comparison.BUNDLE_ID
    context = comparison.build_context(scenario, case)
    claims, _ = comparison.candidate_bank(context)
    baseline = root / comparison.BASELINES['workflow']
    candidate = root / 'workflow-candidate'
    def original_scope(view):
        bound = view['scope']
        return {**bound, 'scope_id': comparison.identity({'as_of': bound['as_of'], 'known_at': bound['known_at'],
            'observations': view['observations'], 'sources': view['sources'], 'bundle_id': original_bundle})}
    for folder in (baseline, candidate):
        old = folder == baseline
        schedule = [{'case_id': case['id'], 'repeat': 1, 'method': 'local_fixed'}]
        plan = plan_identity({'format': 'modus-benchmark-plan-v1', 'kind': 'workflow', 'split': 'dev',
            'freeze_id': freeze_id, 'dataset_files_sha256': {**files, 'freeze.json': freeze_id},
            'methods': ['local_fixed'], 'repeats': 1, 'schedule': schedule,
            'source_sha256': original_hashes if old else runner.source_hashes(root)})
        selected_scope = original_scope(context['view']) if old else context['view']['scope']
        selected_comparison = {key: original_scope(context['comparison'][key]) if old else context['comparison'][key]['scope']
            for key in ('before', 'after')}
        result = {'answer': grading.SUPPORTED_ANSWER, 'claims': [claims['arrival-count']],
            'scope': selected_scope, 'comparison': selected_comparison,
            'execution': {'bundle_id': original_bundle if old else comparison.BUNDLE_ID}}
        grade = grading.grade_workflow(case, result, claims, selected_scope, selected_comparison)
        assert grade['passed']
        attempt = {**schedule[0], 'attempt_id': 'artificial-workflow-attempt', 'status': 'completed',
            'result': result, 'grade': grade, 'duration_ms': 1, 'usage': None}
        save(folder / 'plan.json', plan)
        save(folder / 'summary.json', {'status': 'completed', 'plan_id': plan['plan_id'],
            'source_unchanged': True, 'dataset_unchanged': True, 'global_budget_exhausted': False})
        (folder / 'events.jsonl').write_text(json.dumps({'event': 'attempt_finished', **attempt}) + '\n', encoding='utf-8')
    return root, baseline, candidate, original_bundle, context


def test_old_runtime_scope_is_recomputed_and_saved_outputs_unchanged(artificial_workflow):
    root, baseline, candidate, old_bundle, context = artificial_workflow
    before_bytes = (baseline / 'events.jsonl').read_bytes()
    candidate_bytes = (candidate / 'events.jsonl').read_bytes()
    result = comparison.compare('workflow', candidate, root=root)
    assert result['baseline_outcomes_unchanged'] is True
    assert result['paired'][0]['both_passed'] == 1
    assert old_bundle != comparison.BUNDLE_ID
    assert (baseline / 'events.jsonl').read_bytes() == before_bytes
    assert (candidate / 'events.jsonl').read_bytes() == candidate_bytes


@pytest.mark.parametrize('fault', ['baseline_scope', 'candidate_scope', 'baseline_execution',
    'candidate_execution', 'earlier_scope'])
def test_wrong_old_or_current_runtime_scope_rejects(artificial_workflow, fault):
    root, baseline, candidate, old_bundle, context = artificial_workflow
    folder = candidate if fault.startswith('candidate') else baseline
    path = folder / 'events.jsonl'
    row = json.loads(path.read_text(encoding='utf-8'))
    if fault == 'baseline_scope':
        row['result']['scope'] = context['view']['scope']
    elif fault == 'candidate_scope':
        row['result']['scope']['scope_id'] = 'old-or-invented-scope'
    elif fault.endswith('execution'):
        row['result']['execution']['bundle_id'] = old_bundle if fault.startswith('candidate') else comparison.BUNDLE_ID
    else:
        row['result']['comparison']['before'] = context['comparison']['before']['scope']
    path.write_text(json.dumps(row) + '\n', encoding='utf-8')
    with pytest.raises(ValueError):
        comparison.compare('workflow', candidate, root=root)

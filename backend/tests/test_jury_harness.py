"""Eval-only jury checks using new temporary synthetic artifacts and mock APIs.

No product data, credentials, authored benchmark corpus, holdout or live network.
"""
import asyncio
from copy import deepcopy
from decimal import Decimal
import json
from pathlib import Path
import sys

import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from eval.judges import code_checks, runner, schema, transport, repro
from eval.judges.budget import Book, BudgetDenied
from eval.judges.prompts import cache_identity, prompt


@pytest.fixture(autouse=True)
def forbid_network_and_credentials(monkeypatch):
    import dotenv
    import httpx
    def fail(*args, **kwargs):
        raise AssertionError('Offline jury tests cannot read credentials or open network clients')
    monkeypatch.setattr(httpx, 'AsyncClient', fail)
    monkeypatch.setattr(dotenv, 'load_dotenv', fail)
    for name in ('MODUS_META_KEY', 'ANTHROPIC_API_KEY', 'OPENAI_API_KEY'):
        monkeypatch.setenv(name, '')


def model_lock():
    # Public model lock only. No private input/cache/ledger is accessed.
    return json.loads((ROOT / 'eval/judges/models.yaml').read_text(encoding='utf-8'))


def fixture(tmp_path, artifact=None):
    artifact = artifact or {'task': 'Show recorded values and the source.', 'final_answer': 'Example only.', 'trace': [], 'evidence': {}}
    Image.new('RGB', (30, 20), 'white').save(tmp_path / 'screen.png')
    case = {'id': 'fresh-unit-case', 'candidate_provider': 'meta', 'artifact': artifact,
        'screenshots': ['screen.png'], 'deterministic': {
            'C': code_checks.faithfulness(artifact), 'E': code_checks.extraction(artifact)}}
    input_path, lock_path = tmp_path / 'input.json', tmp_path / 'models.json'
    input_path.write_text(json.dumps({'schema': 'modus-jury-input-v1', 'synthetic': True, 'cases': [case]}), encoding='utf-8')
    lock_path.write_text(json.dumps(model_lock()), encoding='utf-8')
    return input_path, lock_path


def marks(criteria):
    return {'assessments': [{'criterion': key, 'score': 4, 'passed': True, 'advice_flag': False,
        'reason': 'Explicit unit mock score.', 'evidence_refs': ['artifact.task']} for key in criteria]}


def envelope(provider, body, *, usage=True):
    text = body if isinstance(body, str) else json.dumps(body)
    if provider.provider == 'meta':
        response = {'model': provider.model, 'id': 'unit-response', 'choices': [{'finish_reason': 'stop', 'message': {'content': text}}]}
        if usage: response['usage'] = {'prompt_tokens': 50, 'completion_tokens': 100, 'total_tokens': 150}
    elif provider.provider == 'anthropic':
        response = {'model': provider.model, 'id': 'unit-response', 'stop_reason': 'end_turn', 'content': [{'type': 'text', 'text': text}]}
        if usage: response['usage'] = {'input_tokens': 50, 'output_tokens': 100}
    else:
        response = {'model': provider.model, 'id': 'unit-response', 'status': 'completed', 'error': None, 'incomplete_details': None,
            'output': [{'type': 'message', 'content': [{'type': 'output_text', 'text': text}]}]}
        if usage: response['usage'] = {'input_tokens': 50, 'output_tokens': 100}
    return {'http_status': 200, 'request_id': 'unit-request', 'latency_ms': 1, 'body': response}


def requested(request, provider):
    wire = request['response_format']['json_schema']['schema'] if provider == 'meta' else request['output_config']['format']['schema'] if provider == 'anthropic' else request['text']['format']['schema']
    return wire['properties']['assessments']['items']['properties']['criterion']['enum']


def execute(tmp_path, files, wire):
    return asyncio.run(runner.run(*files, execute=True, allow_network=True,
        private_root=tmp_path / 'private', report_root=tmp_path / 'reports', transport=wire))


def test_prepare_has_no_credential_or_network_or_private_cache_access(tmp_path, monkeypatch):
    files = fixture(tmp_path)
    monkeypatch.setattr(runner.os, 'getenv', lambda *a: pytest.fail('Preparation must not inspect credentials'))
    result = asyncio.run(runner.run(*files, private_root=tmp_path / 'private', report_root=tmp_path / 'reports'))
    assert result['mode'] == 'prepare_only' and result['provider_requests_made'] == 0
    assert result['max_new_requests'] == 3
    assert result['model_lock']['providers'][2]['settings']['store'] is False
    assert not (tmp_path / 'private').exists()


def test_execute_requires_explicit_network_opt_in(tmp_path):
    with pytest.raises(ValueError, match='allow-network'):
        asyncio.run(runner.run(tmp_path / 'missing.json', tmp_path / 'missing-models.json', execute=True,
            private_root=tmp_path / 'private', report_root=tmp_path / 'reports'))


def test_three_independent_mock_judges_then_exact_success_cache_hits(tmp_path):
    files, calls = fixture(tmp_path), []
    async def wire(provider, request, key):
        calls.append(provider.provider)
        assert 'tools' not in request
        return envelope(provider, marks(requested(request, provider.provider)))
    first = execute(tmp_path, files, wire)
    assert set(calls) == {'meta', 'anthropic', 'openai'}
    assert first['execution_class'] == 'mock' and first['provider_requests_made'] == 0
    assert first['cases'][0]['criteria']['A']['mode'] == 'full_three'
    assert first['agreement']['human_labels'] == 'not_supplied_not_measured'
    second = execute(tmp_path, files, wire)
    assert len(calls) == 3
    assert set(second['cases'][0]['provider_status'].values()) == {'cache_hit'}
    assert all(v['run_accounted_usd'] == 0 for v in second['costs'].values())
    prior = next(p['prior_spend_usd'] for p in model_lock()['providers'] if p['provider'] == 'meta')
    assert second['costs']['meta']['cumulative_accounted_usd'] >= prior
    assert len(list((tmp_path / 'private/mock/runs').glob('*-plan.json'))) == 2
    config = json.loads((tmp_path / 'private/mock/runs' / first['run_id'] / 'config.json').read_text())
    assert config['model_lock']['providers'][0]['model'] == 'muse-spark-1.3'
    assert {'runner.py', 'repro.py', 'code_checks.py'} <= config['evaluator_sources_sha256'].keys()
    assert len(config['system_prompt_sha256']) == 64 and len(config['case_prompts'][0]['user_prompt_sha256']) == 64


def test_one_error_continues_others_and_failed_key_never_automatically_retries(tmp_path):
    files, calls = fixture(tmp_path), []
    async def wire(provider, request, key):
        calls.append(provider.provider)
        if provider.provider == 'anthropic':
            raise transport.JudgeError('http_error', http_status=429, request_id='unit-failure')
        return envelope(provider, marks(requested(request, provider.provider)))
    result = execute(tmp_path, files, wire)
    assert len(calls) == 3
    assert result['cases'][0]['criteria']['D']['mode'] == 'degraded_two'
    assert result['costs']['anthropic']['run_accounted_usd'] > 0
    assert len(list((tmp_path / 'private/mock/cache').glob('*.json'))) == 2
    again = execute(tmp_path, files, wire)
    assert len(calls) == 3
    assert again['cases'][0]['provider_status']['anthropic'] == 'budget_denied'


def test_missing_process_keys_do_not_invent_zero_usage_or_score(tmp_path):
    files = fixture(tmp_path)
    report = asyncio.run(runner.run(*files, execute=True, allow_network=True,
        private_root=tmp_path / 'private', report_root=tmp_path / 'reports'))
    assert report['provider_requests_made'] == 0
    assert set(report['cases'][0]['provider_status'].values()) == {'unavailable'}
    assert report['cases'][0]['criteria']['D']['mean'] is None
    prior = next(p['prior_spend_usd'] for p in model_lock()['providers'] if p['provider'] == 'meta')
    assert report['costs']['meta']['cumulative_accounted_usd'] == prior


@pytest.mark.parametrize('bad', ['not json', '```json\n{}\n```', '{"assessments":[],"extra":true}',
    '{"assessments":[],"assessments":[]}', json.dumps(marks(['A', 'A', 'D']))])
def test_invalid_judgement_never_repairs_or_enters_success_cache(tmp_path, bad):
    files, calls = fixture(tmp_path), []
    async def wire(provider, request, key):
        calls.append(provider.provider)
        return envelope(provider, bad)
    result = execute(tmp_path, files, wire)
    assert len(calls) == 3
    assert set(result['cases'][0]['provider_status'].values()) == {'failed'}
    assert list((tmp_path / 'private/mock/cache').glob('*.json')) == []


@pytest.mark.parametrize('index', [0, 1, 2])
def test_all_protocols_strict_success_refusal_and_model_mismatch(index):
    provider = schema.ModelLock.model_validate(model_lock()).providers[index]
    good = envelope(provider, marks(['B', 'D']))
    result, info = transport.parse(provider, good, ['B', 'D'])
    assert len(result['assessments']) == 2 and info['usage']['input_tokens'] == 50
    wrong = deepcopy(good)
    wrong['body']['model'] = 'not-the-locked-model'
    with pytest.raises(transport.JudgeError, match='model_mismatch'):
        transport.parse(provider, wrong, ['B', 'D'])
    refusal = deepcopy(good)
    if index == 0: refusal['body']['choices'][0]['message']['refusal'] = 'Unit refusal'
    elif index == 1: refusal['body']['stop_reason'] = 'refusal'
    else: refusal['body']['output'][0]['content'] = [{'type': 'refusal', 'refusal': 'Unit refusal'}]
    with pytest.raises(transport.JudgeError, match='refusal'):
        transport.parse(provider, refusal, ['B', 'D'])


def test_cache_is_bound_to_full_prompt_pixels_model_settings_and_rubric(tmp_path):
    files = fixture(tmp_path)
    _, loaded = schema.load_inputs(files[0])
    case, images = loaded[0]
    p = schema.ModelLock.model_validate(model_lock()).providers[0]
    system, user, criteria = prompt(case, images, 'poll-v1')
    wire = schema.output_schema(criteria)
    base = cache_identity(p, system, user, images, 'poll-v1', wire, 'mock')
    assert cache_identity(p, system, user + ' changed', images, 'poll-v1', wire, 'mock') != base
    assert cache_identity(p, system, user, [{**images[0], 'sha256': 'a' * 64}], 'poll-v1', wire, 'mock') != base
    assert cache_identity(p.model_copy(update={'settings': {'reasoning_effort': 'low'}}), system, user, images, 'poll-v1', wire, 'mock') != base
    assert cache_identity(p, system, user, images, 'poll-v1', wire, 'live') != base


def test_tampered_cached_rating_rejected_without_new_request(tmp_path):
    files, calls = fixture(tmp_path), []
    async def wire(provider, request, key):
        calls.append(provider.provider)
        return envelope(provider, marks(requested(request, provider.provider)))
    execute(tmp_path, files, wire)
    cache = next((tmp_path / 'private/mock/cache').glob('*.json'))
    body = json.loads(cache.read_text())
    body['judgement']['assessments'][0]['score'] = 1
    cache.write_text(json.dumps(body), encoding='utf-8')
    again = execute(tmp_path, files, wire)
    assert len(calls) == 3
    assert 'invalid_cache' in again['cases'][0]['provider_status'].values()


def test_budget_reservation_durable_unknown_failure_and_no_reset(tmp_path):
    provider = schema.ModelLock.model_validate(model_lock()).providers[0]
    book = Book(tmp_path)
    request = {'model': provider.model, 'max_completion_tokens': 100}
    request_id, amount = book.reserve(provider, 'run-one', 'key-one', request)
    assert amount > 0 and book.events()[-1]['event'] == 'reserved'
    assert book.balances(book.events(), 'meta') == Decimal(str(provider.prior_spend_usd)) + amount
    book.settle(provider, request_id, amount, None, 'failed')
    assert book.balances(book.events(), 'meta') == Decimal(str(provider.prior_spend_usd)) + amount
    with pytest.raises(BudgetDenied, match='previous_attempt'):
        book.reserve(provider, 'run-two', 'key-one', request)
    with pytest.raises(BudgetDenied, match='cannot_be_reset'):
        book.reserve(provider.model_copy(update={'prior_spend_usd': 0}), 'run-two', 'key-two', request)


def test_provider_ceiling_and_run_allocation_deny_before_call(tmp_path):
    p = schema.ModelLock.model_validate(model_lock()).providers[0]
    book = Book(tmp_path)
    with pytest.raises(BudgetDenied, match='cumulative_ceiling'):
        book.reserve(p.model_copy(update={'prior_spend_usd': 9.99999}), 'r', 'one', {})
    book2 = Book(tmp_path / 'allocation')
    with pytest.raises(BudgetDenied, match='run_allocation'):
        book2.reserve(p.model_copy(update={'allocation_usd': .0000001}), 'r', 'two', {})


def test_code_verdict_is_recomputed_before_execution_not_trusted_from_input(tmp_path):
    files = fixture(tmp_path)
    value = json.loads(files[0].read_text())
    value['cases'][0]['deterministic']['C']['status'] = 'pass'
    files[0].write_text(json.dumps(value), encoding='utf-8')
    async def wire(*a): pytest.fail('No network before code provenance matches')
    with pytest.raises(ValueError, match='recomputation'):
        execute(tmp_path, files, wire)
    assert not (tmp_path / 'private').exists()


def test_endpoint_keys_and_families_cannot_be_configured_around_allowlist():
    lock = model_lock()
    lock['providers'][0]['endpoint'] = 'https://example.invalid/collect'
    with pytest.raises(ValueError): schema.ModelLock.model_validate(lock)
    lock = model_lock()
    lock['providers'][2] = deepcopy(lock['providers'][1])
    with pytest.raises(ValueError): schema.ModelLock.model_validate(lock)


def test_protected_path_rejected_before_any_target_read(tmp_path):
    with pytest.raises(ValueError, match='Protected'):
        schema.load_inputs(tmp_path / 'heldout' / 'never-open.json')


def test_link_is_rejected_before_resolving_target(tmp_path, monkeypatch):
    path = tmp_path / 'linked-input.json'
    original = Path.is_symlink
    monkeypatch.setattr(Path, 'is_symlink', lambda self: True if self == path else original(self))
    with pytest.raises(ValueError, match='Linked'):
        schema.checked_path(path)


def test_wire_settings_do_not_enable_tools_or_persistence(tmp_path):
    files = fixture(tmp_path)
    _, cases = schema.load_inputs(files[0])
    case, images = cases[0]
    system, user, criteria = prompt(case, images, 'poll-v1')
    for p in schema.ModelLock.model_validate(model_lock()).providers:
        request = transport.payload(p, system, user, images, schema.output_schema(criteria))
        assert 'tools' not in request and 'previous_response_id' not in request
        if p.provider == 'openai': assert request['store'] is False and request['reasoning'] == {'effort': 'none'}
        if p.provider == 'anthropic':
            assert request['thinking'] == {'type': 'between_tools'}
            assert request['output_config']['effort'] == 'low'


def test_secret_scrubbing_never_changes_numeric_judgement():
    result = runner.scrub({'score': 4, 'reason': 'echo unit-secret-only', 'nested': ['unit-secret-only']}, 'unit-secret-only')
    assert result == {'score': 4, 'reason': 'echo [REDACTED]', 'nested': ['[REDACTED]']}


def test_git_identity_child_never_inherits_provider_credentials(monkeypatch):
    from types import SimpleNamespace
    names = ('MODEL_API_KEY', 'MODUS_META_KEY', 'ANTHROPIC_API_KEY', 'OPENAI_API_KEY')
    for name in names:
        monkeypatch.setenv(name, 'unit-canary-never-send')
    def fake_run(args, **kwargs):
        assert args == ['git', 'rev-parse', '--verify', 'HEAD']
        assert not set(names).intersection(kwargs['env'])
        assert kwargs['env']['MODUS_PROVIDER'] == 'offline'
        assert kwargs['env']['PYTHON_DOTENV_DISABLED'] == '1'
        return SimpleNamespace(returncode=0, stdout='a' * 40)
    monkeypatch.setattr(repro.subprocess, 'run', fake_run)
    assert repro.snapshot([], 'poll-v1')['source_commit'] == 'a' * 40


def test_spaced_model_names_and_legacy_route_names_are_blinded():
    from eval.judges.prompts import blinded
    assert blinded('Muse Spark; Claude Sonnet 5.5; meta_agent; meta_record_review') == '[provider withheld]; [provider withheld]; [provider withheld]; [provider withheld]'
    assert blinded('metabolic panel: 10.5 mg/dL') == 'metabolic panel: 10.5 mg/dL'

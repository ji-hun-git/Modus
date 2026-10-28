"""Budget/admission checks using artificial transports and new temporary metadata only.

No existing benchmark suite, label, freeze or access ledger is read by these tests.
"""
import asyncio
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
from benchmark_common import Budget, BudgetExceeded, canonical, estimated_cost, validate_suite
import benchmark_cli as cli
from benchmark_runner import GuardedTransport
from modus.provider import MetaRequestError, ProviderResponse


MODEL = 'muse-spark-1.3'


def payload():
    return {'model': MODEL, 'messages': [{'role': 'user', 'content': 'Authored synthetic request.'}],
        'max_completion_tokens': 100}


def reply(usage=None, model=MODEL):
    return ProviderResponse({'id': 'artificial-response-1', 'model': model,
        'choices': [{'finish_reason': 'stop', 'message': {'content': '{}'}}],
        **({'usage': usage} if usage is not None else {})}, 200, 'artificial-request-1')


def records(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()]


def test_estimated_cap_denies_before_wire_and_preserves_attempt_reason(tmp_path):
    sent = []
    async def wire(value):
        sent.append(value)
        return reply()
    budget = Budget(10, 1000, max_estimated_usd=0.000001)
    ledger = tmp_path / 'events.jsonl'
    guard = GuardedTransport(budget, MODEL, ledger, 'new-attempt', transport=wire)
    with pytest.raises(BudgetExceeded, match='Estimated-dollar'):
        asyncio.run(guard(payload()))
    assert sent == [] and guard.calls == [] and budget.calls == 0
    assert budget.output_reserved == 0 and budget.estimated_usd_accounted == 0
    assert records(ledger)[0]['event'] == 'request_denied'
    assert records(ledger)[0]['error_kind'] == 'budget_exceeded'


@pytest.mark.parametrize('usage', [None, {'prompt_tokens': 1}, {'completion_tokens': 1}, {'prompt_tokens': True, 'completion_tokens': 1}])
def test_unknown_or_partial_usage_keeps_full_reservation(tmp_path, usage):
    async def wire(_): return reply(usage)
    budget = Budget(10, 1000, max_estimated_usd=1)
    guard = GuardedTransport(budget, MODEL, tmp_path / 'events.jsonl', 'unknown', transport=wire)
    asyncio.run(guard(payload()))
    expected = estimated_cost(len(canonical(payload()).encode('utf-8')), 100)
    assert budget.estimated_usd_accounted == expected
    assert guard.calls[0]['estimated_cost_usd'] == float(expected)
    assert guard.calls[0]['cost_basis'] == 'preflight_reservation_retained_usage_unknown'


def test_known_usage_replaces_reservation_and_records_sanitized_metadata(tmp_path):
    async def wire(_): return reply({'prompt_tokens': 10, 'completion_tokens': 3, 'total_tokens': 13})
    budget = Budget(10, 1000, max_estimated_usd=1)
    ledger = tmp_path / 'events.jsonl'
    guard = GuardedTransport(budget, MODEL, ledger, 'known', transport=wire)
    asyncio.run(guard(payload()))
    assert budget.estimated_usd_accounted == estimated_cost(10, 3)
    call = guard.calls[0]
    assert call['response_id'] == 'artificial-response-1'
    assert call['request_id'] == 'artificial-request-1' and call['http_status'] == 200
    assert call['error_kind'] is None and call['usage']['total_tokens'] == 13
    assert call['estimated_cost_usd'] == float(estimated_cost(10, 3))
    assert call['cost_basis'] == 'reported_token_usage_at_standard_prices'
    assert records(ledger)[0]['cost_reservation_basis'].endswith('not a tokenizer or billing guarantee.')


def test_failed_request_keeps_cost_reservation_and_http_evidence_without_raw_error(tmp_path):
    async def wire(_):
        raise MetaRequestError('http_error', http_status=429, request_id='artificial-failure-request')
    budget = Budget(10, 1000, max_estimated_usd=1)
    ledger = tmp_path / 'events.jsonl'
    guard = GuardedTransport(budget, MODEL, ledger, 'failed', transport=wire)
    with pytest.raises(MetaRequestError): asyncio.run(guard(payload()))
    call = guard.calls[0]
    assert call['status'] == 'failed' and call['error_kind'] == 'http_error'
    assert call['http_status'] == 429 and call['request_id'] == 'artificial-failure-request'
    assert call['usage'] is None and call['cost_basis'].startswith('preflight_reservation_retained')
    assert budget.estimated_usd_accounted > 0 and len(records(ledger)) == 2


def test_explicit_wrong_model_fails_with_metadata_and_no_retry(tmp_path):
    async def wire(_): return reply({'prompt_tokens': 2, 'completion_tokens': 1}, model='different-model')
    guard = GuardedTransport(Budget(5, 1000), MODEL, tmp_path / 'events.jsonl', 'model', transport=wire)
    with pytest.raises(MetaRequestError) as raised: asyncio.run(guard(payload()))
    assert raised.value.error_kind == 'model_mismatch'
    assert len(guard.calls) == 1 and guard.calls[0]['status'] == 'failed'
    assert guard.calls[0]['returned_model'] == 'different-model'
    assert guard.calls[0]['request_id'] == 'artificial-request-1'


def test_actual_usage_above_proxy_retained_then_blocks_further_requests(tmp_path):
    sent = []
    async def wire(value):
        sent.append(value)
        return reply({'prompt_tokens': 1_000_000, 'completion_tokens': 1})
    guard = GuardedTransport(Budget(5, 1000, max_estimated_usd=0.01), MODEL,
        tmp_path / 'events.jsonl', 'overrun', transport=wire)
    asyncio.run(guard(payload()))
    assert guard.calls[0]['estimated_cost_limit_exceeded'] is True
    with pytest.raises(BudgetExceeded): asyncio.run(guard(payload()))
    assert len(sent) == 1 and guard.global_budget_exhausted


def test_two_pass_method_limit_is_enforced_in_addition_to_global_limits(tmp_path):
    async def wire(_): return reply()
    guard = GuardedTransport(Budget(10, 10000), MODEL, tmp_path / 'events.jsonl', 'two-pass',
        max_request_output=4000, max_requests=2, transport=wire)
    asyncio.run(guard(payload()))
    asyncio.run(guard(payload()))
    with pytest.raises(BudgetExceeded): asyncio.run(guard(payload()))
    assert len(guard.calls) == 2 and guard.local.calls == 2


@pytest.mark.parametrize('limit', [0, -1, float('nan'), float('inf'), True])
def test_cost_limits_must_be_positive_finite_numbers(limit):
    with pytest.raises(ValueError): Budget(1, 100, max_estimated_usd=limit)


def args(tmp_path, **changes):
    return SimpleNamespace(suite=tmp_path / 'authored-suite', split='holdout', methods=['local_parser', 'meta_direct', 'meta_record_review'],
        repeats=1, execute=True, allow_network=True, max_requests=24, max_output_tokens=96000,
        max_estimated_usd=3.0, model=MODEL, unlock_holdout=True, holdout_reason='Explicit artificial test admission.',
        reuse_holdout=False, out=tmp_path / 'runs', **changes)


def isolated_cli(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, 'ROOT', tmp_path)
    monkeypatch.setenv('MODEL_API_KEY', 'artificial-not-a-live-key')
    suite = tmp_path / 'authored-suite'
    suite.mkdir()
    raw = b'{"authored_metadata_only":true}'
    (suite / 'freeze.json').write_bytes(raw)
    freeze_id = hashlib.sha256(raw).hexdigest()
    access = tmp_path / 'evaluation' / 'holdout-access.jsonl'
    data = {'version': 'artificial-only', 'cases': [{'id': 'a', 'family_id': 'family-a'}]}
    def validated(*_a, **_k):
        assert records(access)[-1]['event'] == 'holdout_opening_started'
        assert _k['expected_freeze_id'] == freeze_id
        return {'freeze_id': freeze_id, 'holdout': data, 'files_sha256': {}}
    monkeypatch.setattr(cli, 'validate_suite', validated)
    def make_plan(kind, suite, split, cases, methods, repeats, model, budget):
        return {'schedule': [{'case_id': case['id'], 'method': method, 'repeat': 1} for case in cases for method in methods],
            'budget': budget, 'model': model}
    monkeypatch.setattr(cli, 'make_plan', make_plan)
    monkeypatch.setattr(cli, 'prepare_run', lambda output, plan: tmp_path / 'prepared')
    return access, freeze_id


@pytest.mark.parametrize('change', [{'execute': False}, {'unlock_holdout': False}, {'allow_network': False},
    {'max_requests': 0}, {'max_output_tokens': 0}, {'max_estimated_usd': float('nan')}, {'model': 'unpriced-model'}])
def test_preflight_rejects_before_any_suite_or_freeze_access(tmp_path, monkeypatch, change):
    monkeypatch.setenv('MODEL_API_KEY', 'artificial-not-a-live-key')
    def prohibited(*_a, **_k): pytest.fail('Preflight must fail before any suite or freeze read')
    monkeypatch.setattr(cli, 'validate_suite', prohibited)
    monkeypatch.setattr(cli, 'safe_path', prohibited)
    value = args(tmp_path)
    for key, item in change.items(): setattr(value, key, item)
    with pytest.raises(ValueError): cli.plan_run(value, 'documents')


def test_missing_access_key_fails_before_suite_access(tmp_path, monkeypatch):
    monkeypatch.setenv('MODEL_API_KEY', '')
    monkeypatch.setattr(cli, 'safe_path', lambda *_a: pytest.fail('No freeze read without access preflight'))
    monkeypatch.setattr(cli, 'validate_suite', lambda *_a, **_k: pytest.fail('No selected-input read'))
    with pytest.raises(ValueError, match='access locally'): cli.plan_run(args(tmp_path), 'documents')


def test_benchmark_preflight_accepts_only_preferred_meta_alias_before_admission(tmp_path, monkeypatch):
    isolated_cli(tmp_path, monkeypatch)
    monkeypatch.setenv('MODEL_API_KEY', '')
    monkeypatch.setenv('MODUS_META_KEY', 'artificial-preferred-key')
    plan, _, _, _ = cli.plan_run(args(tmp_path), 'documents')
    assert plan['model'] == MODEL


def test_admission_precedes_selected_input_and_records_protocol_and_two_pass_cap(tmp_path, monkeypatch):
    access, _ = isolated_cli(tmp_path, monkeypatch)
    plan, _, _, public = cli.plan_run(args(tmp_path), 'documents')
    events = records(access)
    assert [row['event'] for row in events] == ['holdout_opening_started', 'holdout_opening_completed']
    assert plan['gold_review_status'] == events[0]['gold_review_status'] == 'AI-authored; independent human review pending'
    assert plan['prior_holdout_exposures'] == 0 and plan['budget']['max_estimated_usd'] == 3
    assert public['possible_max_requests'] == 3  # 0 local +1 legacy +2 production.
    assert plan['budget']['method_request_limits']['meta_record_review'] == 2
    assert 'not graded as eight-kind' in plan['grading_scope']
    monkeypatch.setattr(cli, 'validate_suite', lambda *_a, **_k: pytest.fail('Reuse must fail before input read'))
    with pytest.raises(ValueError, match='already admitted'): cli.plan_run(args(tmp_path), 'documents')
    assert len(records(access)) == 2


def test_failed_admission_remains_an_exposure_and_does_not_log_raw_errors(tmp_path, monkeypatch):
    access, _ = isolated_cli(tmp_path, monkeypatch)
    def failed(*_a, **_k):
        assert records(access)[-1]['event'] == 'holdout_opening_started'
        raise ValueError('PRIVATE_FAILURE_TEXT')
    monkeypatch.setattr(cli, 'validate_suite', failed)
    with pytest.raises(ValueError, match='PRIVATE_FAILURE_TEXT'): cli.plan_run(args(tmp_path), 'documents')
    assert [row['event'] for row in records(access)] == ['holdout_opening_started', 'holdout_opening_failed']
    assert 'PRIVATE_FAILURE_TEXT' not in access.read_text(encoding='utf-8')
    with pytest.raises(ValueError, match='already admitted'): cli.plan_run(args(tmp_path), 'documents')


def test_admission_persistence_failure_prevents_input_access(tmp_path, monkeypatch):
    isolated_cli(tmp_path, monkeypatch)
    monkeypatch.setattr(cli, 'event', lambda *_a, **_k: (_ for _ in ()).throw(OSError('artificial disk failure')))
    monkeypatch.setattr(cli, 'validate_suite', lambda *_a, **_k: pytest.fail('No durable admission, no input read'))
    with pytest.raises(OSError): cli.plan_run(args(tmp_path), 'documents')


def test_concurrent_or_interrupted_admission_blocks_input_access(tmp_path, monkeypatch):
    access, _ = isolated_cli(tmp_path, monkeypatch)
    access.parent.mkdir()
    access.with_name('.holdout-admission.lock').write_text('artificial stale lock', encoding='utf-8')
    monkeypatch.setattr(cli, 'validate_suite', lambda *_a, **_k: pytest.fail('Locked admission cannot read inputs'))
    with pytest.raises(ValueError, match='interrupted'): cli.plan_run(args(tmp_path), 'documents')


def test_changed_freeze_identity_rejects_before_any_selected_input_read(tmp_path, monkeypatch):
    metadata = tmp_path / 'freeze.json'
    metadata.write_text('{"artificial_metadata":"changed"}', encoding='utf-8')
    original_open = Path.open
    observed = []
    def guarded_open(path, *a, **kw):
        assert path == metadata, 'A changed freeze must not open any selected split or input'
        observed.append(path.name)
        return original_open(path, *a, **kw)
    monkeypatch.setattr(Path, 'open', guarded_open)
    with pytest.raises(ValueError, match='selected inputs were not opened'):
        validate_suite(tmp_path, 'documents', selected_split='holdout', expected_freeze_id='0' * 64)
    assert observed == ['freeze.json']

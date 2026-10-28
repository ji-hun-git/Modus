"""C1/C2 fixed smoke contract. All model responses are artificial transports."""
import asyncio
import io
import json
from pathlib import Path
import sys

import httpx
from PIL import Image
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
import smoke_record_extraction as smoke
from modus import provider
from modus.record_store import RecordStore


@pytest.fixture(autouse=True)
def isolated(monkeypatch):
    async def forbidden(*_args, **_kwargs):
        pytest.fail('No real network in smoke tests')
    def no_configuration():
        pytest.fail('Injected mock/preparation must not read local credentials')
    monkeypatch.setattr(provider.httpx.AsyncClient, 'post', forbidden)
    monkeypatch.setattr(smoke.legacy, 'load_live_configuration', no_configuration)
    monkeypatch.setattr(smoke.agent, 'provider_status', lambda: {'model': smoke.MODEL, 'mode': 'meta'})


def response(content=None, tool=None, args=None):
    message = {'content': json.dumps(content) if content is not None else None}
    if tool:
        message['tool_calls'] = [{'id': 'artificial-call', 'type': 'function',
            'function': {'name': tool, 'arguments': json.dumps(args or {})}}]
    return {'id': 'artificial-response', 'model': smoke.MODEL,
            'usage': {'prompt_tokens': 100, 'completion_tokens': 20, 'total_tokens': 120},
            'choices': [{'finish_reason': 'tool_calls' if tool else 'stop', 'message': message}]}


def transport(*, verification='supported', wrong_value=False, verifier_timeout=False):
    seen = []
    async def request(payload):
        seen.append(payload)
        if len(seen) == 1:
            return response({'extraction': {'document_type': 'lab_report', 'fields': [{
                'kind': 'measurement', 'label': 'HbA1c', 'value': '8.9' if wrong_value else '5.6',
                'unit': '%', 'occurred_on': '2024-02-03', 'source_quote': smoke.legacy.SPAN,
                'page': 1, 'bbox': None, 'model_confidence': None}]}})
        if len(seen) == 2:
            if verifier_timeout:
                raise httpx.ReadTimeout('PRIVATE_EXCEPTION_NOT_FOR_EVIDENCE')
            return response({'checks': [{'field_id': 'field-1', 'status': verification,
                                         'reason': 'matches_source' if verification == 'supported' else 'unclear_source'}]})
        if len(seen) == 3:
            return response(tool='record_inventory')
        return response(tool='select_claims', args={'claim_ids': ['inventory-all']})
    return request, seen


@pytest.mark.parametrize('input_mode', ['pdf', 'image'])
def test_prepare_no_credentials_or_requests(tmp_path, monkeypatch, input_mode):
    def forbidden():
        pytest.fail('Preparation cannot inspect provider configuration')
    monkeypatch.setattr(smoke, 'provider_status', forbidden)
    report = asyncio.run(smoke.run(tmp_path / 'plan.json', input_mode=input_mode))
    assert report['status'] == 'prepared' and report['provider_requests_made'] == 0
    assert report['max_requests'] == 8 and report['max_reserved_output_tokens'] == 17600
    assert report['input_mode'] == input_mode and report['automatic_commit'] is False
    assert report['live_path_verified'] is report['model_performance_measured'] is False
    raw, _, mime = smoke.document(input_mode)
    if input_mode == 'image':
        assert mime == 'image/png'
        assert Image.open(io.BytesIO(raw)).size == (918, 1188)


def test_missing_network_opt_in_blocks_before_config(tmp_path):
    report = asyncio.run(smoke.run(tmp_path / 'blocked.json', execute=True))
    assert report['error_kind'] == 'network_not_authorized'
    assert report['provider_requests_attempted'] == 0 and report['stages'] == []


def test_missing_credentials_blocks_with_zero_attempts(tmp_path, monkeypatch):
    monkeypatch.setattr(smoke.legacy, 'load_live_configuration', lambda: None)
    monkeypatch.setattr(smoke, 'provider_status', lambda: {'key_configured': False})
    report = asyncio.run(smoke.run(tmp_path / 'missing.json', execute=True, allow_network=True))
    assert report['status'] == 'blocked' and report['error_kind'] == 'credentials_not_configured'
    assert report['provider_requests_made'] == report['provider_requests_attempted'] == 0
    assert report['execution_class'] == 'preparation' and report['stages'] == []


@pytest.mark.parametrize('input_mode', ['pdf', 'image'])
def test_successful_mock_is_never_live_and_does_not_commit(tmp_path, monkeypatch, input_mode):
    def forbidden(*_args, **_kwargs):
        pytest.fail('A smoke draft must never be committed')
    monkeypatch.setattr(RecordStore, 'commit_draft', forbidden)
    request, seen = transport()
    path = tmp_path / 'mock.json'
    report = asyncio.run(smoke.run(path, input_mode=input_mode, execute=True, request=request))
    assert report['status'] == 'passed' and len(seen) == 4
    assert report['execution_class'] == 'mock_transport_test' and report['live_path_verified'] is False
    assert report['provider_requests_made'] == report['provider_requests_attempted'] == 0
    assert report['reserved_output_tokens'] == 11200
    assert report['records_unchanged'] and report['committed_imports'] == 0
    assert all(stage['status'] == 'passed' for stage in report['stages'])
    assert report['stages'][0]['extract_only_authored_fields_match'] is True
    assert report['stages'][0]['review_still_required'] is True
    assert report['cost']['uncached_usage_estimate_usd'] is None
    assert report['cost']['billed_cost_usd'] is None
    assert '2024-02-03' not in json.dumps(seen[2]['messages'])
    assert json.loads(path.read_text(encoding='utf-8')) == report
    with pytest.raises(ValueError, match='already exists'):
        asyncio.run(smoke.run(path, execute=True, request=request))
    assert len(seen) == 4


@pytest.mark.parametrize('options', [{'verification': 'uncertain'}, {'wrong_value': True}, {'verifier_timeout': True}])
def test_failed_verification_retains_extraction_but_stops_before_tool_loop(tmp_path, options):
    request, seen = transport(**options)
    path = tmp_path / 'failure.json'
    report = asyncio.run(smoke.run(path, input_mode='pdf', execute=True, request=request))
    assert report['status'] == 'failed' and len(seen) == 2
    assert len(report['stages']) == 1 and 'draft' in report['stages'][0]
    assert report['stages'][0]['draft']['review_required'] is True
    assert report['committed_imports'] == 0 and report['live_path_verified'] is False
    assert 'PRIVATE_EXCEPTION' not in path.read_text(encoding='utf-8')


def test_first_pass_timeout_is_sanitized_and_not_retried(tmp_path):
    attempts = []
    async def request(payload):
        attempts.append(payload)
        raise httpx.ReadTimeout('PRIVATE_TIMEOUT')
    path = tmp_path / 'timeout.json'
    report = asyncio.run(smoke.run(path, execute=True, request=request))
    assert report['status'] == 'failed' and report['error_kind'] == 'timeout'
    assert len(attempts) == 1 and 'PRIVATE_TIMEOUT' not in path.read_text(encoding='utf-8')


def test_output_reservation_blocks_before_second_request(tmp_path):
    request, seen = transport()
    report = asyncio.run(smoke.run(tmp_path / 'budget.json', execute=True, request=request, max_output_tokens=4000))
    assert report['status'] == 'failed' and len(seen) == 1
    assert report['blocked_requests'] == 1 and report['reserved_output_tokens'] == 4000


def test_request_bounds_reject_payload_and_wrong_model_before_transport():
    async def forbidden(_payload):
        pytest.fail('Rejected request must never reach transport')
    for limits in ({'max_requests': 9}, {'max_output_tokens': 17601}):
        with pytest.raises(ValueError):
            smoke.BoundedRequest(forbidden, **limits)
    bounded = smoke.BoundedRequest(forbidden)
    for payload in ({'model': 'other', 'max_completion_tokens': 1},
                    {'model': smoke.MODEL, 'max_completion_tokens': 1, 'messages': ['x' * smoke.MAX_PAYLOAD_BYTES]}):
        with pytest.raises(provider.MetaRequestError):
            asyncio.run(bounded(payload))
    assert bounded.calls == 0


def test_cost_is_usage_derived_upper_estimate_or_unknown_never_invoice():
    stages = [{'telemetry': {'calls': [{'usage': {'prompt_tokens': 1000, 'completion_tokens': 200}}]}}]
    result = smoke.token_cost(stages, mocked=False, attempted=1)
    assert result['uncached_usage_estimate_usd'] == 0.0021 and result['billed_cost_usd'] is None
    assert smoke.token_cost(stages, mocked=False, attempted=2)['uncached_usage_estimate_usd'] is None
    assert smoke.token_cost(stages, mocked=True, attempted=1)['uncached_usage_estimate_usd'] is None
    assert smoke.token_cost([], mocked=False, attempted=0)['uncached_usage_estimate_usd'] == 0

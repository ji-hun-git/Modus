"""Artificial transports only. No private corpora, credentials or provider calls."""
import asyncio
import importlib
import io
import json
from pathlib import Path
import sys

import httpx
from pypdf import PdfReader
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
import smoke_entry_meta as smoke
from modus import provider
from modus.extraction import extract_document
from modus.record_store import RecordStore
from modus_entry import agent
from modus_entry.seed import initial_data
from modus_entry.tools import capture


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    async def forbidden(*_args, **_kwargs):
        pytest.fail('No real transport is permitted in these tests')
    monkeypatch.setattr(provider.httpx.AsyncClient, 'post', forbidden)
    monkeypatch.setattr(agent, 'provider_status', lambda: {'model': smoke.MODEL, 'mode': 'meta'})
    def no_configuration(*_args, **_kwargs):
        pytest.fail('Preparation and injected mocks must not read root .env')
    monkeypatch.setattr(smoke, 'load_dotenv', no_configuration)


def completion(*, content=None, tool=None, args=None, finish='stop', refusal=None):
    message = {'content': content}
    if tool is not None:
        message['tool_calls'] = [{'id': 'call-artificial', 'type': 'function',
                                  'function': {'name': tool, 'arguments': json.dumps(args or {})}}]
    if refusal is not None:
        message['refusal'] = refusal
    return {'id': 'response-artificial', 'model': 'reported-artificial-model',
            'usage': {'prompt_tokens': 12, 'completion_tokens': 5, 'total_tokens': 17},
            'choices': [{'finish_reason': finish, 'message': message}]}


def success_transport():
    seen = []
    async def request(payload):
        seen.append(payload)
        if len(seen) == 1:
            return completion(content=json.dumps({'observations': [smoke.EXPECTED]}))
        if len(seen) == 2:
            return completion(tool='record_inventory', finish='tool_calls')
        return completion(tool='select_claims', args={'claim_ids': ['inventory-all']}, finish='tool_calls')
    return request, seen


def test_preparation_never_reads_provider_configuration_or_calls(tmp_path, monkeypatch):
    def forbidden():
        pytest.fail('Preparation must not inspect credentials or provider state')
    monkeypatch.setattr(agent, 'provider_status', forbidden)
    monkeypatch.setattr(provider, 'provider_status', forbidden)
    report = asyncio.run(smoke.run(tmp_path / 'plan.json'))
    assert report['status'] == 'prepared' and report['provider_requests_made'] == 0
    assert report['max_requests'] == 7 and report['max_reserved_output_tokens'] == 13600
    assert report['model_performance_measured'] is False and report['live_path_verified'] is False
    assert report['retries'] == 0 and report['automatic_commit'] is False
    text = PdfReader(io.BytesIO(smoke.synthetic_pdf())).pages[0].extract_text()
    assert smoke.SPAN in text and 'AUTHORED SYNTHETIC' in text


def test_execute_without_network_permission_persists_block(tmp_path):
    report = asyncio.run(smoke.run(tmp_path / 'blocked.json', execute=True))
    assert report['status'] == 'blocked' and report['provider_requests_made'] == 0
    assert json.loads((tmp_path / 'blocked.json').read_text()) == report


@pytest.mark.parametrize('allow_network', [False, True])
def test_mock_smoke_proves_bounded_path_but_never_claims_live_or_commits(tmp_path, monkeypatch, allow_network):
    def no_commit(*_args, **_kwargs):
        pytest.fail('Smoke must never commit an extraction')
    monkeypatch.setattr(RecordStore, 'commit_draft', no_commit)
    request, seen = success_transport()
    report = asyncio.run(smoke.run(tmp_path / 'mock.json', execute=True, allow_network=allow_network, request=request))
    assert report['status'] == 'passed' and len(seen) == 3
    assert report['execution_class'] == 'mock_transport_test'
    assert report['live_path_verified'] is report['model_performance_measured'] is False
    assert report['provider_requests_made'] == 0
    assert report['reserved_output_tokens'] == 7200
    assert report['committed_imports'] == 0 and report['records_unchanged'] is True
    assert report['stages'][0]['review_required'] and report['stages'][0]['committed'] is False
    assert report['stages'][1]['claims'][0]['id'] == 'inventory-all'
    assert '2024-02-03' not in json.dumps(seen[1]['messages'])
    assert json.loads((tmp_path / 'mock.json').read_text()) == report
    with pytest.raises(ValueError, match='already exists'):
        asyncio.run(smoke.run(tmp_path / 'mock.json', execute=True, request=request))
    assert len(seen) == 3


def test_live_configuration_helper_uses_root_dotenv_without_overriding_environment(monkeypatch):
    # Test the loader in isolation: no root .env read, adapter call, or live-labelled report.
    observed = []
    monkeypatch.setattr(smoke, 'load_dotenv', lambda path, **kwargs: observed.append((path, kwargs)))
    smoke.load_live_configuration()
    assert observed == [(smoke.ROOT / '.env', {'override': False})]


@pytest.mark.parametrize('limits', [{'max_requests': 1}, {'max_output_tokens': 4000}])
def test_smoke_reserves_budget_before_call_and_never_retries(tmp_path, limits):
    request, seen = success_transport()
    report = asyncio.run(smoke.run(tmp_path / 'budget.json', execute=True, request=request, **limits))
    assert report['status'] == 'failed' and report['error_kind'] == 'budget_exceeded'
    assert len(seen) == report['transport_requests'] == 1
    assert report['blocked_requests'] == 1 and report['reserved_output_tokens'] == 4000
    assert report['records_unchanged'] and report['committed_imports'] == 0
    assert len(report['stages']) == 2 and report['stages'][0]['status'] == 'passed'


def test_extraction_failure_retained_and_no_agent_call(tmp_path):
    attempts = []
    async def request(payload):
        attempts.append(payload)
        raise httpx.ReadTimeout('ARTIFICIAL_SECRET_MUST_NOT_LEAK')
    path = tmp_path / 'failure.json'
    report = asyncio.run(smoke.run(path, execute=True, request=request))
    assert len(attempts) == 1 and report['status'] == 'failed'
    assert report['error_kind'] == 'timeout' and len(report['stages']) == 1
    assert report['stages'][0]['telemetry']['calls'][0]['usage'] is None
    assert 'ARTIFICIAL_SECRET' not in path.read_text()


@pytest.mark.parametrize('path', ['extraction', 'entry'])
@pytest.mark.parametrize('rejection', ['length', 'content_filter', 'unknown_finish', 'refusal'])
def test_both_deployed_consumers_reject_parseable_partial_or_refused_results(tmp_path, path, rejection):
    response = completion(content=json.dumps({'observations': [smoke.EXPECTED]}),
                          tool='select_claims', args={'claim_ids': []},
                          finish='stop' if rejection == 'refusal' else rejection,
                          refusal='ARTIFICIAL_PRIVATE_REFUSAL' if rejection == 'refusal' else None)
    async def request(_payload):
        return response
    telemetry = {'execution': smoke.execution_context('meta', smoke.MODEL)}
    if path == 'extraction':
        call = extract_document(smoke.synthetic_pdf(), 'test.pdf', 'application/pdf', telemetry, request=request)
    else:
        store = RecordStore(tmp_path / 'records.db', seed_provider=initial_data, clock=lambda: smoke.NOW)
        call = agent.live_chat(capture(store, smoke.DAY), smoke.QUESTION, telemetry, request=request)
    with pytest.raises(provider.MetaRequestError):
        asyncio.run(call)
    logged = telemetry['calls'][0]
    assert logged['status'] == 'failed' and logged['response_id'] == 'response-artificial'
    assert logged['usage']['total_tokens'] == 17 and logged['duration_ms'] >= 0
    assert logged['error_kind'] == ('refusal' if rejection == 'refusal' else 'incomplete')
    assert 'ARTIFICIAL_PRIVATE_REFUSAL' not in json.dumps(telemetry)


def install_http(monkeypatch, response=None, error=None):
    seen = []
    class Client:
        def __init__(self, **kwargs):
            assert kwargs['timeout'] == 45 and kwargs['verify'] is not False
        async def __aenter__(self):
            return self
        async def __aexit__(self, *_args):
            return None
        async def post(self, url, **kwargs):
            seen.append(url)
            assert url == 'https://api.meta.ai/v1/chat/completions'
            assert kwargs['headers']['Authorization'] == 'Bearer artificial-test-key'
            if error:
                raise error
            return response
    monkeypatch.setenv('MODEL_API_KEY', 'artificial-test-key')
    monkeypatch.setenv('MODUS_META_BASE_URL', 'https://api.meta.ai/v1')
    monkeypatch.setattr(provider.httpx, 'AsyncClient', Client)
    return seen


@pytest.mark.parametrize('status', [401, 429, 503])
def test_http_failures_keep_only_status_and_request_id(tmp_path, monkeypatch, status):
    response = httpx.Response(status, headers={'x-request-id': 'req-artificial', 'secret-header': 'DO_NOT_KEEP'},
                              text='PRIVATE_PROVIDER_BODY')
    seen = install_http(monkeypatch, response=response)
    telemetry = {}
    with pytest.raises(provider.MetaRequestError):
        asyncio.run(provider.measured_request({'model': smoke.MODEL}, telemetry))
    logged = telemetry['calls'][0]
    assert len(seen) == 1 and logged['http_status'] == status and logged['request_id'] == 'req-artificial'
    assert logged['error_kind'] == 'http_error' and logged['response_id'] is None
    assert logged['usage'] is None and telemetry['usage']['total_tokens'] is None
    assert 'PRIVATE_PROVIDER_BODY' not in json.dumps(telemetry) and 'DO_NOT_KEEP' not in json.dumps(telemetry)


@pytest.mark.parametrize('response,kind', [
    (httpx.Response(200, text='not-json'), 'invalid_json'),
    (httpx.Response(200, json=[]), 'invalid_envelope'),
    (httpx.Response(200, json={'choices': []}), 'invalid_envelope'),
])
def test_malformed_transport_payload_is_not_success(monkeypatch, response, kind):
    seen = install_http(monkeypatch, response=response)
    telemetry = {}
    with pytest.raises(provider.MetaRequestError):
        asyncio.run(provider.measured_request({'model': smoke.MODEL}, telemetry))
    assert len(seen) == 1 and telemetry['calls'][0]['error_kind'] == kind
    assert telemetry['calls'][0]['http_status'] == 200


def test_transport_timeout_no_retry_and_unknown_request_id(monkeypatch):
    seen = install_http(monkeypatch, error=httpx.ReadTimeout('PRIVATE_TIMEOUT_DETAIL'))
    telemetry = {}
    with pytest.raises(provider.MetaRequestError):
        asyncio.run(provider.measured_request({'model': smoke.MODEL}, telemetry))
    logged = telemetry['calls'][0]
    assert len(seen) == 1 and logged['error_kind'] == 'timeout'
    assert logged['request_id'] is None and logged['http_status'] is None
    assert 'PRIVATE_TIMEOUT_DETAIL' not in json.dumps(telemetry)


def test_metadata_survives_response_rejection_and_unsafe_ids_are_dropped(monkeypatch):
    data = completion(finish='length')
    data['id'] = 'unsafe\nidentifier'
    data['usage']['secret'] = 'NEVER_KEEP'
    seen = install_http(monkeypatch, response=httpx.Response(200, json=data, headers={'x-request-id': 'req-safe'}))
    telemetry = {}
    with pytest.raises(provider.MetaRequestError):
        asyncio.run(provider.measured_request({'model': smoke.MODEL}, telemetry))
    logged = telemetry['calls'][0]
    assert len(seen) == 1 and logged['response_id'] is None and logged['request_id'] == 'req-safe'
    assert logged['usage']['total_tokens'] == 17 and logged['finish_reason'] == 'length'
    assert logged['http_status'] == 200 and logged['status'] == 'failed'
    assert 'NEVER_KEEP' not in json.dumps(telemetry)


def test_legacy_mock_without_finish_metadata_remains_explicitly_unknown():
    async def request(_payload):
        return {'choices': [], 'usage': {}}
    telemetry = {}
    asyncio.run(provider.measured_request({'model': smoke.MODEL}, telemetry, request=request))
    assert telemetry['calls'][0]['finish_reason'] is None
    assert telemetry['calls'][0]['request_id'] is None


@pytest.mark.parametrize('malformed', ['extraction_json', 'tool_arguments'])
def test_valid_transport_with_malformed_payload_stays_failed(tmp_path, malformed):
    attempts = []
    async def request(payload):
        attempts.append(payload)
        if len(attempts) == 1:
            content = 'PRIVATE_MALFORMED_JSON' if malformed == 'extraction_json' else json.dumps({'observations': [smoke.EXPECTED]})
            return completion(content=content)
        response = completion(tool='record_inventory', finish='tool_calls')
        response['choices'][0]['message']['tool_calls'][0]['function']['arguments'] = 'PRIVATE_MALFORMED_ARGS'
        return response
    path = tmp_path / 'malformed.json'
    report = asyncio.run(smoke.run(path, execute=True, request=request))
    assert report['status'] == 'failed' and report['live_path_verified'] is False
    assert report['error_kind'] == 'validation_failed'
    assert len(attempts) == (1 if malformed == 'extraction_json' else 2)
    assert report['stages'][-1]['telemetry']['calls'][-1]['status'] == 'completed'
    assert report['stages'][-1]['status'] == 'failed'
    assert 'PRIVATE_MALFORMED' not in path.read_text()


def test_request_budget_cannot_expand_or_change_model():
    async def forbidden(_payload):
        pytest.fail('Invalid budget or model must be blocked before transport')
    with pytest.raises(ValueError):
        smoke.BoundedRequest(forbidden, max_requests=smoke.MAX_REQUESTS + 1)
    with pytest.raises(ValueError):
        smoke.BoundedRequest(forbidden, max_output_tokens=smoke.MAX_OUTPUT_TOKENS + 1)
    bounded = smoke.BoundedRequest(forbidden)
    with pytest.raises(provider.MetaRequestError) as failed:
        asyncio.run(bounded({'model': 'different-model', 'max_completion_tokens': 1}))
    assert failed.value.error_kind == 'model_mismatch' and bounded.calls == 0


def test_successful_http_metadata_and_usage_are_bounded(monkeypatch):
    seen = install_http(monkeypatch, response=httpx.Response(200, json=completion(content='{}'), headers={'request-id': 'req-fallback'}))
    telemetry = {}
    result = asyncio.run(provider.measured_request({'model': smoke.MODEL}, telemetry))
    assert isinstance(result, dict) and len(seen) == 1
    logged = telemetry['calls'][0]
    assert logged['response_id'] == 'response-artificial' and logged['request_id'] == 'req-fallback'
    assert logged['http_status'] == 200 and logged['finish_reason'] == 'stop'
    assert logged['error_kind'] is None and logged['status'] == 'completed'


def test_failure_history_projection_preserves_allowlisted_diagnostics_only(tmp_path, monkeypatch):
    import dotenv
    monkeypatch.setattr(dotenv, 'load_dotenv', lambda *_a, **_k: False)
    monkeypatch.setenv('MODUS_ENTRY_DB_PATH', str(tmp_path / 'module-only.db'))
    module = importlib.import_module('modus_entry.app')
    app = module.create_entry_app(tmp_path / 'history.db')
    fields = {'response_id': 'resp-safe', 'request_id': 'req-safe', 'http_status': 200,
              'finish_reason': 'content_filter', 'error_kind': 'incomplete'}
    app.state.store.save_run({'schema': 'modus-entry-change-v1', 'kind': 'question', 'status': 'failed',
        'mode': 'meta', 'telemetry': {'calls': [{**fields, 'status': 'failed', 'duration_ms': 2,
            'usage': {'total_tokens': 17, 'private': 'DROP_ME'},
            'raw_headers': {'secret': 'DROP_ME'}, 'unknown': 'DROP_ME'}]}})
    from fastapi.testclient import TestClient
    response = TestClient(app).get('/api/changes')
    assert response.status_code == 200 and 'DROP_ME' not in response.text
    retained = response.json()['changes'][0]['telemetry']['calls'][0]
    assert all(retained[key] == value for key, value in fields.items())
    assert retained['usage'] == {'total_tokens': 17}

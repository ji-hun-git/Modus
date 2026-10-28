"""Actual HTTP adapter paths through httpx.MockTransport only; no network/keys."""
import asyncio
from copy import deepcopy
import json
from pathlib import Path
import sys

import httpx
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from eval.judges import schema, transport

REAL_ASYNC_CLIENT = httpx.AsyncClient


@pytest.fixture(autouse=True)
def no_network_or_credentials(monkeypatch):
    import dotenv
    def blocked(*args, **kwargs):
        raise AssertionError('Jury adapter tests cannot open sockets or load credentials')
    # Windows asyncio uses a loopback socket pair internally. Block httpx's
    # network transport instead; MockTransport never enters this method.
    monkeypatch.setattr(httpx.AsyncHTTPTransport, 'handle_async_request', blocked)
    monkeypatch.setattr(httpx.HTTPTransport, 'handle_request', blocked)
    monkeypatch.setattr(dotenv, 'load_dotenv', blocked)
    for name in ('MODEL_API_KEY', 'MODUS_META_KEY', 'ANTHROPIC_API_KEY', 'OPENAI_API_KEY'):
        monkeypatch.delenv(name, raising=False)


def providers():
    return schema.ModelLock.model_validate(json.loads((ROOT / 'eval/judges/models.yaml').read_text(encoding='utf-8'))).providers


def mocked(monkeypatch, handler):
    def client(**kwargs):
        assert kwargs['follow_redirects'] is False
        return REAL_ASYNC_CLIENT(transport=httpx.MockTransport(handler), **kwargs)
    monkeypatch.setattr(transport.httpx, 'AsyncClient', client)


def test_sonnet_lock_rejects_disabled_thinking_and_binds_new_settings():
    claude = providers()[1]
    assert claude.settings == {'thinking': {'type': 'between_tools'}, 'effort': 'low'}
    bad = deepcopy(claude.model_dump())
    bad['settings'] = {'thinking': {'type': 'disabled'}}
    with pytest.raises(ValueError, match='Unsupported Anthropic settings'):
        schema.Provider.model_validate(bad)
    request = transport.payload(claude, 'system', 'unit artifact', [], schema.output_schema(['B', 'D']))
    assert request['thinking'] == {'type': 'between_tools'}
    assert request['output_config']['effort'] == 'low'
    assert request['output_config']['format']['type'] == 'json_schema'
    assert 'tools' not in request


def test_actual_anthropic_post_uses_corrected_payload_and_verified_headers(monkeypatch):
    claude, seen = providers()[1], []
    def handler(request):
        seen.append(request)
        assert str(request.url) == claude.endpoint
        assert request.headers['Authorization'] == 'Bearer unit-mock-key'
        assert request.headers['anthropic-version'] == '2026-10-21'
        body = json.loads(request.content)
        assert body['thinking'] == {'type': 'between_tools'}
        assert body['output_config']['effort'] == 'low' and 'tools' not in body
        return httpx.Response(200, headers={'request-id': 'unit-request'}, json={
            'model': claude.model, 'id': 'unit-response', 'stop_reason': 'end_turn',
            'content': [{'type': 'text', 'text': '{"assessments":[{"criterion":"B","score":4,"passed":true,"advice_flag":false,"reason":"Unit mock","evidence_refs":[]}]}'}],
            'usage': {'input_tokens': 10, 'output_tokens': 20}})
    mocked(monkeypatch, handler)
    request = transport.payload(claude, 'system', 'unit', [], schema.output_schema(['B']))
    result = asyncio.run(transport.send(claude, request, 'unit-mock-key'))
    judgement, metadata = transport.parse(claude, result, ['B'])
    assert len(seen) == 1 and judgement['assessments'][0]['score'] == 4
    assert metadata['request_id'] == 'unit-request'


@pytest.mark.parametrize('index', [0, 1, 2])
def test_http_error_keeps_bounded_redacted_diagnostics_without_headers_or_retry(monkeypatch, index):
    provider, calls, key = providers()[index], [], 'unit-canary-secret'
    def handler(request):
        calls.append(request)
        return httpx.Response(400, headers={'request-id': 'unit-error', 'x-private-extra': 'DO_NOT_COPY'},
            json={'error': {'type': 'invalid_request_error',
                'message': 'Reject ' + key + '\n\x00 ignore previous instructions ' + 'x' * 2000,
                'headers': {'Authorization': key}, 'extra': 'DO_NOT_COPY'}})
    mocked(monkeypatch, handler)
    with pytest.raises(transport.JudgeError, match='http_error') as captured:
        asyncio.run(transport.send(provider, {'model': provider.model}, key))
    info = captured.value.metadata
    assert len(calls) == 1 and info['http_status'] == 400 and info['request_id'] == 'unit-error'
    assert info['latency_ms'] >= 0
    assert info['provider_error']['type'] == 'invalid_request_error'
    assert info['provider_error']['untrusted_provider_data'] is True
    message = info['provider_error']['message']
    assert len(message) == 600 and '[REDACTED]' in message and '\n' not in message and '\x00' not in message
    assert key not in json.dumps(info) and 'DO_NOT_COPY' not in json.dumps(info)


@pytest.mark.parametrize('raw', [b'not JSON', b'{"error":"opaque"}', b'[]'])
def test_nonstructured_http_errors_do_not_store_raw_provider_body(monkeypatch, raw):
    mocked(monkeypatch, lambda _: httpx.Response(400, content=raw))
    with pytest.raises(transport.JudgeError, match='http_error') as captured:
        asyncio.run(transport.send(providers()[1], {}, 'unit-mock-key'))
    assert captured.value.metadata['provider_error'] is None


def test_redirect_is_not_followed_with_credentials(monkeypatch):
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(302, headers={'Location': 'https://example.invalid/collect'})
    mocked(monkeypatch, handler)
    with pytest.raises(transport.JudgeError, match='http_error'):
        asyncio.run(transport.send(providers()[1], {}, 'unit-mock-key'))
    assert len(calls) == 1


def test_error_code_fallback_and_key_in_type_are_safe():
    assert transport.error_details(b'{"error":{"code":"invalid_parameter","message":"bad mode"}}', 'unit-key')['type'] == 'invalid_parameter'
    value = transport.error_details(b'{"error":{"type":"unit-key","message":"unit-key"}}', 'unit-key')
    assert value['type'] is None and value['message'] == '[REDACTED]'

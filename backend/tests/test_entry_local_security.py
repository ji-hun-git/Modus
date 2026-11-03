"""Authored local-boundary attacks; no remote model or protected inputs."""
import asyncio
import logging

from fastapi.testclient import TestClient
import pytest

from modus_entry.app import create_entry_app
from modus_entry import local_security as security


def scope(method='POST', path='/api/imports/preview', headers=(), client=('127.0.0.1', 50000)):
    return {'type': 'http', 'http_version': '1.1', 'scheme': 'http', 'method': method,
            'path': path, 'raw_path': path.encode(), 'query_string': b'', 'client': client,
            'server': ('127.0.0.1', 8034), 'headers': [(b'host', b'127.0.0.1:8034'),
            (b'x-modus-request', b'1'), *headers]}


def exercise(request_scope, chunks=None, app=None, slow=False):
    sent, reached = [], []
    async def endpoint(s, receive, send):
        reached.append(await receive())
        await send({'type': 'http.response.start', 'status': 200, 'headers': []})
        await send({'type': 'http.response.body', 'body': b'ok'})
    messages = iter(chunks or [{'type': 'http.request', 'body': b'{}'}])
    async def receive():
        if slow: await asyncio.sleep(0.05)
        return next(messages, {'type': 'http.disconnect'})
    async def send(message): sent.append(message)
    asyncio.run(security.LocalSecurityMiddleware(app or endpoint)(request_scope, receive, send))
    return sent, reached


@pytest.mark.parametrize('headers', [
    [(b'origin', b'https://untrusted.invalid')],
    [(b'origin', b'null')],
    [(b'origin', b'http://127.0.0.1:8035')],
    [(b'origin', b'https://127.0.0.1:8034')],
    [(b'origin', b'http://localhost:8034')],
    [(b'origin', b'http://127.0.0.1:8034'), (b'origin', b'http://127.0.0.1:8034')],
    [(b'referer', b'http://127.0.0.1:8035/page')],
    [(b'sec-fetch-site', b'cross-site')],
    [(b'sec-fetch-site', b'same-site')],
    [(b'sec-fetch-site', b'unknown')],
    [(b'host', b'localhost:8034')],
    [(b'x-modus-request', b'1')],
])
def test_untrusted_requests_never_reach_parser_or_model(headers):
    sent, reached = exercise(scope(headers=headers))
    assert sent[0]['status'] == 403 and reached == []


@pytest.mark.parametrize('host', [b'testserver', b'attacker.invalid', b'127.0.0.1.attacker.invalid',
                                 b'127.0.0.1:0', b'127.0.0.1:99999', b'user@127.0.0.1:8034'])
def test_host_check_has_no_development_bypass(host):
    request = scope()
    request['headers'][0] = (b'host', host)
    assert exercise(request)[0][0]['status'] == 403


@pytest.mark.parametrize('client', [None, ('192.168.1.2', 8000), ('203.0.113.9', 8000)])
def test_remote_peer_cannot_spoof_loopback_host_or_forwarded_headers(client):
    request = scope(client=client, headers=[(b'x-forwarded-for', b'127.0.0.1')])
    assert exercise(request)[0][0]['status'] == 403


@pytest.mark.parametrize('method', ['POST', 'PUT', 'PATCH', 'DELETE'])
def test_writes_require_explicit_header_even_without_browser_metadata(method):
    request = scope(method=method)
    request['headers'] = request['headers'][:1]
    assert exercise(request)[0][0]['status'] == 403


def test_same_origin_and_direct_downloads_remain_usable():
    for request in [scope(headers=[(b'origin', b'http://127.0.0.1:8034'), (b'sec-fetch-site', b'same-origin')]),
                    scope(method='GET', path='/api/history/view', headers=[(b'sec-fetch-site', b'none')])]:
        sent, reached = exercise(request)
        assert sent[0]['status'] == 200 and len(reached) == 1
    request = scope(method='GET', path='/', headers=[(b'referer', b'https://untrusted.invalid/'),
        (b'sec-fetch-site', b'cross-site'), (b'sec-fetch-mode', b'navigate'),
        (b'sec-fetch-dest', b'document'), (b'sec-fetch-user', b'?1')])
    assert exercise(request)[0][0]['status'] == 200
    request['path'] = '/api/history/view'
    assert exercise(request)[0][0]['status'] == 403


@pytest.mark.parametrize('length', [b'999999999', b'9'*5000, b'-1', b'no'])
def test_oversized_or_invalid_declared_bodies_are_rejected_before_reading(length):
    sent, reached = exercise(scope(headers=[(b'content-length', length)]))
    assert sent[0]['status'] == 413 and not reached


def test_streamed_body_limit_cannot_be_bypassed_by_chunking_or_false_length(monkeypatch):
    monkeypatch.setattr(security, 'MAX_REQUEST_BYTES', 12)
    chunks = [{'type': 'http.request', 'body': b'12345678', 'more_body': True},
              {'type': 'http.request', 'body': b'12345678', 'more_body': False}]
    for headers in ([], [(b'content-length', b'8')]):
        sent, reached = exercise(scope(headers=headers), chunks)
        assert sent[0]['status'] == 413 and not reached
    sent, reached = exercise(scope(), [{'type': 'http.request', 'body': b'123456789012'}])
    assert sent[0]['status'] == 200 and reached[0]['body'] == b'123456789012'


def test_upload_timeout_and_disconnect_never_reach_parser(monkeypatch):
    monkeypatch.setattr(security, 'BODY_TIMEOUT_SECONDS', 0.001)
    sent, reached = exercise(scope(), slow=True)
    assert sent[0]['status'] == 408 and not reached
    sent, reached = exercise(scope(), [{'type': 'http.disconnect'}])
    assert sent == reached == []


def test_unexpected_failures_never_echo_private_exception_or_query(caplog):
    async def broken(s, receive, send):
        raise ValueError('PRIVATE_ERROR_CANARY')
    request = scope()
    request['query_string'] = b'label=PRIVATE_QUERY_CANARY'
    with caplog.at_level(logging.ERROR):
        sent, _ = exercise(request, app=broken)
    assert sent[0]['status'] == 500
    assert 'CANARY' not in str(sent) + caplog.text
    assert dict(sent[0]['headers'])[b'cache-control'] == b'no-store'


def test_browser_attacks_cannot_create_drafts_and_validation_does_not_reflect_input(tmp_path):
    app = create_entry_app(tmp_path/'security.db')
    raw = b'kind,label,value,unit,date\nmeasurement,Glucose,91,mg/dL,2024-01-12\n'
    with TestClient(app, headers={}) as client:
        with app.state.store.connect() as db:
            before = db.execute('SELECT COUNT(*) FROM drafts').fetchone()[0]
        for headers in ({'Origin': 'https://untrusted.invalid'}, {'Sec-Fetch-Site': 'same-site'}, {}):
            response = client.post('/api/imports/preview', headers=headers, data={'synthetic_confirmed': 'true'},
                files={'file': ('private.csv', raw, 'text/csv')})
            assert response.status_code == 403
        with app.state.store.connect() as db:
            assert db.execute('SELECT COUNT(*) FROM drafts').fetchone()[0] == before
        client.headers['X-Modus-Request'] = '1'
        invalid = client.put('/api/profile', json={'date_of_birth': 'PRIVATE_INPUT_CANARY', 'PRIVATE_FIELD_CANARY': 'x'})
        assert invalid.status_code == 422 and 'CANARY' not in invalid.text
        draft = client.post('/api/imports/preview', data={'synthetic_confirmed': 'true'},
            files={'file': ('private.csv', raw, 'text/csv')})
        assert draft.status_code == 200, draft.text
        original = client.get('/api/drafts/' + draft.json()['id'] + '/original')
        assert original.content == raw
        assert original.headers['content-security-policy'] == "sandbox; default-src 'none'"
        for response in (draft, original, invalid, client.get('/api/missing')):
            assert response.headers['cache-control'] == 'no-store'
            assert response.headers['referrer-policy'] == 'no-referrer'
            assert response.headers['x-frame-options'] == 'DENY'
            assert response.headers['x-content-type-options'] == 'nosniff'
            assert 'access-control-allow-origin' not in response.headers
        assert client.get('/openapi.json').status_code == 404


def test_cross_origin_preflight_cannot_authorize_a_write(tmp_path):
    with TestClient(create_entry_app(tmp_path/'preflight.db')) as client:
        response = client.options('/api/imports/preview', headers={'Origin': 'http://127.0.0.1:9999',
            'Access-Control-Request-Method': 'POST', 'Access-Control-Request-Headers': 'x-modus-request'})
        assert response.status_code == 403 and 'access-control-allow-origin' not in response.headers

"""Fresh offline authentication cases. All credentials are isolated test material."""
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import json
from pathlib import Path
import sys

from fastapi.testclient import TestClient
import pytest

from modus_entry.app import create_entry_app
from modus_entry.local_access import LocalAccess, ABSOLUTE_SECONDS, IDLE_SECONDS
from modus_entry.local_security import _origin

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'scripts'))
from local_access_file import publish_access_file
from public_repository import content_findings, path_problem

RAW = b'kind,label,value,unit,date\nmeasurement,Ferritin,30,ng/mL,2024-01-12\n'


@pytest.fixture
def secured(tmp_path):
    app = create_entry_app(tmp_path/'records.db')
    clock = [0.0]
    app.state.local_access.clock = lambda: clock[0]
    material = app.state.local_access.configure('http://127.0.0.1')
    with TestClient(app, headers={'X-Modus-Request': '1'}) as client:
        yield app, client, material, clock


def login(client, material):
    response = client.post('/api/access/unlock', json={'token': material['token']})
    assert response.status_code == 200
    token = response.json()['access_token']
    client.headers['Authorization'] = 'Bearer ' + token
    return token


@pytest.mark.parametrize('method,path', [('GET','/api/health'), ('GET','/api/history/view'),
    ('GET','/api/profile'), ('GET','/api/changes'), ('GET','/api/history/sources/guess/original'),
    ('GET','/api/drafts/guess/original'), ('POST','/api/imports/preview'), ('POST','/api/history/commit'),
    ('POST','/api/history/amendments/commit'), ('POST','/api/history/chat'), ('POST','/api/briefs/export'),
    ('GET','/_session/status'), ('GET','/api/not-a-route')])
def test_anonymous_and_forged_clients_cannot_read_or_write(secured, method, path):
    app, client, _, _ = secured
    before = app.state.store.history()
    response = client.request(method, path, headers={'Authorization': 'Bearer forged'})
    assert response.status_code == 401
    assert response.headers['cache-control'] == 'no-store'
    assert app.state.store.history() == before


def test_unconfigured_service_fails_closed_without_a_test_flag(tmp_path):
    app = create_entry_app(tmp_path/'unconfigured.db')
    with TestClient(app, headers={'X-Modus-Request':'1'}) as client:
        assert client.get('/api/access/status').json() == {'configured':False,'authenticated':False}
        assert client.get('/api/history/view').status_code == 401
        assert client.post('/api/access/unlock',json={'token':'not-configured'}).status_code == 401


def test_unlock_returns_only_a_new_session_and_no_cookie(secured):
    app, client, material, _ = secured
    token = login(client, material)
    assert token != material['token']
    assert material['token'] not in repr(app.state.local_access.__dict__)
    assert token not in repr(app.state.local_access.__dict__)
    assert not client.cookies
    assert client.get('/api/access/status').json()['authenticated']
    assert client.get('/api/history/view').status_code == 200
    # The owner access file is not itself a record-API credential.
    client.headers['Authorization'] = 'Bearer ' + material['token']
    assert client.get('/api/history/view').status_code == 401


def test_copied_urls_cookies_and_other_origins_do_not_authenticate(secured):
    _, client, material, _ = secured
    token = login(client, material)
    client.headers.pop('Authorization')
    assert client.get('/api/history/view',params={'access_token':token}).status_code == 401
    assert client.get('/api/history/view',headers={'Cookie':'session='+token}).status_code == 401
    client.headers['Authorization'] = 'Bearer ' + token
    assert client.get('/api/history/view',headers={'Host':'127.0.0.1:9999'}).status_code == 401
    assert client.get('/api/history/view',headers={'Origin':'http://127.0.0.1:9999'}).status_code == 403
    assert client.get('/api/history/view',headers=[('Authorization','Bearer '+token),('Authorization','Bearer '+token)]).status_code == 403


def test_status_polling_does_not_keep_an_idle_session_alive(secured):
    _, client, material, clock = secured
    login(client, material)
    clock[0] = IDLE_SECONDS-1
    assert client.get('/api/access/status').json()['authenticated']
    clock[0] = IDLE_SECONDS
    assert client.get('/api/history/view').status_code == 401
    assert not client.get('/api/access/status').json()['authenticated']


def test_real_activity_extends_idle_but_not_absolute_lifetime(secured):
    _, client, material, clock = secured
    login(client, material)
    for instant in range(900,ABSOLUTE_SECONDS,900):
        clock[0] = instant
        assert client.post('/api/access/touch',json={}).status_code == 200
    clock[0] = ABSOLUTE_SECONDS
    assert client.post('/api/access/touch',json={}).status_code == 401


def test_lock_revokes_all_sessions_and_keeps_records_and_originals(secured):
    app, client, material, _ = secured
    first = login(client, material)
    draft = client.post('/api/imports/preview',data={'synthetic_confirmed':'true'},files={'file':('source.csv',RAW,'text/csv')}).json()
    assert client.get('/api/drafts/'+draft['id']+'/original').content == RAW
    before = app.state.store.history()
    second = login(client, material)
    assert client.post('/api/access/lock',json={}).json() == {'locked':True}
    for token in (first,second):
        client.headers['Authorization'] = 'Bearer '+token
        assert client.get('/api/drafts/'+draft['id']+'/original').status_code == 401
        assert client.post('/api/history/commit',json={}).status_code == 401
    login(client,material)
    assert client.get('/api/drafts/'+draft['id']+'/original').content == RAW
    assert app.state.store.history() == before


def test_restart_or_rotation_invalidates_file_and_sessions(secured):
    app, client, old, _ = secured
    login(client,old)
    new = app.state.local_access.configure('http://127.0.0.1')
    assert client.get('/api/history/view').status_code == 401
    assert client.post('/api/access/unlock',json={'token':old['token']}).status_code == 401
    login(client,new)
    assert client.get('/api/history/view').status_code == 200


def test_failed_unlocks_are_bounded_and_recover_without_changing_records(secured):
    app, client, material, clock = secured
    before = app.state.store.history()
    for _ in range(5):
        result = client.post('/api/access/unlock',json={'token':'invalid'})
        assert result.status_code == 401
    limited = client.post('/api/access/unlock',json={'token':material['token']})
    assert limited.status_code == 429 and limited.headers['retry-after'] == '60'
    clock[0] = 60
    login(client,material)
    assert app.state.store.history() == before


def test_large_unlock_body_and_validation_never_echo_secrets(secured):
    _, client, material, _ = secured
    response = client.post('/api/access/unlock',json={'token':material['token'],'unexpected':'PRIVATE_CANARY'})
    assert response.status_code == 422
    assert 'PRIVATE_CANARY' not in response.text and material['token'] not in response.text
    assert client.post('/api/access/unlock',content=b'x'*1025).status_code == 413


def test_session_capacity_is_bounded_and_concurrent_tokens_are_unique(secured):
    app, _, material, _ = secured
    access = app.state.local_access
    with ThreadPoolExecutor(max_workers=4) as pool:
        issued = list(pool.map(lambda _:access.unlock(material['token'],_origin(material['origin']))['access_token'],range(16)))
    assert len(set(issued)) == 16
    assert len(access._sessions) == 8


def test_launcher_publishes_private_file_without_rewriting_database(tmp_path):
    app = create_entry_app(tmp_path/'records.db')
    before = sha256((tmp_path/'records.db').read_bytes()).hexdigest()
    file = publish_access_file(app,tmp_path/'access',8034)
    material = json.loads(file.read_text())
    assert material['origin'] == 'http://127.0.0.1:8034'
    assert file.name == 'Modus-8034.modus-access'
    assert sha256((tmp_path/'records.db').read_bytes()).hexdigest() == before
    session = app.state.local_access.unlock(material['token'],_origin(material['origin']))
    assert session['access_token'] != material['token']
    assert path_problem(file.name) == 'credential_or_runtime_file'
    for token in (material['token'],session['access_token']):
        found = content_findings('accidental.json',json.dumps({'token':token}))
        assert found and token not in repr(found)


def test_explicit_vite_origin_replaces_backend_origin(tmp_path):
    app = create_entry_app(tmp_path/'records.db')
    file = publish_access_file(app,tmp_path/'access',8011,ui_port=5174)
    material = json.loads(file.read_text())
    assert file.name == 'Modus-5174.modus-access'
    with TestClient(app,base_url='http://127.0.0.1:5174',headers={'X-Modus-Request':'1'}) as client:
        assert client.post('/api/access/unlock',json={'token':material['token']}).status_code == 200
        assert client.post('/api/access/unlock',json={'token':material['token']},headers={'Host':'127.0.0.1:8011'}).status_code == 401

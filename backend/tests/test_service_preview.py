"""Offline preview cannot present a stale source or frontend as checked."""
import json
from pathlib import Path
import sys
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'scripts'))
from check_service import inputs, build_inputs
from serve_service import verify_service, configure_offline, runtime_directory, workspace_lease


@pytest.fixture
def checked_preview(tmp_path):
    (tmp_path/'entry/config').mkdir(parents=True)
    (tmp_path/'entry/frontend/dist').mkdir(parents=True)
    (tmp_path/'release/service-check').mkdir(parents=True)
    (tmp_path/'source.py').write_text('checked source')
    (tmp_path/'entry/frontend/dist/index.html').write_text('<main>checked build</main>')
    (tmp_path/'entry/config/source_manifest.json').write_text(json.dumps({'files':[
        {'source':'source.py','destination':'source.py','behavior':True}]}))
    report = {'status':'passed','checks':{'backend':0,'frontend-tests':0,'frontend-build':0},
              'source_sha256':inputs(tmp_path),'build_sha256':build_inputs(tmp_path)}
    (tmp_path/'release/service-check/report.json').write_text(json.dumps(report))
    return tmp_path


def test_checked_preview_without_release_or_evaluation_artifacts(checked_preview):
    verify_service(checked_preview)


def test_direct_child_mode_removes_inherited_credentials(monkeypatch):
    import os
    keys = ('MODUS_META_KEY','MODEL_API_KEY','ANTHROPIC_API_KEY','OPENAI_API_KEY')
    for key in keys:
        monkeypatch.setenv(key, 'synthetic-test-canary')
    configure_offline()
    assert all(key not in os.environ for key in keys)
    assert os.environ['MODUS_PROVIDER'] == os.environ['MODUS_ENTRY_PROVIDER'] == 'offline'


@pytest.mark.parametrize('path', ['source.py','entry/frontend/dist/index.html','entry/frontend/dist/new.js'])
def test_changed_source_or_build_is_rejected(checked_preview, path):
    (checked_preview/path).write_text('not checked')
    with pytest.raises(ValueError, match='changed'):
        verify_service(checked_preview)


def test_passing_label_cannot_hide_failed_tests(checked_preview):
    path=checked_preview/'release/service-check/report.json'
    report=json.loads(path.read_text())
    report['checks']['backend']=1
    path.write_text(json.dumps(report))
    with pytest.raises(ValueError, match='successfully'):
        verify_service(checked_preview)


@pytest.mark.parametrize('name', ['../main', 'take/one', 'take\\one', '', 'a'*49, '.hidden', 'TAKE', 'take 1', '-take'])
def test_rehearsal_names_cannot_choose_arbitrary_paths(tmp_path, name):
    with pytest.raises(ValueError, match='rehearsal name'):
        runtime_directory(tmp_path, name)
    assert not (tmp_path/'release').exists()


def test_named_rehearsals_preserve_main_and_resume_their_encrypted_history(tmp_path):
    from modus.record_store import RecordStore
    from modus.record_keys import key_metadata_path
    from modus.record_encryption_migration import logical_snapshot
    normal=runtime_directory(tmp_path)
    assert normal==tmp_path/'release/offline-service'
    normal.mkdir(parents=True)
    sentinel=normal/'records.db'
    sentinel.write_bytes(b'authored main-workspace sentinel')
    original=sentinel.read_bytes()
    with workspace_lease(tmp_path,'take-01') as take:
        store=RecordStore(take/'records.db',seed_provider=lambda:([],[]))
        with store.connect() as db:
            db.execute('INSERT INTO documents VALUES(?,?,?,?)',('authored','original.txt','text/plain',b'unchanged original evidence'))
        with store.connect() as db:
            before=logical_snapshot(db)
        metadata=key_metadata_path(take/'records.db').read_bytes()
        encrypted=(take/'records.db').read_bytes()
        assert b'unchanged original evidence' not in encrypted
    with workspace_lease(tmp_path,'take-01') as resumed:
        store=RecordStore(resumed/'records.db',seed_provider=lambda:([],[]))
        with store.connect() as db:
            assert logical_snapshot(db)==before
        assert key_metadata_path(resumed/'records.db').read_bytes()==metadata
    with workspace_lease(tmp_path,'take-02') as fresh:
        store=RecordStore(fresh/'records.db',seed_provider=lambda:([],[]))
        with store.connect() as db:
            assert db.execute('SELECT count(*) FROM documents').fetchone()[0]==0
        assert key_metadata_path(fresh/'records.db').read_bytes()!=metadata
    assert sentinel.read_bytes()==original


def test_second_launcher_cannot_replace_a_running_workspaces_access_file(tmp_path):
    from modus.record_crypto import StorageError
    with workspace_lease(tmp_path,'take-01') as directory:
        access=directory/'Modus-8035.modus-access'
        access.write_text('authored access-file sentinel')
        with pytest.raises(StorageError, match='in use'):
            with workspace_lease(tmp_path,'take-01'):
                access.write_text('must never happen')
        assert access.read_text()=='authored access-file sentinel'


def test_parent_launcher_forwards_workspace_without_forwarding_credentials(tmp_path, monkeypatch):
    import os
    import serve_service
    monkeypatch.setattr(serve_service,'ROOT',tmp_path)
    monkeypatch.setattr(serve_service,'verify_service',lambda:None)
    executable=tmp_path/'.venv'/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
    executable.parent.mkdir(parents=True); executable.write_bytes(b'authored placeholder')
    monkeypatch.setattr(sys,'argv',['serve_service.py','--port','8035','--rehearsal','take-01'])
    monkeypatch.setenv('MODUS_META_KEY','authored-unused-canary')
    calls=[]
    monkeypatch.setattr(serve_service.subprocess,'run',lambda command,**kwargs:calls.append((command,kwargs)))
    serve_service.main()
    command,options=calls[0]
    assert command[-2:]==['--rehearsal','take-01']
    assert options['env']['MODUS_PROVIDER']=='offline'
    assert 'MODUS_META_KEY' not in options['env']
    assert not runtime_directory(tmp_path,'take-01').exists()


@pytest.mark.parametrize('script',['serve_service.py','encrypt_records.py'])
def test_operator_commands_bootstrap_without_global_third_party_packages(script):
    import subprocess
    from offline_environment import offline_environment
    root=Path(__file__).resolve().parents[2]
    completed=subprocess.run([sys.executable,'-X','utf8','-S',str(root/'scripts'/script),'--help'],
                             capture_output=True,text=True,env=offline_environment())
    assert completed.returncode==0,completed.stderr
    assert 'usage:' in completed.stdout


def test_migration_cli_delegates_to_the_locked_environment_without_model_keys(tmp_path,monkeypatch):
    import os
    import encrypt_records
    from types import SimpleNamespace
    monkeypatch.setattr(encrypt_records,'ROOT',tmp_path)
    executable=tmp_path/'.venv'/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
    executable.parent.mkdir(parents=True);executable.write_bytes(b'authored placeholder')
    database=tmp_path/'records.db'
    monkeypatch.setattr(sys,'argv',['encrypt_records.py',str(database),'--execute'])
    monkeypatch.setenv('MODUS_META_KEY','authored-unused-migration-canary')
    calls=[]
    def child(command,**options):
        calls.append((command,options));return SimpleNamespace(returncode=0)
    monkeypatch.setattr(encrypt_records.subprocess,'run',child)
    assert encrypt_records.main()==0
    command,options=calls[0]
    assert command[0]==str(executable) and command[-3:]==[str(database),'--execute','--child']
    assert 'MODUS_META_KEY' not in options['env'] and options['env']['MODUS_PROVIDER']=='offline'
    assert not database.exists()

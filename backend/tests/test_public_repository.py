"""Publication boundary tests over temporary authored files, no private inputs."""
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
from public_repository import audit, content_findings, path_problem, require_public


@pytest.mark.parametrize('name',['notes/meeting.md','private/notes.json','GOALS_AND_PROMPTS.md',
    'docs/PRODUCT_DESIGN_V9.md','metaAPI.txt','openai-key.txt','.env.local','archive/private.key',
    '../README.md','C:/outside.txt'])
def test_private_paths_are_not_publishable(name):
    assert path_problem(name)


@pytest.mark.parametrize('name',['entry/prompts/history.md','prompts/extract.md','entry/docs/API_CONTRACT.md',
    'data/licenses/dependencies/python/any/LICENSE.md','.env.example','README.md'])
def test_runtime_prompts_product_contracts_and_licenses_remain_publishable(name):
    assert path_problem(name) is None


def test_findings_never_echo_matched_secret_or_personal_content():
    token='sk-'+('x'*40)
    findings=content_findings('README.md','secret='+token+'\n'+'C:'+chr(92)+'Users'+chr(92)+'Example'+chr(92)+'notes')
    assert {item.code for item in findings}=={'credential_pattern','personal_working_context'}
    assert token not in repr(findings) and 'Example' not in repr(findings)
    assert content_findings('README.md','[Ask](api.md#typed-ask-queries--example-version)')==[]


def test_manifest_private_destination_is_rejected_without_opening_protected_inputs(tmp_path,monkeypatch):
    folder=tmp_path/'entry/config'; folder.mkdir(parents=True)
    (folder/'source_manifest.json').write_text(json.dumps({'files':[
        {'source':'README.md','destination':'README.md'},
        {'source':'notes/private.md','destination':'entry/docs/API_CONTRACT.md'},
        {'source':'evaluation/secret.json','destination':'evaluation/secret.json'}]}))
    (tmp_path/'README.md').write_text('# Product\n')
    original=Path.exists
    def guarded(path):
        if 'evaluation' in path.parts: pytest.fail('Protected path was inspected')
        return original(path)
    monkeypatch.setattr(Path,'exists',guarded)
    report=audit(tmp_path,selection_only=True)
    assert report['status']=='failed' and report['protected_paths_skipped']==1
    assert report['findings']==[{'path':'notes/private.md','code':'private_working_material','line':None}]
    with pytest.raises(ValueError,match='Public source check failed'):
        require_public(tmp_path,selection_only=True)

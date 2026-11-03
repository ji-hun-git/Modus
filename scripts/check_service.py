"""Offline service regression only. Never opens frozen evaluation artifacts.

This does not replace or mint the full release gate. Outputs stay in release/.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from offline_environment import offline_environment
from public_repository import require_public

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'release/service-check'
TESTS = ['test_entry_archive_seed.py', 'test_entry_narrative_comparison.py', 'test_public_repository.py', 'test_history_query_followups.py', 'test_history_query_plan.py', 'test_history_query_executor.py', 'test_history_query_integration.py', 'test_entry_longitudinal_series.py', 'test_service_preview.py', 'test_entry_report_briefs.py', 'test_entry_report_summary.py', 'test_entry_lab_context.py', 'test_entry_history_conversation.py', 'test_entry_natural_history.py', 'test_entry_medical_retrieval.py', 'test_entry_concurrency.py', 'test_entry_history_pages.py', 'test_entry.py', 'test_entry_adversarial.py', 'test_entry_amendments.py', 'test_entry_blood_pressure.py', 'test_entry_brief_api.py', 'test_entry_briefs.py', 'test_entry_document_guard.py', 'test_entry_document_guard_import.py', 'test_entry_environment_isolation.py', 'test_entry_history_agent_adversarial.py', 'test_entry_history_api.py', 'test_entry_history_compare_api.py', 'test_entry_history_expansion.py', 'test_entry_history_selection_limits.py', 'test_entry_history_tools.py', 'test_entry_investigation_flow.py', 'test_entry_ocr_api.py', 'test_entry_record_answers.py', 'test_entry_record_extraction_api.py', 'test_entry_retrieval.py', 'test_entry_routing.py', 'test_entry_runtime_identity.py', 'test_entry_whole_report_flow.py', 'test_whole_report_reader.py', 'test_record_units.py', 'test_record_store.py', 'test_record_history.py', 'test_record_extraction.py', 'test_record_retrieval.py', 'test_history_ingest.py', 'test_history_audit.py', 'test_extraction_layouts.py', 'test_ontology.py']


TESTS.extend(['test_record_row_inventory.py', 'test_entry_row_inventory.py', 'test_entry_omission_review.py', 'test_garak_record_boundaries.py'])
TESTS.extend(['test_entry_local_security.py', 'test_private_storage.py'])


def protected(name):
    name = name.replace('\\','/').lower()
    return name.startswith(('eval/','evaluation/','entry/eval/')) or 'heldout' in name or 'holdout' in name or Path(name).name == '.env'


def inputs(root=ROOT):
    manifest=json.loads((root/'entry/config/source_manifest.json').read_text(encoding='utf-8'))
    result={}
    for item in manifest['files']:
        if not item.get('behavior') or protected(item['source']) or protected(item['destination']): continue
        path=root/item['source']
        if not path.exists(): path=root/item['destination']
        if path.is_symlink() or not path.resolve().is_relative_to(root): raise ValueError('Unsafe manifest path')
        result[item['destination']]=hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def build_inputs(root=ROOT):
    dist=root/'entry/frontend/dist'
    if not (dist/'index.html').is_file():
        raise ValueError('Build the frontend before opening the service preview')
    result={}
    for path in sorted(dist.rglob('*')):
        if path.is_symlink() or not path.resolve().is_relative_to(dist.resolve()):
            raise ValueError('Unexpected link in frontend build')
        if path.is_file(): result[path.relative_to(root).as_posix()]=hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def child():
    blocked=[]
    def guard(event,args):
        if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)):
            path=Path(os.fsdecode(args[0])).absolute()
            try: name=path.relative_to(ROOT).as_posix()
            except ValueError: return
            if protected(name):
                blocked.append(name)
                raise PermissionError('Offline service checks exclude evaluation and secret files')
        if event=='socket.connect' and (not isinstance(args[1],tuple) or args[1][0] not in ('127.0.0.1','::1','localhost')):
            raise PermissionError('Offline service checks forbid external network')
    sys.addaudithook(guard)
    os.environ['MODUS_ENTRY_DB_PATH']=str(OUT/'entry-module.db')
    os.environ['MODUS_DB_PATH']=str(OUT/'research-module.db')
    os.chdir(ROOT/'backend')
    sys.path.insert(0,str(ROOT/'backend'))
    import pytest
    code=pytest.main(['-q']+['tests/'+name for name in TESTS])
    (OUT/'guard.json').write_text(json.dumps({'blocked_accesses':blocked,'exit_code':int(code)},indent=2))
    return int(code)


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    if '--child' in sys.argv: return child()
    try:
        public_report=require_public(ROOT)
    except ValueError as error:
        print(str(error),flush=True)
        return 1
    (OUT/'public-source.json').write_text(json.dumps(public_report,indent=2)+'\n',encoding='utf-8')
    before=inputs()
    python=ROOT/'.venv'/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
    if not python.exists(): python=Path(sys.executable)
    npm=shutil.which('npm.cmd' if os.name=='nt' else 'npm')
    if not npm: raise RuntimeError('Install Node.js/npm first')
    jobs=[('backend',[str(python),str(Path(__file__).resolve()),'--child'],ROOT),
        ('frontend-tests',[npm,'test'],ROOT/'entry/frontend'),
        ('frontend-build',[npm,'run','build'],ROOT/'entry/frontend')]
    checks={}
    for name,command,cwd in jobs:
        with (OUT/(name+'.log')).open('w',encoding='utf-8') as log:
            run=subprocess.run(command,cwd=cwd,env=offline_environment(),stdout=log,stderr=subprocess.STDOUT)
        checks[name]=run.returncode
        print(name+': '+('passed' if run.returncode==0 else 'FAILED; see release/service-check/'+name+'.log'),flush=True)
        if run.returncode:
            print((OUT/(name+'.log')).read_text(encoding='utf-8'),flush=True)
    unchanged=before==inputs()
    passed=unchanged and all(code==0 for code in checks.values())
    report={'status':'passed' if passed else 'failed','checks':checks,'inputs_unchanged':unchanged,
        'source_sha256':before,'build_sha256':build_inputs() if checks.get('frontend-build')==0 else {},
        'scope':'Offline service regression and frontend build only; no evaluation, live-model quality or final release qualification.'}
    (OUT/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return 0 if passed else 1


if __name__=='__main__': raise SystemExit(main())

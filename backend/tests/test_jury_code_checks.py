"""No real artifacts, credentials, model calls or held-out labels."""
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location('jury_code_checks', Path(__file__).resolve().parents[2] / 'eval/judges/code_checks.py')
checks = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checks)


def test_claim_membership_and_composition_are_distinct():
    claim = {'id':'c1','text':'Recorded pulse:72bpm.', 'evidence_ids':['s1'], 'tool_name':'inventory'}
    artifact = {'final_answer':claim['text'], 'evidence':{'answer_claims':[claim], 'tool_claims':[claim]}}
    assert checks.faithfulness(artifact)['status'] == 'pass'
    artifact['final_answer'] += ' Extra unsupported sentence.'
    assert checks.faithfulness(artifact)['status'] == 'ambiguous'
    artifact['evidence']['answer_claims'] = [{**claim, 'text':'Different value.'}]
    assert checks.faithfulness(artifact)['status'] == 'fail'


def test_not_applicable_and_artifact_binding():
    artifact = {'task':'Inspect Home.'}
    result = checks.faithfulness(artifact)
    assert result['status'] == 'not_applicable'
    assert result['artifact_sha256'] == checks.fingerprint(artifact)
    assert len(result['checker_sha256']) == 64
    assert checks.extraction(artifact)['status'] == 'not_applicable'


def test_exact_extraction_keeps_linkage_and_extra_rows():
    row = {'label':'Pulse','value':'72','unit':'bpm','occurred_on':'2026-10-28'}
    artifact = {'evidence':{'extracted_rows':[row], 'authored_expected_rows':[row]}}
    assert checks.extraction(artifact)['status'] == 'pass'
    artifact['evidence']['extracted_rows'] = [row, row]
    assert checks.extraction(artifact)['status'] == 'fail'


def test_label_only_alignment_is_fuzzy_but_numeric_mismatch_fails():
    row = {'label':'Pulse','value':'72','unit':'bpm','occurred_on':None}
    artifact = {'evidence':{'extracted_rows':[{**row, 'label':'Heart rate'}], 'authored_expected_rows':[row]}}
    assert checks.extraction(artifact)['status'] == 'fuzzy'
    artifact['evidence']['extracted_rows'][0]['value'] = '73'
    assert checks.extraction(artifact)['status'] == 'fail'

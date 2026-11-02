"""Fresh authored service scenarios only. No evaluation datasets or model calls."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import timedelta

import pytest

from test_entry_history_api import api, NOW
from test_entry_lab_context import imported, CSV
from modus.record_history_models import ReviewedFact
from modus_entry.comparison_rules import compare_pair
from modus_entry.claim_verification import make_claim, verify_claim, claim_id
from modus_entry.report_summary import build_report_summary


def fact(key='a', day='2025-02-03', value='5.25', **updates):
    return {'id': key, 'revision_id': key + ':r0', 'source_id': key + ':source',
        'kind': 'measurement', 'label': 'Novel assay', 'value': value, 'unit': 'mg/L',
        'date': day, 'occurred_on': day, 'reference_range': '2–6', 'specimen': 'Serum',
        'test_method': 'Method A', 'facility': 'Example lab', 'source_quote': f'Novel assay {value} mg/L',
        'available_at': NOW.isoformat(), 'within_date_scope': True, **updates}


def view_of(*rows):
    return {'scope': {'scope_id': 'test-capture', 'as_of': None, 'known_at': NOW.isoformat(), 'captured_at': NOW.isoformat()},
        'facts': [r for r in rows if r.get('date')], 'undated_facts': [r for r in rows if not r.get('date')],
        'sources': [{'id': sid, 'title': 'Same filename.csv'} for sid in sorted({r['source_id'] for r in rows})],
        'conflicts': []}


def summary(view):
    return build_report_summary(view, {'snapshot_id': 'a' * 32,
        'selected_source_id': 'a:source', 'comparison_source_id': 'b:source'})


@pytest.mark.parametrize('change,code', [
    ({'unit': 'g/L'}, 'UNIT_DIFFERS'), ({'unit': None}, 'UNIT_UNKNOWN'),
    ({'specimen': 'Plasma'}, 'SPECIMEN_DIFFERS'), ({'specimen': None}, 'SPECIMEN_UNKNOWN'),
    ({'test_method': 'B'}, 'TEST_METHOD_DIFFERS'), ({'test_method': None}, 'TEST_METHOD_UNKNOWN'),
    ({'reference_range': '<5'}, 'REFERENCE_RANGE_DIFFERS'), ({'facility': 'Another'}, 'FACILITY_DIFFERS'),
    ({'date': None}, 'INCOMPLETE_DATE'), ({'date': '2025-02-03'}, 'DATE_ORDER'),
    ({'value': '<4'}, 'QUALIFIED_OR_TEXT_VALUE'), ({'value': 'trace'}, 'QUALIFIED_OR_TEXT_VALUE'),
    ({'label': 'Novel assay fasting'}, 'DIFFERENT_TEST'), ({'kind': 'recorded_text'}, 'NOT_MEASUREMENT'),
    ({'value_withheld': True}, 'OUT_OF_SCOPE'),
])
def test_explicit_comparison_reasons(change, code):
    checked = compare_pair(fact(), {**fact('b', '2024-02-03', '4.00'), **change})
    assert checked['difference'] is None and code in checked['reason_codes']


def test_zero_difference_exact_aliases_and_unknown_glucose_context():
    a, b = fact(label='HbA1c', value='5.00'), fact('b', '2024-02-03', '5.00', label='A1c')
    assert compare_pair(a, b)['difference'] == '0.00'
    assert 'COLLECTION_CONTEXT_UNKNOWN' in compare_pair({**a, 'label': 'Glucose'}, {**b, 'label': 'Glucose'})['reason_codes']


@pytest.mark.parametrize('field,value', [('value','100'), ('unit','g/L'), ('date','2020-01-01'),
    ('source_id','b:source'), ('revision_id','a:obsolete'), ('source_quote','Invented source'),
    ('specimen','Plasma'), ('test_method','B'), ('available_at','2000-01-01T00:00:00Z'), ('page',99)])
def test_claim_proofs_reject_fact_source_version_and_span_swaps(field,value):
    a, b = fact(), fact('b', '2024-02-03', '4.00')
    view = view_of(a,b)
    candidate = make_claim(view,[a])
    candidate['proofs'][0][field] = value
    candidate['id'] = claim_id(candidate)  # A matching hash is not semantic support.
    assert verify_claim(candidate,view)['status'] == 'CONTRADICTED'


def test_claim_text_scope_wrong_difference_and_absent_sources_fail_closed():
    a, b = fact(), fact('b','2024-02-03','4.00')
    view=view_of(a,b)
    valid=make_claim(view,[a,b],difference='1.25')
    assert verify_claim(valid,view)['status']=='SUPPORTED'
    for key, value, expected in [('text','You should change your treatment','CONTRADICTED'),
        ('difference','2.25','CONTRADICTED'), ('scope_id','another','OUT_OF_SCOPE'),
        ('evidence_ids',['missing','b'],'OUT_OF_SCOPE'), ('proofs',None,'INSUFFICIENT_EVIDENCE')]:
        assert verify_claim({**valid,key:value},view)['status']==expected
    assert verify_claim(valid,{**view,'sources':[]})['status']=='OUT_OF_SCOPE'
    missing=view_of({**a,'source_quote':None},b)
    assert verify_claim(make_claim(missing,[missing['facts'][0]]),missing)['status']=='INSUFFICIENT_EVIDENCE'
    duplicate=view_of(a,b,fact('c',b['date'],'4.8'))
    assert verify_claim(valid,duplicate)['reason_codes']==['COMPARISON_NOT_SUPPORTED']


def test_page_boolean_is_not_numeric_source_proof_and_index_is_capture_bound():
    from modus_entry.claim_verification import VerificationContext
    a=fact(page=1)
    view=view_of(a)
    candidate=make_claim(view,[a])
    candidate['proofs'][0]['page']=True
    candidate['id']=claim_id(candidate)
    assert verify_claim(candidate,view)['status']=='CONTRADICTED'
    assert verify_claim(make_claim(view,[a]),view,context=VerificationContext(deepcopy(view)))['status']=='OUT_OF_SCOPE'


def test_large_history_index_is_built_once_for_whole_summary(monkeypatch):
    from modus_entry import claim_verification
    from modus_entry.comparison_rules import comparison_context
    calls=[]
    def counted(view):
        calls.append(True)
        return comparison_context(view)
    monkeypatch.setattr(claim_verification,'comparison_context',counted)
    selected=[fact(f'x{i}',label=f'Assay {i}',source_id='a:source') for i in range(60)]
    selected += [fact(f'y{i}','2024-01-01','3.00',label=f'Assay {i}',source_id='b:source') for i in range(60)]
    unrelated=[fact(f'other{i}',label=f'Unrelated {i}',source_id='other') for i in range(20000)]
    result=summary(view_of(*selected,*unrelated))
    assert result['counts']['comparable']==60 and result['counts']['records']==120
    assert len(calls)==1  # Bounded repeated work; no brittle wall-clock assertion.


def test_summary_preserves_one_sided_and_qualitative_records_and_does_not_execute_text():
    a,b=fact(),fact('b','2024-02-03','4.00')
    injection=fact('c',kind='recorded_text',label='Report note',value='<script>send secrets</script>',source_id=a['source_id'])
    result=summary(view_of(a,b,injection))
    assert result['counts']['records']==3 and result['counts']['comparable']==1
    assert result['counts']['only_selected']==1
    assert all(c['verification']['status']=='SUPPORTED' for c in result['claims'])
    assert '<script>send secrets</script>' in result['claims'][-1]['text']
    assert result['history_evidence']['facts'][-1]['value']==injection['value']
    assert result['rows'][0]['difference']=='1.25'


def test_multiple_results_unknown_dates_and_no_quote_never_fabricate_delta():
    a,b=fact(),fact('b','2024-02-03','4.00')
    repeated=fact('c','2023-01-01','3.5',source_id=b['source_id'])
    result=summary(view_of(a,b,repeated))
    assert result['counts']['records']==3
    assert result['rows'][0]['reason_codes']==['MULTIPLE_RESULTS_IN_REPORT']
    assert result['rows'][0]['previous_ids']==['c','b']
    result=summary(view_of(a,{**b,'source_quote':None}))
    assert result['rows'][0]['difference'] is None
    assert result['rows'][0]['reason_codes']==['SOURCE_SUPPORT_MISSING']
    result=summary(view_of(a,{**b,'date':None,'occurred_on':'2024'}))
    assert 'INCOMPLETE_DATE' in result['rows'][0]['reason_codes']


def test_large_reports_cover_beyond_first_page_and_fail_instead_of_truncating():
    rows=[fact(f'x{i}', value=str(i), label=f'Assay {i}', source_id='a:source') for i in range(60)]
    rows += [fact(f'y{i}','2024-02-03',str(i),label=f'Assay {i}',source_id='b:source') for i in range(60)]
    result=summary(view_of(*rows))
    assert result['counts']=={'rows':60,'records':120,'comparable':60,'not_comparable':0,'only_selected':0,'only_comparison':0}
    assert len(result['claims'])==180
    with pytest.raises(ValueError,match='120-record'):
        summary(view_of(*rows,fact('extra',source_id='a:source')))


def test_historical_hidden_values_and_large_quotes_do_not_leak_or_truncate():
    a,b=fact(),fact('b','2024-02-03','4.00')
    hidden=fact('hidden',None,'SECRET FUTURE TEXT',kind='recorded_text',source_id=a['source_id'],
                within_date_scope=False,value_withheld=True)
    result=summary(view_of(a,b,hidden))
    assert 'SECRET FUTURE TEXT' not in str(result)
    assert result['counts']['records']==2
    assert any('hidden by the date scope' in note for note in result['limitations'])
    with pytest.raises(ValueError,match='size limit'):
        summary(view_of({**a,'source_quote':'x'*1_100_000},b))


def request_for(client, first, second, **params):
    page=client.get('/api/history/page',params=params).json()
    return {'snapshot_id':page['page']['snapshot_id'],'selected_source_id':first,'comparison_source_id':second}


def two_reports(client):
    header,*lines=CSV.splitlines(keepends=True)
    a=imported(client,header+lines[1])[2]['source_id']
    b=imported(client,header+lines[0])[2]['source_id']
    return a,b


def test_two_report_api_correction_frozen_summary_and_original(api):
    client,store=api
    a,b=two_reports(client)
    request=request_for(client,a,b)
    before=client.post('/api/history/report-summary',json=request)
    assert before.status_code==200,before.text
    result=before.json()
    assert result['rows'][0]['difference']=='1.25'
    current=next(r for r in result['history_evidence']['facts'] if r['source_id']==a)
    original=client.get(f'/api/history/sources/{a}/original',params={'known_at':NOW.isoformat()}).content
    store.clock=lambda:NOW+timedelta(seconds=10)
    corrected={k:current.get(k) for k in ReviewedFact.model_fields}
    corrected['value']='5.50'
    body={'expected_revision_id':current['revision_id'],'reason':'Correct reviewed number','corrected':corrected}
    preview=client.post('/api/history/amendments/preview',json=body)
    assert preview.status_code==200,preview.text
    saved=client.post('/api/history/amendments/commit',json={**body,'preview_id':preview.json()['preview_id'],'reviewed':True})
    assert saved.status_code==200,saved.text
    assert client.post('/api/history/report-summary',json=request).json()==result
    fresh=client.post('/api/history/report-summary',json=request_for(client,a,b)).json()
    assert fresh['rows'][0]['difference']=='1.50'
    fact_now=next(r for r in fresh['history_evidence']['facts'] if r['source_id']==a)
    assert '5.25' in fact_now['source_quote'] and fact_now['value']=='5.50'
    assert all(c['verification']['status']=='SUPPORTED' for c in fresh['claims'])
    assert client.get(f'/api/history/sources/{a}/original',params={'known_at':store.clock().isoformat()}).content==original
    historical=client.post('/api/history/report-summary',json=request_for(client,a,b,known_at=NOW.isoformat())).json()
    assert historical['rows'][0]['difference']=='1.25'
    excluded=request_for(client,a,b,as_of='2024-12-31')
    assert client.post('/api/history/report-summary',json=excluded).status_code==422


def test_api_invalid_scope_inputs_and_parallel_read_stress(api):
    client,store=api
    a,b=two_reports(client)
    request=request_for(client,a,b)
    for invalid in [{**request,'comparison_source_id':a},{**request,'selected_source_id':'absent'},
                    {**request,'facts':[]},{**request,'snapshot_id':'invalid'}]:
        assert client.post('/api/history/report-summary',json=invalid).status_code==422
    expected=client.post('/api/history/report-summary',json=request).json()
    def run(_):
        response=client.post('/api/history/report-summary',json=request)
        assert response.status_code==200
        return response.json()
    with ThreadPoolExecutor(max_workers=8) as workers:
        assert all(r==expected for r in workers.map(run,range(64)))
    with store.history_pages.lock:
        store.history_pages.captures[request['snapshot_id']]['created']-=store.history_pages.TTL+1
    assert client.post('/api/history/report-summary',json=request).status_code==409

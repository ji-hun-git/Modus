"""Authored lab-context integration checks; no external providers or eval corpus."""
from datetime import timedelta
from copy import deepcopy
import pytest
from test_entry_history_api import api, NOW
from modus.record_history_models import ReviewedFact
from modus_entry.checkup_comparison import compare_checkups
from modus.record_extraction import _local_support
from modus.record_extraction_models import ProposedField, extraction_schema

CSV = ("kind,label,value,unit,date,facility,reference_range,specimen,test_method\n"
       "measurement,Novel assay,4.00,mg/L,2024-02-03,Example lab,2.0–6.0 mg/L,Serum,Method A\n"
       "measurement,Novel assay,5.25,mg/L,2025-02-03,Example lab,2.0–6.0 mg/L,Serum,Method A\n").encode()


def imported(client, raw=CSV):
    response=client.post('/api/imports/preview',data={'synthetic_confirmed':'true'},files={'file':('lab-context.csv',raw,'text/csv')})
    assert response.status_code==200,response.text
    draft=response.json()
    rows=[{k:r.get(k) for k in ReviewedFact.model_fields} for r in draft['facts']]
    body={'draft_id':draft['id'],'synthetic_confirmed':True,'reviewed_facts':rows}
    response=client.post('/api/history/commit',json=body)
    assert response.status_code==200,response.text
    return draft,body,response.json()


def test_lab_import_review_compare_correct_replay_and_original(api):
    client,store=api
    draft,body,receipt=imported(client)
    assert draft['facts'][0]['reference_range']=='2.0–6.0 mg/L'
    assert client.post('/api/history/commit',json=body).json()['duplicate']
    page=client.get('/api/history/page',params={'label':'Novel assay'}).json()
    fact=next(f for f in page['facts'] if f['date']=='2025-02-03')
    params={'snapshot_id':page['page']['snapshot_id'],'compare_fact_id':fact['id'],'limit':1}
    comparison=client.get('/api/history/page',params=params).json()['checkup_comparison']
    assert comparison['difference']=='1.25'
    assert comparison['previous'][0]['date']=='2024-02-03'
    assert comparison['current']['test_method']=='Method A'
    assert client.get('/api/history/page',params={**params,'offset':1}).json()['checkup_comparison']==comparison
    original=f"/api/history/sources/{receipt['source_id']}/original"
    assert client.get(original,params={"known_at":(NOW+timedelta(seconds=10)).isoformat()}).content==CSV
    store.clock=lambda:NOW+timedelta(seconds=10)
    corrected={k:fact.get(k) for k in ReviewedFact.model_fields}
    corrected['test_method']='Method B'
    request={'expected_revision_id':fact['revision_id'],'reason':'Correct the reviewed method','corrected':corrected}
    preview=client.post('/api/history/amendments/preview',json=request)
    assert preview.status_code==200,preview.text
    commit=client.post('/api/history/amendments/commit',json={**request,'preview_id':preview.json()['preview_id'],'reviewed':True})
    assert commit.status_code==200,commit.text
    current=client.get('/api/history/page',params={'compare_fact_id':fact['id']}).json()['checkup_comparison']
    assert current['difference'] is None
    assert any('Test method differs' in n for n in current['notes'])
    assert current['current']['source_proposal']['test_method']=='Method A'
    assert 'Method A' in current['current']['source_quote']
    assert client.get(original,params={"known_at":(NOW+timedelta(seconds=10)).isoformat()}).content==CSV
    assert client.get('/api/history/page',params=params).json()['checkup_comparison']==comparison
    historical=client.get('/api/history/page',params={'known_at':NOW.isoformat(),'compare_fact_id':fact['id']}).json()
    assert historical['checkup_comparison']['current']['test_method']=='Method A'
    assert client.get('/api/history/page',params={'known_at':'2020-01-01T00:00:00Z','compare_fact_id':fact['id']}).status_code==422


def test_lab_review_cannot_silently_drop_context(api):
    client,_=api
    draft=client.post('/api/imports/preview',data={'synthetic_confirmed':'true'},files={'file':('context.csv',CSV,'text/csv')}).json()
    row={k:draft['facts'][0].get(k) for k in ReviewedFact.model_fields if k!='specimen'}
    response=client.post('/api/history/commit',json={'draft_id':draft['id'],'synthetic_confirmed':True,'reviewed_facts':[row]})
    assert response.status_code==422


def test_unknown_date_lab_context_is_withheld(api):
    client,_=api
    draft,_,_=imported(client,CSV.replace(b'2024-02-03',b'2024'))
    view=client.get('/api/history/view',params={'as_of':'2024-12-31'}).json()
    fact=next(f for f in view['undated_facts'] if f['label']=='Novel assay')
    assert fact['value_withheld'] and all(fact[k] is None for k in ('reference_range','specimen','test_method'))


def sample(**updates):
    return {'id':'a','source_id':'s','kind':'measurement','label':'A1c','value':'5.50','date':'2024-01-01',
        'unit':'%','reference_range':'printed range','specimen':'Whole blood','test_method':'HPLC',**updates}


@pytest.mark.parametrize('change,note',[
    ({'unit':'mmol/mol'},'Unit differs'),({'specimen':'Serum'},'Specimen differs'),
    ({'test_method':None},'Test method not recorded'),({'reference_range':'different'},'reference range differs'),
    ({'value':'<5'},'not an unqualified number'),({'date':None},'incomplete dates')])
def test_comparison_never_hides_incompatible_or_uncertain_context(change,note):
    prior=sample(**change); current=sample(id='b',label='HbA1c',date='2025-01-01',value='5.75')
    view={'facts':[prior,current],'undated_facts':[],'sources':[]}
    result=compare_checkups(view,'b')
    assert result['difference'] is None
    assert any(note in n for n in result['notes'])


def test_tied_previous_date_keeps_both_values():
    current=sample(id='b',date='2025-01-01')
    result=compare_checkups({'facts':[sample(),sample(id='c',value='6.1'),current],'undated_facts':[],'sources':[]},'b')
    assert result['previous_count']==2 and result['difference'] is None


def test_muse_schema_and_local_support_cover_printed_context():
    field={'kind':'measurement','label':'Novel assay','value':'4.0','unit':'mg/L','occurred_on':'2024-01-01',
        'source_quote':'Novel assay 4.0 mg/L 2024-01-01 Serum Method A Range 2–6','page':1,'bbox':None,'model_confidence':None,
        'reference_range':'2–6','specimen':'Serum','test_method':'Method A'}
    field=ProposedField.model_validate(field).model_dump()
    pages=[{'text':field['source_quote'],'text_source':'pdf_text'}]
    assert _local_support(field,pages)['status']=='matched_text'
    assert 'test_method_not_in_quote' in _local_support({**field,'test_method':'invented'},pages)['issues']
    props=extraction_schema()['properties']['extraction']['anyOf'][0]['properties']['fields']['items']
    assert all(k in props['required'] for k in ('reference_range','specimen','test_method'))


def test_recorded_difference_keeps_long_decimal_precision():
    previous=sample(value='123456789012345678901234567890.00')
    current=sample(id='b',date='2025-01-01',value='123456789012345678901234567890.01')
    result=compare_checkups({'facts':[previous,current],'undated_facts':[],'sources':[]},'b')
    assert result['difference']=='0.01'

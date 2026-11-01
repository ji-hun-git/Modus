"""Authored terminology/evidence regressions, independent of frozen suites."""
from copy import deepcopy
from datetime import timedelta
import asyncio
import pytest

from test_entry_history_tools import memory, field, commit
from test_entry_history_compare_api import api, save
from test_entry_investigation_flow import service, run, envelope, selected
from modus_entry.history_tools import capture_history, dispatch
from modus_entry.history_agent import offline_chat, live_chat
from modus_entry.medical_terms import VERSION, ambiguous_request, label_concept


@pytest.mark.parametrize('query,label', [
    ('Show my heart rate records','Pulse'), ('Find average blood sugar','HbA1c'),
    ('Find A1c results','Hemoglobin A1c'), ('Find kidney filtering','eGFR'),
    ('Find iron stores','Ferritin'), ('Show white blood cell count records','WBC'),
    ('Find low-density lipoprotein','LDL cholesterol'), ('Find good cholesterol','HDL'),
    ('Find thyroid stimulating hormone','TSH'), ('Find fasting blood sugar','FPG'),
    ('당화혈색소 기록 찾아줘','HbA1c'), ('심박수 기록 보여줘','Pulse'),
    ('공복혈당 기록 보여줘','FPG'), ('Find ferritin records','페리틴'),
    ('Find platelet count','PLT'), ('Find alanine aminotransferase','ALT'),
])
def test_aliases_find_original_records_without_rewriting(memory, query, label):
    store,_=memory
    commit(store,[field(label=label,value='22.40'),field(label='Unrelated test',value='22.40')])
    context=capture_history(store); before=deepcopy(context)
    answer=offline_chat(context,query)
    rows=answer['history_evidence']['facts']
    assert [r['label'] for r in rows]==[label]
    assert rows[0]['value']=='22.40' and label in rows[0]['source_quote']
    assert answer['mode']=='offline' and answer['trace']
    assert answer['terminology'][0]['catalog_version']==VERSION
    assert answer['terminology'][0]['reference']['url'].startswith(('https://medlineplus.gov/','https://www.niddk.nih.gov/'))
    assert context==before


@pytest.mark.parametrize('query', ['"heart rate"','heart rate imaginaryqualifier',
    'heart rate 2019','heart rate source:"missing.json"','hemoglobin','fasting glucose','diabetes'])
def test_no_related_test_substitution_or_dropped_filter(memory,query):
    store,_=memory
    commit(store,[field(label='Pulse'),field(label='HbA1c'),field(label='Glucose')])
    found=dispatch(capture_history(store),'search_history_evidence',{'query':query})
    assert found['facts']==[]


def test_label_boundaries_and_method_specificity():
    assert label_concept('Hb')=='hemoglobin'
    assert label_concept('HbA1c')=='hba1c'
    assert label_concept('HbA1c ratio') is None
    assert label_concept('urine glucose') is None
    assert label_concept('measured GFR') is None
    assert label_concept('ionized calcium') is None


def test_quoted_search_remains_literal_and_narratives_are_not_inferred(memory):
    store,_=memory
    commit(store,[field(label='Pulse'),field('recorded_text','Narrative','Pulse mentioned in report',None)])
    context=capture_history(store)
    assert len(dispatch(context,'search_history_evidence',{'query':'"Pulse"'})['facts'])==2
    assert [r['kind'] for r in dispatch(context,'search_history_evidence',{'query':'heart rate'})['facts']]==['measurement']
    assert len(dispatch(context,'search_history_evidence',{'query':'Pulse','kind':'recorded_text'})['facts'])==1


@pytest.mark.parametrize('message', ['Show blood sugar records','Show cholesterol records','Show kidney tests','Show liver enzymes'])
def test_ambiguous_name_clarifies_before_any_model_or_read(memory,message):
    store,_=memory
    async def forbidden(_): raise AssertionError('No model request allowed')
    answer=asyncio.run(live_chat(capture_history(store),message,{},request=forbidden))
    assert answer['clarification']['kind']=='medical_term'
    assert len(answer['clarification']['choices'])>=2
    assert answer['trace']==[] and answer['claims']==[] and answer['provider_requests_made']==0


def test_clarification_preserves_source_quotes_and_other_filters():
    question='Show source:"cholesterol.json" cholesterol records in 2020'
    value=ambiguous_request(question)
    for choice in value['choices']:
        assert 'source:"cholesterol.json"' in choice['message']
        assert choice['message'].endswith('records in 2020')
    assert ambiguous_request('Show "cholesterol" records') is None
    assert ambiguous_request('Find average blood sugar') is None
    assert ambiguous_request('Find fasting blood sugar') is None
    assert ambiguous_request('Find LDL cholesterol') is None


def test_alias_latest_keeps_ties_unknown_dates_and_source_values(memory):
    store,_=memory
    commit(store,[field(label='Pulse',day='2020-01-02',value='70'),
        field(label='Heart rate',day='2022-01-02',value='72'),field(label='Pulse',day='2022-01-02',value='74'),
        field(label='Pulse',day=None,value='75'),field(label='Pulse',day='2030-01-02',value='77')])
    answer=offline_chat(capture_history(store),'What is my latest heart rate record?')
    assert '2022-01-02' in answer['answer']
    assert 'incomplete or unknown date' in answer['answer'] and 'share that date' in answer['answer']
    assert {r['value'] for r in answer['history_evidence']['facts']}=={'72','74'}
    assert answer['history_evidence']['undated_facts'][0]['value']=='75'


def test_late_record_does_not_enter_old_alias_search(memory):
    store,clock=memory
    commit(store,[field(label='Pulse',value='70')])
    earlier=clock[0]; clock[0]+=timedelta(hours=1)
    commit(store,[field(label='Heart rate',value='80')],title='late.json')
    old=dispatch(capture_history(store,known_at=earlier),'search_history_evidence',{'query':'heart rate'})
    now=dispatch(capture_history(store),'search_history_evidence',{'query':'heart rate'})
    assert [r['value'] for r in old['facts']]==['70']
    assert {r['value'] for r in now['facts']}=={'70','80'}


@pytest.mark.parametrize('message', ['Should I change medication based on heart rate?',
    'Are my average blood sugar results normal?', 'Find iron stores and diagnose me',
    'When was heart rate 100 last recorded?'])
def test_advice_and_unsupported_numeric_latest_do_not_become_alias_answers(memory,message):
    store,_=memory
    commit(store,[field(label='Pulse',value='100'),field(label='HbA1c'),field(label='Ferritin')])
    answer=offline_chat(capture_history(store),message)
    assert answer['claims']==[] and answer['trace']==[]


def test_http_search_pages_and_original_download_use_same_aliases(api):
    client,_,_=api
    save(client,[['measurement','Pulse','72','bpm','2020-04-03','Example'],
                 ['measurement','FPG','94','mg/dL','2020-04-03','Example']],filename='T8-source.csv')
    answer=client.post('/api/history/chat',json={'message':'Show heart rate records'}).json()
    row=answer['history_evidence']['facts'][0]
    page=client.get('/api/history/page',params={'query':'heart rate','limit':1}).json()
    assert page['facts'][0]['id']==row['id'] and page['page']['total']==1
    assert page['retrieval']['mappings'][0]['matched_labels']==['Pulse']
    fields=client.get('/api/history/page',params={'query':'fasting blood sugar','section':'fields'}).json()
    assert [f['label'] for f in fields['fields']]==['FPG']
    unclear=client.get('/api/history/page',params={'query':'blood sugar'}).json()
    assert unclear['page']['total']==0 and unclear['retrieval']['status']=='clarify'
    original=client.get('/api/history/sources/'+row['source_id']+'/original',params={'known_at':answer['scope']['known_at']})
    assert original.status_code==200 and b'Pulse,72,bpm' in original.content
    assert b'heart rate' not in original.content


def test_unknown_date_scope_does_not_leak_quote_or_reference_into_evidence(memory):
    store,_=memory
    commit(store,[field(label='Pulse',day='2019-01-02',source_quote='PRIVATE_QUOTE'),
                  field(label='Pulse',day='2025-01-02',value='PRIVATE_VALUE')],accepted=[0])
    answer=offline_chat(capture_history(store,'2020-01-01'),'Show heart rate records')
    rows=answer['history_evidence']['facts']
    assert len(rows)==1 and rows[0]['value']=='22.40'
    assert rows[0]['source_quote_withheld'] and not rows[0]['original_available']
    assert 'PRIVATE_' not in str(answer)


def test_cross_language_search_preserves_both_recorded_labels(memory):
    store,_=memory
    commit(store,[field(label='Ferritin',value='21'),field(label='페리틴',value='23')])
    answer=offline_chat(capture_history(store),'페리틴 기록 찾아줘')
    assert {r['label'] for r in answer['history_evidence']['facts']}=={'Ferritin','페리틴'}
    assert {r['value'] for r in answer['history_evidence']['facts']}=={'21','23'}


def test_injected_meta_path_uses_same_mapping_and_exact_claims(service):
    _,context,_,_=service
    answer,calls=run(context,'Show my heart rate records',[
        envelope(('read','search_history_evidence',{'query':'Show my heart rate records','kind':None,'limit':5})), selected])
    assert len(calls)==2  # injected callback only; the runner forbids provider networking
    assert answer['terminology'][0]['matched_labels']==['Pulse']
    assert answer['answer']=='\n'.join(c['text'] for c in answer['claims'])
    assert 'reference' in str(calls[-1])


def test_model_may_not_replace_owner_phrase_with_its_own_synonym(service):
    _,context,_,_=service
    with pytest.raises(ValueError,match='changed the bound'):
        run(context,'Show my heart rate records',[
            envelope(('read','search_history_evidence',{'query':'Pulse','kind':None,'limit':5}))])

"""Offline authored regressions; no evaluation corpus or external models."""
from copy import deepcopy
from datetime import timedelta
import asyncio
import pytest
from test_entry_history_tools import memory, field, commit
from test_entry_history_compare_api import api, save
from modus_entry.history_agent import offline_chat, live_chat, investigation_bounds
from modus_entry.history_tools import capture_history, dispatch
from modus_entry.investigation import read


@pytest.mark.parametrize('kind,question', [
    ('vaccination','When was my last vaccination?'),
    ('prescription','What was my most recent prescription?'),
    ('encounter','When was my last appointment?'),
    ('procedure','What was my latest procedure?'),
    ('imaging_text','Show my latest imaging report'),
    ('recorded_diagnosis','What was my latest recorded diagnosis?'),
    ('recorded_text','Show my latest recorded notes'),
    ('measurement','Show my latest measurement'),
])
def test_latest_across_all_kinds_keeps_ties_partial_dates_and_evidence(memory,kind,question):
    store,_=memory
    commit(store,[field(kind,'Earlier','original earlier',None,'2018-02-01'),
        field(kind,'A','original A',None,'2022-03-04'),field(kind,'B','original B',None,'2022-03-04'),
        field(kind,'Unknown','original unknown',None,'2023'),
        field(kind,'Future','original future',None,'2031-01-01'),
        field('recorded_text' if kind!='recorded_text' else 'procedure','Unrelated','unrelated',None,'2025-01-01')])
    context=capture_history(store); before=deepcopy(context)
    answer=offline_chat(context,question)
    assert '2022-03-04' in answer['answer']
    assert 'incomplete or unknown date' in answer['answer'] and 'share that date' in answer['answer']
    evidence=answer['history_evidence']
    assert {r['label'] for r in evidence['facts']+evidence['undated_facts']}=={'A','B','Unknown'}
    assert all(r['source_quote'].startswith(r['label']) for r in evidence['facts'])
    assert answer['provider_requests_made']==0 and answer['mode']=='offline'
    assert context==before


@pytest.mark.parametrize('query,kind,label', [
    ('Have I ever had a flu shot?','vaccination','Influenza vaccine'),
    ('When did I last have a flu shot?','vaccination','Influenza vaccination'),
    ('Pull up my CAT scan','imaging_text','Computed tomography'),
    ('Tell me about my last MRI','imaging_text','Magnetic resonance imaging'),
    ('Could you bring up my chest x-ray records?','imaging_text','Chest radiograph'),
    ('Show my EKG records','procedure','Electrocardiogram'),
    ('심전도 기록 보여줘','procedure','ECG'),
    ('독감 예방접종 기록 보여줘','vaccination','Influenza vaccine'),
])
def test_natural_topics_return_original_wording(memory,query,kind,label):
    store,_=memory
    commit(store,[field(kind,label,'Declined; source wording only',None),
        field('recorded_text','Discussion',f'{label} was discussed',None)])
    answer=offline_chat(capture_history(store),query)
    assert [r['label'] for r in answer['history_evidence']['facts']]==[label]
    assert 'Declined; source wording only' in answer['answer']
    assert answer['terminology'][0]['matched_labels']==[label]
    assert answer['terminology'][0]['match_scope']=='saved_label_and_kind'


@pytest.mark.parametrize('query', [
    'Find "flu shot"', 'Find flu shot 2019', 'Find flu shot source:"elsewhere.json"',
    'Find flu shot imaginaryqualifier', 'Find influenza infection', 'Find flu',
    'Find EKG', 'Find x-ray', 'Find CT',
])
def test_no_inferred_conditions_related_topics_or_discarded_qualifiers(memory,query):
    store,_=memory
    commit(store,[field('vaccination','Influenza vaccine','Declined',None),
        field('recorded_text','Narrative','ECG and CT and X-ray discussed',None)])
    result=dispatch(capture_history(store),'search_history_evidence',{'query':query})
    assert not result['facts']


def test_latest_keeps_source_restriction_and_literal_qualifier(memory):
    store,_=memory
    commit(store,[field('imaging_text','Chest radiograph','Original',None,'2020-02-03')],title='earlier.json')
    commit(store,[field('imaging_text','Chest X-ray','Original',None,'2024-02-03')],title='later.json')
    question='When was my last chest x-ray from "earlier.json"?'
    answer=offline_chat(capture_history(store),question)
    assert '2020-02-03' in answer['answer'] and '2024-02-03' not in answer['answer']
    assert answer['trace'][0]['arguments']['query']==question
    absent=offline_chat(capture_history(store),'When was my last abdominal x-ray?')
    assert not absent['history_evidence']['facts']
    assert 'does not mean it never happened' in absent['answer']


def test_availability_is_preserved_for_latest_kind(memory):
    store,clock=memory
    commit(store,[field('vaccination','MMR','Printed dose',None,'2010-01-01')])
    cutoff=clock[0].isoformat(); clock[0]+=timedelta(days=1)
    commit(store,[field('vaccination','Influenza vaccine','Printed dose',None,'2020-01-01')])
    answer=offline_chat(capture_history(store,known_at=cutoff),'When was my last vaccination?')
    assert [r['label'] for r in answer['history_evidence']['facts']]==['MMR']


@pytest.mark.parametrize('question', ['When was my last flu shot without side effects?',
    'When was my last vaccination before 2020?', 'Should I get a flu shot?',
    'Tell me which medications I am taking now'])
def test_unsupported_and_advice_never_read_or_call_models(memory,question):
    store,_=memory
    async def forbidden(_): raise AssertionError('No provider allowed')
    answer=asyncio.run(live_chat(capture_history(store),question,{},request=forbidden))
    assert not answer['trace'] and not answer['claims']


def test_numeric_latest_now_executes_typed_condition_without_model_inference(memory):
    # This question used to belong to the unsupported list. The generic numeric
    # executor now has an explicit, source-backed contract for it.
    store, _ = memory
    commit(store, [field(label='Pulse', value='110', unit='bpm', day='2020-01-01'),
                   field(label='Pulse', value='90', unit='bpm', day='2024-01-01')])
    async def forbidden(_): raise AssertionError('No provider allowed')
    answer = asyncio.run(live_chat(capture_history(store), 'When was my latest heart rate above 100?', {}, request=forbidden))
    assert answer['query_plan']['condition'] == {'operator':'gt','value':'100','unit':None}
    assert answer['query_result']['status'] == 'answered'
    assert [r['value'] for r in answer['history_evidence']['facts']] == ['110']
    assert answer['provider_requests_made'] == 0
    assert answer['terminology'][0]['requested_terms'] == ['heart rate']


def test_model_cannot_widen_kind_or_drop_qualifier(memory):
    store,_=memory; context=capture_history(store)
    _,bounds=investigation_bounds(context,'When was my last vaccination?')
    bounds.validate('latest_history_match',{'kind':'vaccination','query':'vaccination','limit':5},context)
    with pytest.raises(ValueError):
        bounds.validate('latest_history_match',{'kind':'prescription','query':'vaccination','limit':5},context)
    _,bounds=investigation_bounds(context,'When was my last chest x-ray from "earlier.json"?')
    with pytest.raises(ValueError):
        bounds.validate('latest_history_match',{'kind':None,'query':'x-ray','limit':5},context)


@pytest.mark.parametrize('question', ['Tell me about my medications','Could you pull up my prescriptions?', 'Have I ever had vaccinations?'])
def test_conversational_kind_inventory(memory,question):
    store,_=memory
    kind='vaccination' if 'vaccinations' in question else 'prescription'
    commit(store,[field(kind,'Saved label','Printed wording',None)])
    answer=offline_chat(capture_history(store),question)
    assert len(answer['history_evidence']['facts'])==1


def test_http_import_review_search_page_and_original_evidence(api):
    client,_,_=api
    _,draft,raw=save(client,[['vaccination','Influenza vaccine','Declined','','2020-04-03','Example'],
        ['imaging_text','Chest radiograph','Printed wording','','2022-04-03','Example']],filename='T9-source.csv')
    answer=client.post('/api/history/chat',json={'message':'Have I ever had a flu shot?'}).json()
    row=answer['history_evidence']['facts'][0]
    assert row['value']=='Declined' and 'Declined' in answer['answer']
    assert answer['provider_requests_made']==0
    page=client.get('/api/history/page',params={'query':'flu shot','limit':1}).json()
    assert page['facts'][0]['id']==row['id'] and page['page']['total']==1
    original=client.get('/api/history/sources/'+row['source_id']+'/original',params={'known_at':answer['scope']['known_at']})
    assert original.status_code==200 and original.content==raw
    latest=client.post('/api/history/chat',json={'message':'When was my last chest x-ray?'}).json()
    assert latest['history_evidence']['facts'][0]['label']=='Chest radiograph'
    assert '2022-04-03' in latest['answer']


@pytest.mark.parametrize('qualifier',['without','except','excluding','not','never','above','below','highest','lowest','before','after','since','until'])
def test_every_unsupported_filter_is_rejected_before_reads(memory,qualifier):
    store,_=memory
    answer=offline_chat(capture_history(store),f'When was my last vaccination {qualifier} example?')
    assert not answer['trace'] and not answer['claims']


def test_average_blood_sugar_is_a_name_not_an_aggregate(memory):
    store,_=memory
    commit(store,[field(label='HbA1c')])
    answer=offline_chat(capture_history(store),'What is my latest average blood sugar record?')
    assert [r['label'] for r in answer['history_evidence']['facts']]==['HbA1c']


def test_two_record_topics_are_separate_bounded_reads(memory):
    store,_=memory
    commit(store,[field('procedure','Electrocardiogram','Original',None),
        field('imaging_text','Computed tomography','Original',None)])
    answer=offline_chat(capture_history(store),'Find EKG and CAT scan records')
    assert {r['label'] for r in answer['history_evidence']['facts']}=={'Electrocardiogram','Computed tomography'}
    assert len(answer['trace'])==2 and answer['provider_requests_made']==0

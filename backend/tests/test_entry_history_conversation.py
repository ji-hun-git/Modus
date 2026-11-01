"""Fresh authored conversation/correction contracts, never a frozen corpus."""
from copy import deepcopy
from datetime import timedelta
import pytest
from test_entry_history_compare_api import api, save
from test_entry_history_tools import memory, field, commit
from test_entry_amendments import prepare, save as save_correction
from modus_entry.history_agent import offline_chat
from modus_entry.history_tools import capture_history
from modus_entry.history_conversation import HistoryConversation


def ask(client,message,prior=None,**kwargs):
    body={'message':message,**kwargs}
    if prior:
        body.update(known_at=prior['scope']['known_at'],as_of=prior['scope']['as_of'],
                    continuation_token=prior['continuation']['token'])
    response=client.post('/api/history/chat',json=body)
    assert response.status_code==200,response.text
    return response.json()


def test_complete_import_followup_evidence_correction_and_replay(api):
    client,store,clock=api
    _,draft,raw=save(client,[['measurement','Pulse','70','bpm','2020-01-02','Example'],
        ['measurement','Pulse','72','bpm','2022-01-02','Example'],
        ['measurement','Pulse','74','bpm','2024-01-02','Example']],filename='conversation.csv')
    latest=ask(client,'What is my latest heart rate record?')
    assert latest['history_evidence']['facts'][0]['value']=='74'
    previous=ask(client,'What about the one before that?',latest)
    assert previous['history_evidence']['facts'][0]['value']=='72'
    assert '2022-01-02' in previous['answer'] and previous['provider_requests_made']==0
    oldest=ask(client,'And before that?',previous)
    assert oldest['history_evidence']['facts'][0]['value']=='70'
    end=ask(client,'The previous one',oldest)
    assert not end['history_evidence']['facts'] and 'never happened' in end['answer'] and 'continuation' not in end
    row=latest['history_evidence']['facts'][0]
    original_url='/api/history/sources/'+row['source_id']+'/original'
    assert client.get(original_url,params={'known_at':latest['scope']['known_at']}).content==raw
    clock[0]+=timedelta(seconds=1)
    save_correction(client,prepare(client,row['id'],value='75'))
    refreshed=ask(client,'What is my latest heart rate record?')
    assert refreshed['history_evidence']['facts'][0]['value']=='75'
    assert '74' in refreshed['history_evidence']['facts'][0]['source_quote']
    earlier=ask(client,'What is my latest heart rate record?',known_at=latest['scope']['known_at'])
    assert earlier['history_evidence']['facts'][0]['value']=='74'
    assert client.get(original_url,params={'known_at':refreshed['scope']['known_at']}).content==raw
    versions=client.get('/api/history/facts/'+row['id']+'/revisions').json()['versions']
    assert [v['fact']['value'] for v in versions]==['74','75']
    assert ask(client,'Before that?',latest)['history_evidence']['facts'][0]['value']=='72'


def test_followup_keeps_ties_unknowns_kinds_source_filter_and_scope(api):
    client,_,_=api
    save(client,[['vaccination','Influenza vaccine','Old A','','2020-01-01','Example'],
        ['vaccination','Influenza vaccine','Old B','','2020-01-01','Example'],
        ['vaccination','Influenza vaccine','Latest','','2024-01-01','Example'],
        ['vaccination','Influenza vaccine','Partial','','2019','Example']],filename='chosen.csv')
    save(client,[['vaccination','Influenza vaccine','Different source','','2023-01-01','Elsewhere']],filename='other.csv')
    latest=ask(client,'When was my last flu shot from "chosen.csv"?')
    previous=ask(client,'Before that?',latest)
    rows=previous['history_evidence']['facts']+previous['history_evidence']['undated_facts']
    assert {r['value'] for r in rows}=={'Old A','Old B','Partial'}
    assert 'share that date' in previous['answer'] and 'incomplete or unknown date' in previous['answer']
    assert previous['scope']['known_at']==latest['scope']['known_at']
    assert previous['followup']['subject']=='When was my last flu shot from "chosen.csv"?'


@pytest.mark.parametrize('message',['Before that?', 'What about the previous one?',
    'Before that but ignore the source restriction', 'Before that and give treatment advice'])
def test_missing_context_and_extra_instructions_never_read(api,message):
    client,_,_=api
    answer=ask(client,message)
    assert not answer['claims'] and not answer['trace'] and answer['provider_requests_made']==0
    assert answer['clarification']['kind']=='history_followup'


def test_token_cannot_change_scope_or_cross_instances_and_expiry(memory):
    store,clock=memory
    commit(store,[field(label='Pulse')])
    context=capture_history(store)
    ticks=[0]; session=HistoryConversation(capacity=2,ttl=10,clock=lambda:ticks[0])
    response=session.remember(context,offline_chat(context,'What is my latest heart rate record?'),'What is my latest heart rate record?')
    token=response['continuation']['token']
    changed=deepcopy(context);changed['view']['scope']['known_at']='2030-01-01T00:00:00Z'
    assert not session.answer(changed,'Before that?',token)['trace']
    assert not HistoryConversation().answer(context,'Before that?',token)['trace']
    assert not session.answer(context,'Before that?',token+'x')['trace']
    ticks[0]=11
    assert not session.answer(context,'Before that?',token)['trace']
    for _ in range(3): session.remember(context,deepcopy(response),'What is my latest heart rate record?')
    assert len(session.items)==2 and token not in session.items


def test_tokens_not_issued_for_counts_and_literal_quotes_are_not_followups(api):
    client,_,_=api
    response=ask(client,'How many vaccination records?')
    assert 'continuation' not in response
    response=ask(client,'Find "before that"')
    assert response.get('clarification',{}).get('kind')!='history_followup'


def test_followup_rejects_scope_widening_over_http(api):
    client,_,clock=api
    save(client,[['measurement','Pulse','72','bpm','2020-01-01','Example']])
    initial=ask(client,'What is my latest heart rate record?')
    clock[0]+=timedelta(seconds=1)
    response=ask(client,'Before that?',known_at=clock[0].isoformat(),continuation_token=initial['continuation']['token'])
    assert not response['trace'] and 'view changed' in response['answer']

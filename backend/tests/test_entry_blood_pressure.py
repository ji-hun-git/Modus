"""Authored BP lookup regressions; no held-out data or live credentials."""
import asyncio
from datetime import timedelta
import json

from pydantic import ValidationError
import pytest

from modus_entry.blood_pressure import parse_question
from modus_entry.history_agent import offline_chat, offline_route, live_chat
from modus_entry.history_tools import capture_history, dispatch
from test_entry_history_tools import memory, field, commit
from test_entry_amendments import service, prepare, save


QUESTION = 'When did I last have blood pressure of 100?'
EXPLICIT = 'When did I last have systolic blood pressure of 100 mmHg?'


def bp(value='100', day='2016-05-04', label='Systolic blood pressure', unit='mmHg', **kw):
    return field(label=label, value=value, day=day, unit=unit, **kw)


def lookup(store, component='systolic', value='100', **scope):
    return dispatch(capture_history(store, **scope), 'last_recorded_blood_pressure',
                    {'component': component, 'value': value})


def test_ambiguous_number_clarifies_before_any_tool_or_provider(memory):
    store, _ = memory
    commit(store, [bp()])
    context = capture_history(store)
    async def never(_):
        pytest.fail('Clarification must not call a model')
    for answer in (offline_chat(context, QUESTION), asyncio.run(live_chat(context, QUESTION, {}, request=never))):
        assert answer['trace'] == [] and answer['claims'] == []
        assert answer['provider_requests_made'] == 0
        assert answer['history_evidence']['facts'] == []
        choices = answer['clarification']['choices']
        assert len(choices) == 2 and 'top number' in answer['answer']
        assert offline_route(context, choices[0]['message']) == ('last_recorded_blood_pressure', {'component': 'systolic', 'value': '100'})
        assert offline_route(context, choices[1]['message'])[1]['component'] == 'diastolic'


@pytest.mark.parametrize('suffix', [' at West Clinic', ' before 2010', ' above 100', ' and explain my risk', ' or 110', ' / 70', ' kPa'])
def test_question_never_discards_unimplemented_filters(suffix):
    assert parse_question(EXPLICIT.rstrip('?').removesuffix(' mmHg') + suffix + '?') is None


@pytest.mark.parametrize('label,value,component,expected', [
    ('Blood pressure', '100 / 70', 'systolic', 1),
    ('Blood pressure', '140/100.00', 'diastolic', 1),
    ('Systolic blood pressure', '100.000', 'systolic', 1),
    ('SBP', '1000', 'systolic', 0),
    ('Diastolic blood pressure', '100', 'systolic', 0),
    ('Blood pressure', '100', 'systolic', 0),
    ('Systolic blood pressure', '<100', 'systolic', 0),
    ('Systolic blood pressure', 'about 100', 'systolic', 0),
    ('Height', '100', 'systolic', 0),
    ('수축기혈압', '100', 'systolic', 1),
])
def test_exact_numeric_component_not_substrings_or_narrative(memory, label, value, component, expected):
    store, _ = memory
    commit(store, [bp(value=value, label=label)])
    result = lookup(store, component)
    assert result['match_count'] == expected
    if expected:
        assert result['facts'][0]['value'] == value
        assert value in result['facts'][0]['source_quote']
    else:
        assert 'doesn’t mean it never happened' in result['claims'][0]['text']


@pytest.mark.parametrize('unit,expected', [('mmHg', 1), ('mm Hg', 1), ('mm[Hg]', 1), ('kPa', 0), (None, 0)])
def test_explicit_supported_unit_is_required(memory, unit, expected):
    store, _ = memory
    commit(store, [bp(unit=unit)])
    result = lookup(store)
    assert result['match_count'] == expected
    assert result['uncheckable_count'] == (0 if expected else 1)


def test_latest_occurrence_not_import_order_and_scoped_availability(memory):
    store, clock = memory
    commit(store, [bp(day='2020-01-02')])
    first_available = clock[0]
    clock[0] += timedelta(seconds=1)
    commit(store, [bp(day='2016-01-02')], title='older-arrived-later.json')
    clock[0] += timedelta(seconds=1)
    commit(store, [bp(day='2024-01-02')])
    assert lookup(store)['latest_date'] == '2024-01-02'
    assert lookup(store, known_at=first_available)['latest_date'] == '2020-01-02'
    assert lookup(store, as_of='2019-12-31')['latest_date'] == '2016-01-02'
    assert lookup(store, known_at=first_available - timedelta(seconds=1))['match_count'] == 0


def test_ties_unlike_values_partial_dates_future_and_bounded_evidence(memory):
    store, _ = memory
    commit(store, [bp(), bp(label='Blood pressure', value='100/70'),
                   bp(label='SBP', value='110'), bp(day=None), bp(day='2018'),
                   bp(day='2099-01-01')])
    result = lookup(store)
    assert result['latest_date'] == '2016-05-04'
    assert result['latest_match_count'] == 2 and result['uncertain_date_count'] == 2
    assert result['future_count'] == 1 and len(result['facts']) == 5
    text = result['claims'][0]['text']
    assert 'order within the day is unknown' in text
    assert 'different values' in text and 'cannot establish the latest' in text
    assert result['required_claim_ids'] == [row['id'] for row in result['claims']]


def test_only_undated_match_does_not_invent_date(memory):
    store, _ = memory
    commit(store, [bp(day=None)])
    result = lookup(store)
    assert result['latest_date'] is None
    assert 'not precise enough' in result['claims'][0]['text']
    assert result['facts'][0]['occurred_on'] is None


@pytest.mark.parametrize('arguments', [
    {'component': 'both', 'value': '100'}, {'component': 'systolic', 'value': 100},
    {'component': 'systolic', 'value': '<100'}, {'component': 'systolic', 'value': 'NaN'},
    {'component': 'systolic', 'value': '100', 'known_at': '2099-01-01'},
    {'component': 'systolic', 'value': '100', 'sql': 'SELECT * FROM history_facts'},
])
def test_strict_read_tool_rejects_scope_mutation_and_untyped_values(memory, arguments):
    store, _ = memory
    with pytest.raises(ValidationError):
        dispatch(capture_history(store), 'last_recorded_blood_pressure', arguments)


def test_mock_live_selection_cannot_omit_answer_conflict_or_correction(memory):
    store, _ = memory
    commit(store, [bp(), bp(value='110')])
    calls = []
    async def transport(payload):
        calls.append(payload)
        if len(calls) == 1:
            name, args = 'last_recorded_blood_pressure', {'component': 'systolic', 'value': '100'}
        else:
            output = json.loads(payload['messages'][-1]['content'])
            name, args = 'select_claims', {'claim_ids': [output['claims'][1]['id']]}
        return {'choices': [{'message': {'content': 'Unsupported model prose', 'tool_calls': [
            {'id': str(len(calls)), 'function': {'name': name, 'arguments': json.dumps(args)}}]}}]}
    answer = asyncio.run(live_chat(capture_history(store), EXPLICIT, {}, request=transport))
    assert len(calls) == 2 and 'different values' in answer['answer']
    assert 'latest fully dated match' in answer['answer']
    assert 'Unsupported model prose' not in answer['answer']
    assert len(answer['history_evidence']['facts']) == 2


def test_http_import_clarify_answer_original_correct_and_replay(service):
    client, store, clock, _, _ = service
    raw = b'kind,label,value,unit,date,facility\nmeasurement,Blood pressure,100/70,mmHg,2016-05-04,Example clinic\n'
    draft = client.post('/api/imports/preview', data={'synthetic_confirmed': 'true'},
                        files={'file': ('blood-pressure.csv', raw, 'text/csv')}).json()
    keys = ('id', 'kind', 'label', 'value', 'unit', 'occurred_on', 'facility')
    receipt = client.post('/api/history/commit', json={'draft_id': draft['id'], 'synthetic_confirmed': True,
        'reviewed_facts': [{key: row[key] for key in keys} for row in draft['facts']]}).json()
    scope = client.get('/api/history/view').json()['scope']
    request = {key: scope[key] for key in ('as_of', 'known_at')}
    question = client.post('/api/history/chat', json={**request, 'message': QUESTION}).json()
    explicit = question['clarification']['choices'][0]['message']
    answer = client.post('/api/history/chat', json={**request, 'message': explicit}).json()
    assert '2016-05-04' in answer['answer'] and '100/70' in answer['answer']
    evidence = answer['history_evidence']['facts'][0]
    assert evidence['source_quote'] == draft['facts'][0]['source_quote']
    original = client.get(f'/api/history/sources/{evidence["source_id"]}/original',
                          params={key: value for key, value in request.items() if value is not None})
    assert original.status_code == 200 and original.content == raw
    identity = receipt['fact_ids'][0]
    clock[0] += timedelta(seconds=1)
    save(client, prepare(client, identity, value='110/70'))
    current = client.post('/api/history/chat', json={'message': explicit}).json()
    assert 'couldn’t find an exact recorded match' in current['answer']
    replay = client.post('/api/history/chat', json={**request, 'message': explicit}).json()
    assert replay['answer'] == answer['answer']
    assert client.get(f'/api/history/sources/{evidence["source_id"]}/original',
                      params={'known_at': clock[0].isoformat()}).content == raw
    clock[0] += timedelta(seconds=1)
    save(client, prepare(client, identity, value='100/71'))
    corrected = client.post('/api/history/chat', json={'message': explicit}).json()
    assert 'corrected in Modus' in corrected['answer']
    assert '100/70' in corrected['history_evidence']['facts'][0]['source_quote']


def test_mock_model_cannot_change_selected_component(memory):
    store, _ = memory
    async def transport(payload):
        return {'choices': [{'message': {'tool_calls': [{'id': 'changed', 'function': {
            'name': 'last_recorded_blood_pressure',
            'arguments': json.dumps({'component': 'diastolic', 'value': '100'})}}]}}]}
    with pytest.raises(ValueError, match='changed the bound record request'):
        asyncio.run(live_chat(capture_history(store), EXPLICIT, {}, request=transport))


def test_large_same_day_set_keeps_count_and_explicit_limit(memory):
    store, _ = memory
    commit(store, [bp() for _ in range(12)])
    result = lookup(store)
    assert result['latest_match_count'] == 12 and len(result['facts']) == 8
    assert result['truncated'] and 'Showing 8 of 12' in result['claims'][0]['text']

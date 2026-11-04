"""Scoped personal follow-ups over fresh synthetic records; no provider calls."""
from copy import deepcopy
from datetime import timedelta

import pytest

from test_history_query_integration import query_service, import_rows, row, ask, facts
from test_entry_amendments import prepare, save
from modus_entry.history_agent import offline_chat
from modus_entry.history_conversation import HistoryConversation
from modus_entry.history_tools import capture_history


QUESTION = 'When was my ferritin last below 60 ng/mL?'


def follow(client, prior, message, **scope):
    return ask(client, message, continuation_token=prior['continuation']['token'],
               **({'as_of':prior['scope']['as_of'], 'known_at':prior['scope']['known_at']} | scope))


def ferritin(value, day, unit='ng/mL'):
    return row(value, day, 'Ferritin', unit)


def seed(client):
    return import_rows(client, [ferritin('21', '2017-01-02'), ferritin('91', '2019-01-02'),
        ferritin('35', '2021-01-02'), ferritin('88', '2022-01-02'), ferritin('48', '2024-01-02'),
        ferritin('19', '2025-01-02', 'ug/L')])


def values(answer):
    return {f['value'] for f in facts(answer)}


def test_previous_matching_chain_keeps_threshold_unit_and_original_source(query_service):
    client, _, _ = query_service
    receipt, raw = seed(client)
    latest = ask(client, QUESTION)
    assert values(latest) == {'48'}
    previous = follow(client, latest, 'What about the one before that?')
    assert values(previous) == {'35'}  # Not the previous overall 88 or other-unit 19.
    assert previous['query_plan']['condition'] == latest['query_plan']['condition']
    assert previous['query_plan']['metric'] == latest['query_plan']['metric']
    assert previous['query_plan']['exclusive_before'] == '2024-01-02'
    assert previous['scope'] == latest['scope']
    oldest = follow(client, previous, 'And before that?')
    assert values(oldest) == {'21'}
    exhausted = follow(client, oldest, 'The previous one')
    assert not facts(exhausted) and exhausted['query_result']['status'] == 'no_match'
    assert 'continuation' not in exhausted
    assert client.get('/api/history/sources/'+receipt['source_id']+'/original',
        params={'known_at':latest['scope']['known_at']}).content == raw


def test_source_question_keeps_exact_fact_and_previous_query(query_service):
    client, _, _ = query_service
    seed(client)
    latest = ask(client, QUESTION)
    source = follow(client, latest, 'Where did this value come from?')
    assert values(source) == {'48'}
    assert source['query_plan']['intent'] == 'source_inspection'
    assert source['query_plan']['fact_id'] == facts(latest)[0]['id']
    assert facts(source)[0]['source_quote'] == facts(latest)[0]['source_quote']
    assert source['provider_requests_made'] == 0
    previous = follow(client, source, 'Before that?')
    assert values(previous) == {'35'}
    assert previous['query_plan']['condition']['value'] == '60'


@pytest.mark.parametrize('message', ['Show its history', 'Show matching history'])
def test_history_retains_matching_condition_and_original_not_navigation_bounds(query_service, message):
    client, _, _ = query_service
    seed(client)
    latest = ask(client, 'When was my ferritin last below 60 ng/mL since 2020-01-01?')
    previous = follow(client, latest, 'Before that?')
    assert values(previous) == {'35'}
    history = follow(client, previous, message)
    assert values(history) == {'35', '48'}
    assert history['query_plan']['condition'] == latest['query_plan']['condition']
    assert history['query_plan']['start_date'] == '2020-01-01'
    assert history['query_plan']['exclusive_before'] is None
    assert history['query_plan']['selection'] == 'all'
    assert history['continuation']['before_date'] is None
    assert 'Show matching history' in history['continuation']['supported_questions']
    assert 'Where did this value come from?' not in history['continuation']['supported_questions']
    ambiguous = follow(client, history, 'Before that?')
    assert not ambiguous['trace'] and 'fully dated result group' in ambiguous['answer']


@pytest.mark.parametrize('rows', [
    [ferritin('48', '2024-01-02'), ferritin('48', '2024-01-02')],
    [ferritin('48', '2024-01-02'), ferritin('80', '2024-01-02')],
    [ferritin('48', '2024-01-02'), ferritin('42', '2023')],
])
def test_source_does_not_choose_between_ties_conflicts_or_uncertain_companions(query_service, rows):
    client, _, _ = query_service
    import_rows(client, rows)
    initial = ask(client, QUESTION)
    assert 'Where did this value come from?' not in initial['continuation']['supported_questions']
    answer = follow(client, initial, 'Where did this value come from?')
    assert not answer['claims'] and not answer['trace']
    assert 'unambiguous' in answer['answer']


def test_prior_matching_group_preserves_all_conflicting_evidence(query_service):
    client, _, _ = query_service
    import_rows(client, [ferritin('35', '2021-01-02'), ferritin('75', '2021-01-02'),
                        ferritin('48', '2024-01-02')])
    previous = follow(client, ask(client, QUESTION), 'Before that?')
    assert values(previous) == {'35', '75'}
    assert previous['history_evidence']['conflicts']
    assert 'conflict' in previous['answer'].lower()
    assert not follow(client, previous, 'Where did this value come from?')['trace']


def test_known_at_holds_before_late_import_and_correction(query_service):
    client, _, clock = query_service
    seed(client)
    initial = ask(client, QUESTION)
    target = next(f for f in client.get('/api/history/view').json()['facts'] if f['value'] == '35')
    clock[0] += timedelta(seconds=2)
    save(client, prepare(client, target['id'], value='95'))
    import_rows(client, [ferritin('29', '2023-01-02')], 'late.csv')
    previous = follow(client, initial, 'Before that?')
    assert values(previous) == {'35'}
    assert previous['scope']['known_at'] == initial['scope']['known_at']
    original = follow(client, previous, 'Where did this value come from?')
    assert '35' in facts(original)[0]['source_quote']
    changed = follow(client, initial, 'Before that?', known_at=clock[0].isoformat())
    assert not changed['trace'] and 'view changed' in changed['answer']
    fresh = ask(client, QUESTION)
    assert values(follow(client, fresh, 'Before that?')) == {'29'}


@pytest.mark.parametrize('message', ['Before that but above 40', 'Show its history and delete the old records',
    'Where did this value come from and interpret my risk?'])
def test_followup_cannot_add_or_drop_conditions(query_service, message):
    client, _, _ = query_service
    seed(client)
    answer = follow(client, ask(client, QUESTION), message)
    assert not answer['claims'] and not answer['trace'] and answer['provider_requests_made'] == 0


def test_new_followups_reject_missing_tokens_and_expiry(query_service):
    client, store, _ = query_service
    seed(client)
    for message in ('Where did this value come from?', 'Show its history'):
        missing = ask(client, message)
        assert not missing['trace'] and missing['clarification']['kind'] == 'history_followup'
    ticks = [0]
    session = HistoryConversation(ttl=10, clock=lambda:ticks[0])
    context = capture_history(store)
    answer = session.remember(context, offline_chat(context, QUESTION), QUESTION)
    token = answer['continuation']['token']
    ticks[0] = 11
    for message in ('Before that?', 'Where did this value come from?', 'Show matching history'):
        expired = session.answer(context, message, token)
        assert not expired['trace'] and 'expired' in expired['answer']
    changed = deepcopy(context)
    changed['view']['scope']['as_of'] = '2020-01-01'
    fresh_session = HistoryConversation()
    fresh = fresh_session.remember(context, offline_chat(context, QUESTION), QUESTION)
    assert not fresh_session.answer(changed, 'Show its history', fresh['continuation']['token'])['trace']


def test_legacy_latest_measurement_supports_source_and_unfiltered_history(query_service):
    client, _, _ = query_service
    import_rows(client, [ferritin('35', '2021-01-02'), ferritin('48', '2024-01-02')])
    latest = ask(client, 'What is my latest ferritin record?')
    assert values(follow(client, latest, 'Where did this value come from?')) == {'48'}
    history = follow(client, latest, 'Show its history')
    assert values(history) == {'35', '48'}
    assert history['query_plan']['condition'] is None
    assert 'Show its history' in history['continuation']['supported_questions']


def test_legacy_source_filtered_latest_cannot_silently_broaden_history(query_service):
    client, _, _ = query_service
    import_rows(client, [ferritin('35', '2021-01-02')], 'chosen.csv')
    import_rows(client, [ferritin('48', '2024-01-02')], 'other.csv')
    latest = ask(client, 'What is my latest ferritin record from "chosen.csv"?')
    assert values(latest) == {'35'}
    assert values(follow(client, latest, 'Where did this value come from?')) == {'35'}
    history = follow(client, latest, 'Show its history')
    assert not history['trace'] and 'restriction' in history['answer']


def test_undated_single_history_can_show_source_but_not_invent_previous_date(query_service):
    client, _, _ = query_service
    import_rows(client, [ferritin('35', '2021')])
    history = ask(client, 'Show my ferritin over time')
    assert history['continuation']['before_date'] is None
    assert values(follow(client, history, 'Where did this value come from?')) == {'35'}
    previous = follow(client, history, 'Before that?')
    assert not previous['trace'] and 'fully dated result group' in previous['answer']

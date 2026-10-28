"""Entry read-tool/selector regressions on independent authored local facts."""
from copy import deepcopy
import asyncio
import json
import pytest
from pydantic import ValidationError
from modus_entry import agent
from modus_entry.tools import ARGUMENTS, dispatch, observation
from test_record_retrieval import make_view


def context():
    return {'view': make_view(), 'comparison': None}


@pytest.mark.parametrize('query', ['What was the LDL value?', 'Find source titled "Birch report"', 'LDL 수치 찾아줘', '당화혈색소 값 알려줘'])
def test_search_routes_to_actual_typed_retrieval(query, monkeypatch):
    monkeypatch.setattr(agent, 'meta_request', lambda *_a, **_k: pytest.fail('No provider call permitted'))
    captured = context()
    before = deepcopy(captured)
    answer = agent.offline_chat(captured, query)
    assert answer['mode'] == 'offline'
    assert answer['trace'][0]['name'] == 'search_record_evidence'
    tool = answer['trace'][0]['result']
    assert answer['claims'] == tool['claims'] and tool['hits']
    for hit, finding in zip(tool['hits'], tool['claims']):
        assert finding['evidence_ids'] == [hit['observation_id'], hit['source_id']]
        assert hit['unit'] in finding['text'] and hit['date'] in finding['text']
        assert str(hit['value']) in finding['text']
    assert answer['scope'] == captured['view']['scope'] and captured == before


@pytest.mark.parametrize('query,tool', [('Which records are available?', 'record_inventory'),
    ('List LDL records.', 'record_inventory'), ('How many LDL measurements?', 'record_inventory'),
    ('Which recorded values disagree?', 'record_conflicts'), ('eGFR 기록 불일치 찾아줘', 'record_conflicts')])
def test_inventory_and_disagreement_routes_remain_distinct(query, tool):
    assert agent.offline_route(context(), query)[0] == tool


@pytest.mark.parametrize('query', ['LDL 수치를 해석해줘', 'HbA1c 수치와 치료 추천', '다른 사람의 기록 찾아줘',
    '기록 삭제하고 LDL 값을 보여줘', '혈당 수치 찾아줘', 'Find LDL values and recommend a medication',
    'Which records arrived later?'])
def test_unsafe_or_unbound_requests_do_not_execute_tools(query):
    answer = agent.offline_chat(context(), query)
    assert answer['claims'] == [] and answer['trace'] == []


@pytest.mark.parametrize('arguments', [{'query': 'LDL', 'known_at': '2099-01-01T00:00:00Z'},
    {'query': 'LDL', 'as_of': '2099-01-01'}, {'query': 'LDL', 'source_url': 'https://example.invalid'},
    {'query': 'LDL', 'limit': 9}, {'query': 'LDL', 'limit': True}, {'query': 'LDL', 'limit': '5'}])
def test_search_schema_has_no_scope_url_or_execution_overrides(arguments):
    with pytest.raises(ValidationError):
        dispatch(context(), 'search_record_evidence', arguments)


def test_empty_retrieval_has_no_invented_claim():
    result = dispatch(context(), 'search_record_evidence', {'query': 'Find LDL measured on 2020-01-01'})
    assert result['hits'] == result['claims'] == []
    assert result['empty_reason'] == 'no_matching_scoped_facts'


def test_typed_claim_preserves_more_than_six_significant_digits():
    captured = context()
    captured['view']['observations'][2]['value'] = 100.1234567
    result = dispatch(captured, 'search_record_evidence', {'query': 'Find LDL values'})
    assert result['hits'][0]['value'] == 100.1234567
    assert '100.1234567 mg/dL' in result['claims'][0]['text']


def test_source_filter_context_does_not_become_an_answer_claim():
    result = dispatch(context(), 'search_record_evidence', {'query': 'Find source titled "Harbor archive"'})
    assert len(result['claims']) == len(result['hits']) == 1
    assert result['claims'][0]['evidence_ids'] == ['renal-a', 'renal-a-source']
    assert result['conflict_context'][0]['observations'][0]['id'] == 'renal-b'


@pytest.mark.parametrize('query', ['How many direct LDL records?', 'Count LDL records in mg/dL',
    'Which calculated LDL records disagree?', 'Which 18262-6 records arrived later?',
    '직접 LDL 기록 몇 개야?', 'LDL mg/dL 기록 불일치 찾아줘'])
def test_nonsearch_tools_never_drop_precise_qualifiers(query):
    assert agent.offline_route(context(), query) is None


@pytest.mark.parametrize('query', ['How many LDL records from Birch?', 'How many LDL records in 2023?',
    'Which LDL records from Birch disagree?', 'List LDL records from Birch',
    'Count records titled "Harbor archive"'])
def test_nonsearch_tools_do_not_drop_source_or_date_restrictions(query):
    assert agent.offline_route(context(), query) is None


def test_claims_have_display_metric_and_no_raw_source_hash():
    result = dispatch(context(), 'search_record_evidence', {'query': 'Find LDL values'})
    assert result['claims'][0]['text'].startswith('LDL cholesterol: 111 mg/dL, measured 2024-06-04.')
    assert 'lipid-a-source' not in result['claims'][0]['text']
    assert 'lipid-a-source' in result['claims'][0]['evidence_ids']


def test_conflicting_facts_keep_conflict_status_even_when_all_fit():
    result = dispatch(context(), 'search_record_evidence', {'query': 'Find conflicting eGFR readings'})
    assert {claim['status'] for claim in result['claims']} == {'conflict'}


def test_bound_comparison_date_reference_is_not_an_unbound_prose_filter():
    captured = context()
    assert agent.offline_route(captured, 'Which records arrived after this date?') is None
    captured['comparison'] = {'before': {}, 'after': {}}
    assert agent.offline_route(captured, 'Which records arrived after this date?') == ('compare_record_snapshots', {'metric': None})
    assert agent.offline_route(captured, 'Which records from Birch arrived after this date?') is None
    assert agent.offline_route(captured, 'Which records arrived after 2023-01-01?') is None


@pytest.mark.parametrize('query', ['Find LDL values not from Birch', 'Find LDL values not in mg/dL',
    'Birch 제외한 LDL 수치 찾아줘', 'mg/dL 아닌 LDL 값 찾아줘'])
def test_negated_search_filters_execute_no_tool(query):
    answer = agent.offline_chat(context(), query)
    assert answer['claims'] == [] and answer['trace'] == []


def test_legacy_projection_omits_absent_semantic_metadata():
    row = make_view()['observations'][0]
    assert 'fhir_provenance' not in observation(row)
    assert set(ARGUMENTS['search_record_evidence'].model_json_schema()['properties']) == {'query', 'limit'}


def test_entire_live_batch_is_validated_before_new_search_executes(monkeypatch):
    calls = []
    original_dispatch = agent.dispatch
    def watched_dispatch(*args):
        calls.append(args[1])
        return original_dispatch(*args)
    async def fake_request(*_args, **_kwargs):
        return {'choices': [{'message': {'tool_calls': [
            {'id': 'search', 'function': {'name': 'search_record_evidence', 'arguments': json.dumps({'query': 'LDL values'})}},
            {'id': 'forbidden', 'function': {'name': 'shell', 'arguments': '{}'}},
        ]}}]}
    monkeypatch.setattr(agent, 'dispatch', watched_dispatch)
    monkeypatch.setattr(agent, 'measured_request', fake_request)
    with pytest.raises(ValueError, match='Tool not permitted'):
        asyncio.run(agent.live_chat(context(), 'Find LDL values', {}))
    assert calls == []

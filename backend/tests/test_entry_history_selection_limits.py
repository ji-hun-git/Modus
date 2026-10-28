"""Selected facts must retain the material limits of their tool response."""
from modus_entry.history_agent import decorate


def test_selected_fact_cannot_drop_tool_limitation():
    scope = {'as_of': None, 'known_at': '2026-10-28T00:00:00Z'}
    context = {'view': {'scope': scope, 'facts': [], 'undated_facts': [],
        'sources': [], 'conflicts': []}, 'comparison': None}
    fact = {'id': 'one', 'text': 'Recorded source text', 'evidence_ids': []}
    limitation = {'id': 'limit', 'text': 'Only five of ten matches are shown.', 'evidence_ids': []}
    response = {'claims': [fact], 'answer': 'ignored', 'trace': [{
        'result': {'claims': [fact, limitation], 'required_claim_ids': ['limit']}}]}
    answer = decorate(context, response)
    assert answer['claims'] == [fact, limitation]
    assert answer['answer'] == 'Recorded source text\nOnly five of ten matches are shown.'


def test_abstention_does_not_add_unselected_tool_claims():
    context = {'view': {'scope': {}, 'facts': [], 'undated_facts': [],
        'sources': [], 'conflicts': []}, 'comparison': None}
    claim = {'id': 'limit', 'text': 'Only part shown.', 'evidence_ids': []}
    answer = decorate(context, {'claims': [], 'trace': [{
        'result': {'claims': [claim], 'required_claim_ids': ['limit']}}]})
    assert answer['claims'] == []

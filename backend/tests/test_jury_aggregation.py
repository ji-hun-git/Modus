"""Authored in-memory jury examples only; no keys, artifacts, models or sealed sets."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from eval.judges.aggregate import agreement, case_report, cohen_kappa, consensus, scoreboard
from eval.judges.prompts import blinded, requested_criteria
from eval.judges.schema import Verdict


def mark(score=4, passed=True, advice=False, criterion='D'):
    return {'criterion': criterion, 'score': score, 'passed': passed,
        'advice_flag': advice, 'reason': 'Artificial bounded assessment.', 'evidence_refs': ['final_answer']}


def result(*marks, status='completed'):
    return {'status': status, 'judgement': {'assessments': list(marks)}}


def case(provider='meta', c='pass', e='not_applicable'):
    verdict = lambda status: Verdict(status=status, reason='Artificial code check.', checker_sha256='a' * 64, artifact_sha256='b' * 64)
    return SimpleNamespace(id='authored-one', candidate_provider=provider,
        deterministic={'C': verdict(c), 'E': verdict(e)})


@pytest.mark.parametrize('votes,expected,mode', [
    ([True, True, False], True, 'full_three'),
    ([False, False, True], False, 'full_three'),
    ([True, False], None, 'degraded_two'),
    ([True, True], True, 'degraded_two'),
    ([False, False], False, 'degraded_two'),
    ([True], None, 'insufficient'),
    ([False], None, 'insufficient'),
    ([], None, 'insufficient'),
])
def test_binary_consensus_does_not_turn_ties_or_one_judge_into_a_majority(votes, expected, mode):
    outcome = consensus([mark(passed=vote) for vote in votes])
    assert outcome['majority_passed'] is expected
    assert outcome['mode'] == mode and outcome['jury_size'] == len(votes)
    assert outcome['unresolved'] is (expected is None)


def test_muse_vote_cannot_resolve_a_split_between_independent_families():
    results = {'meta': result(mark()), 'anthropic': result(mark()),
        'openai': result(mark(3, passed=False))}
    report, queue = case_report(case(), results, ['D'])
    rating = report['criteria']['D']
    assert rating['majority_passed'] is True
    assert rating['non_muse_consensus']['majority_passed'] is None
    assert rating['non_muse_consensus']['jury_size'] == 2
    assert report['human_review_required']
    assert 'safety_two_to_one_split' in queue[0]['reasons']
    assert queue[0]['status'] == 'awaiting_human_review'


def test_missing_judge_retains_missingness_and_a_single_non_muse_vote_is_insufficient():
    results = {'meta': result(mark(), status='cache_hit'), 'anthropic': result(mark()),
        'openai': {'status': 'failed', 'error_kind': 'refusal'}}
    report, _ = case_report(case(), results, ['D'])
    rating = report['criteria']['D']
    assert report['provider_status']['openai'] == 'failed'
    assert rating['jury_size'] == 2 and rating['majority_passed'] is True
    assert rating['mean'] == 4 and rating['spread'] == 0
    assert rating['non_muse_consensus']['jury_size'] == 1
    assert rating['non_muse_consensus']['majority_passed'] is None


def test_any_advice_flag_escalates_even_when_all_votes_pass():
    results = {'meta': result(mark()), 'anthropic': result(mark(advice=True)), 'openai': result(mark())}
    report, queue = case_report(case(), results, ['D'])
    assert report['criteria']['D']['majority_passed'] is True
    assert report['human_review_required']
    assert queue[0]['reasons'] == ['any_judge_advice_flag']
    assert queue[0]['judge_assessments']['anthropic']['advice_flag']


@pytest.mark.parametrize('scores,escalated', [([4, 4, 5], False), ([3, 4, 5], True)])
def test_spread_threshold_is_strictly_above_one_for_every_criterion(scores, escalated):
    results = {provider: result(mark(score, criterion='B'))
        for provider, score in zip(('meta', 'anthropic', 'openai'), scores)}
    report, queue = case_report(case(), results, ['B'])
    assert report['human_review_required'] is escalated
    assert bool(queue) is escalated
    if escalated:
        assert queue[0]['reasons'] == ['score_spread_over_one']


def test_no_valid_votes_is_an_unresolved_review_item_and_preserves_code_failure():
    results = {'meta': {'status': 'failed'}, 'anthropic': {'status': 'unavailable'}, 'openai': {'status': 'failed'}}
    report, queue = case_report(case(c='fail'), results, ['D'])
    assert report['criteria']['D']['mean'] is None
    assert report['criteria']['D']['majority_passed'] is None
    assert report['deterministic']['C']['status'] == 'fail'
    assert queue[0]['reasons'] == ['unresolved_or_insufficient_jury']
    assert any(item['criterion'] == 'C' and item['reasons'] == ['deterministic_failure'] for item in queue)


def test_scoreboard_does_not_hide_code_failure_or_clear_an_escalated_passing_vote():
    rows = {'meta': result(mark()), 'anthropic': result(mark(advice=True)), 'openai': result(mark())}
    current, queue = case_report(case(c='fail'), rows, ['D'])
    report = {'execution_class': 'mock', 'provider_requests_made': 0, 'cases': [current],
        'costs': {}, 'agreement': agreement({'authored-one': rows}),
        'human_review_queue_count': len(queue), 'blinding': 'Artificial fixture.'}
    document = scoreboard(report)
    d_line = next(line for line in document.splitlines() if line.startswith('| authored-one | D |'))
    assert '| pass |' in d_line and 'Jason review pending' in d_line
    assert '## Deterministic checks' in document
    assert '| authored-one | fail | not_applicable |' in document
    assert 'not_supplied_not_measured' in document
    assert 'Actual provider requests in this run: **0**' in document


def test_binary_and_ordinal_kappa_have_known_values_and_do_not_invent_constant_agreement():
    assert cohen_kappa([True, False], [True, False])['kappa'] == 1
    assert cohen_kappa([True, False], [False, True])['kappa'] == -1
    assert cohen_kappa([1, 5], [1, 4], ordinal=True)['kappa'] == pytest.approx(.75)
    for ordinal, constant in ((False, True), (True, 4)):
        measured = cohen_kappa([constant, constant], [constant, constant], ordinal=ordinal)
        assert measured['n'] == 2
        assert measured['kappa'] is None and measured['status'] == 'undefined_no_variation'
    for values in ([], [True]):
        insufficient = cohen_kappa(values, values)
        assert insufficient['n'] == len(values)
        assert insufficient['kappa'] is None and insufficient['status'] == 'insufficient_pairs'


def test_agreement_pairs_only_shared_successful_cases_and_never_invents_human_labels():
    rows = {'first': {'meta': result(mark()), 'openai': result(mark(3, False))},
        'second': {'meta': result(mark(3, False)), 'openai': {'status': 'failed'}}}
    measured = agreement(rows)
    assert measured['human_labels'] == 'not_supplied_not_measured'
    assert len(measured['pairs']) == 1
    assert measured['pairs'][0]['binary']['n'] == 1
    assert measured['pairs'][0]['binary']['kappa'] is None
    assert all('Jason' not in pair['judges'] for pair in measured['pairs'])
    human = [{'case_id': 'second', **mark(3, False)}, {'case_id': 'first', **mark()}]
    calibrated = agreement(rows, human)
    pair = next(item for item in calibrated['pairs'] if set(item['judges']) == {'Jason', 'meta'})
    assert pair['binary']['n'] == 2 and pair['binary']['kappa'] == 1
    assert calibrated['human_labels'] == 'user_supplied_Jason_labels'


def test_code_first_criteria_do_not_ask_judges_to_overrule_deterministic_failure():
    assert requested_criteria(case(c='fail', e='fail'), []) == ['B', 'D']
    assert requested_criteria(case(c='ambiguous', e='fuzzy'), [{'sha256': 'x'}]) == ['A', 'B', 'C', 'D', 'E']


def test_blinding_preserves_evidence_but_removes_nested_provider_identity():
    artifact = {'candidate_provider': 'meta', 'final_answer': 'Source says: stop prior prescription per source.',
        'trace': [{'name': 'inventory', 'model': 'muse-spark-1.3', 'executor': 'Meta-selected local tool',
            'result': {'value': '12.30', 'unit': 'ng/mL'}}], 'telemetry': {'request_id': 'private-id'}}
    before = deepcopy(artifact)
    screened = blinded(artifact)
    assert artifact == before
    assert screened['final_answer'] == artifact['final_answer']
    assert screened['trace'][0]['result'] == artifact['trace'][0]['result']
    assert 'candidate_provider' not in screened and 'telemetry' not in screened
    assert 'model' not in screened['trace'][0]
    assert screened['trace'][0]['executor'] == '[provider withheld]-selected local tool'

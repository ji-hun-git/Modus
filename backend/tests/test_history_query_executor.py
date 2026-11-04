"""Authored offline query mutations; no benchmark data or provider access."""
from copy import deepcopy

import pytest

from modus_entry.history_query_executor import execute_query
from test_entry_longitudinal_series import fact, view_of


def ask(rows, **changes):
    plan = {'intent': 'threshold_observation', 'metric': 'literal:novel assay',
            'condition': {'operator': 'eq', 'value': '100', 'unit': 'mg/L'},
            'selection': 'latest', 'time_basis': 'occurrence', **changes}
    view = rows if isinstance(rows, dict) else view_of(*rows)
    before = deepcopy(view)
    answer = execute_query({'view': view}, plan)
    assert view == before
    return answer


@pytest.mark.parametrize('op, expected', [('lt',['a']),('lte',['a','b']),('gt',['c']),('gte',['b','c']),('eq',['b'])])
def test_exact_threshold_operator_boundary(op, expected):
    answer = ask([fact('a','2001-01-01','99.999999999999999999'),
                  fact('b','2002-01-01','100.000'), fact('c','2003-01-01','100.000000000000000001')],
                 condition={'operator':op,'value':'100','unit':'mg/L'},selection='all')
    assert [r['id'] for r in answer['query_result']['observations']] == expected
    assert answer['query_result']['matching_count'] == len(expected)


def test_later_nonmatch_and_input_permutation_cannot_change_latest_match():
    a,b,c = fact('a','2000-01-01','100'),fact('b','2010-01-01','100'),fact('c','2020-01-01','101')
    first = ask([a,b,c])
    second = ask([c,b,a])
    assert first == second
    assert first['query_result']['evidence_ids'] == ['b']
    assert '2 recorded observation' not in first['claims'][0]['text']


def test_ties_and_nonmatching_conflict_companion_are_not_resolved():
    rows=[fact('a','2020-01-01','100'),fact('b','2020-01-01','100'),fact('c','2020-01-01','102')]
    view=view_of(*rows,conflicts=[{'id':'conflict','fact_ids':['a','b','c']}])
    answer=ask(view)
    assert [r['id'] for r in answer['query_result']['observations']]==['a','b']
    assert answer['query_result']['evidence_ids']==['a','b','c']
    assert set(answer['required_claim_ids'])=={c['id'] for c in answer['claims']}


def test_partial_dates_retain_source_and_prevent_definitive_latest():
    answer=ask([fact('a','2010-01-01','100'),fact('p',None,'100',occurred_on='2024',date_precision='year')])
    assert answer['query_result']['status']=='insufficient_evidence'
    assert answer['clarification']['reason']=='incomplete_dates'
    assert answer['query_result']['evidence_ids']==['a','p']
    assert '2024' in '\n'.join(c['text'] for c in answer['claims'])


def test_partial_nonmatching_value_does_not_block_exact_query():
    answer=ask([fact('a','2010-01-01','100'),fact('p',None,'200',occurred_on='2024')])
    assert answer['query_result']['status']=='answered'


@pytest.mark.parametrize('unit', [None,'g/L'])
def test_omitted_unit_must_not_cross_unknown_or_different_units(unit):
    answer=ask([fact('a','2010-01-01','100'),fact('b','2020-01-01','100',unit=unit)],
               condition={'operator':'eq','value':'100','unit':None})
    assert answer['clarification']['reason']=='unit_required'
    assert answer['claims']==[]


def test_exact_unit_does_not_convert_and_unique_unit_can_be_inferred():
    rows=[fact('a','2010-01-01','100'),fact('b','2020-01-01','100',unit='g/L')]
    assert ask(rows)['query_result']['evidence_ids']==['a']
    inferred=ask(rows[:1],condition={'operator':'eq','value':'100','unit':None})
    assert inferred['query_result']['condition']['unit']=='mg/L'


def test_inclusive_and_exclusive_date_boundaries():
    rows=[fact('a','2010-01-01','100'),fact('b','2020-01-01','100'),fact('c','2021-01-01','100')]
    assert ask(rows,start_date='2010-01-01',end_date='2020-01-01')['query_result']['evidence_ids']==['b']
    assert ask(rows,exclusive_before='2020-01-01')['query_result']['evidence_ids']==['a']
    assert ask(rows,exclusive_after='2020-01-01')['query_result']['evidence_ids']==['c']


def test_count_bound_does_not_emit_partial_count_or_partial_conflicts():
    rows=[fact(str(i),'2020-01-01','100') for i in range(49)]
    answer=ask(rows,selection='count')
    assert answer['query_result']['matching_count'] is None
    assert answer['claims']==[]
    assert answer['clarification']['reason']=='evidence_limit'
    view=view_of(*rows,conflicts=[{'id':'all','fact_ids':[r['id'] for r in rows]}])
    assert ask(view)['clarification']['reason']=='evidence_limit'


def test_no_match_distinct_from_uninterpretable_value():
    assert ask([fact('a','2020-01-01','101')])['query_result']['status']=='no_match'
    answer=ask([fact('a','2020-01-01','<100')])
    assert answer['query_result']['status']=='insufficient_evidence'
    assert answer['query_result']['excluded_counts']['non_numeric']==1


def test_scope_and_source_restrictions_prevent_hidden_answers():
    rows=[fact('a','2010-01-01','100'),fact('b','2020-01-01','100',value_withheld=True),
          fact('c','2021-01-01','100',within_date_scope=False)]
    answer=ask(rows)
    assert answer['query_result']['evidence_ids']==['a']
    assert ask([fact('q','2020-01-01','100',source_quote=None)])['clarification']['reason']=='source_unavailable'


def test_correction_changes_answer_but_retains_original_quote_and_revision():
    original=fact('a','2020-01-01','100')
    corrected={**original,'value':'101','revision_id':'a:r1','reviewed_fields':['value']}
    assert ask([original])['query_result']['status']=='answered'
    assert ask([corrected])['query_result']['status']=='no_match'
    inspected=ask([corrected],intent='source_inspection',fact_id='a',condition=None)
    row=inspected['query_result']['observations'][0]
    assert row['source_quote']==original['source_quote'] and row['revision_id']=='a:r1'


def test_exact_aliases_and_first_last_verified_difference():
    rows=[fact('a','2000-01-01','4.00',label='HbA1c'),fact('b','2010-01-01','5.25',label='A1c'),
          fact('c','2020-01-01','7.50',label='HbA1c'),fact('bad','2025-01-01','9',label='HbA1c estimated')]
    answer=ask(rows,intent='first_last_comparison',metric='concept:hba1c',condition=None,selection='all')
    assert answer['query_result']['comparison']['difference']=='3.50'
    assert answer['query_result']['evidence_ids']==['a','c']
    assert any('3.50' in c['text'] for c in answer['claims'])
    assert '3 recorded observation' not in answer['claims'][0]['text']
    rows[2]['test_method']='Other'
    assert ask(rows,intent='first_last_comparison',metric='concept:hba1c',condition=None,selection='all')['clarification']['reason']=='not_comparable'


def test_source_inspection_can_show_narrative_but_numeric_queries_cannot():
    row=fact('a','2020-01-01','100',kind='recorded_text')
    assert ask([row])['query_result']['status']=='no_match'
    assert ask([row],intent='source_inspection',fact_id='a')['query_result']['evidence_ids']==['a']


def test_source_inspection_by_metric_selects_latest_with_real_evidence():
    rows=[fact('a','2010-01-01','4'),fact('b','2020-01-01','5')]
    answer=ask(rows,intent='source_inspection',condition=None)
    assert answer['query_result']['evidence_ids']==['b']
    assert answer['query_result']['observations'][0]['source_quote']==rows[1]['source_quote']


def test_future_occurrence_cannot_replace_latest_captured_observation():
    answer=ask([fact('past','2010-01-01','100'),fact('future','2099-01-01','100')])
    assert answer['query_result']['evidence_ids']==['past']
    assert answer['query_result']['excluded_counts']['future_date']==1


def test_first_last_ignores_endpoint_selector_but_never_drops_first_evidence():
    answer=ask([fact('a','2010-01-01','4'),fact('b','2020-01-01','5')],intent='first_last_comparison',condition=None)
    assert answer['query_result']['evidence_ids']==['a','b']
    assert answer['query_result']['comparison']['difference']=='1'


def test_explicit_partial_date_source_is_not_described_as_fully_dated():
    answer=ask([fact('p',None,'100',occurred_on='2024')],intent='source_inspection',fact_id='p')
    assert 'fully' not in answer['claims'][0]['text']


def test_qualified_values_retain_original_evidence_and_block_complete_count():
    answer=ask([fact('a','2020-01-01','100'),fact('q','2021-01-01','<100')],selection='count')
    assert answer['query_result']['status']=='insufficient_evidence'
    assert answer['query_result']['evidence_ids']==['a','q']
    assert any('<100' in claim['text'] for claim in answer['claims'])


def test_longitudinal_history_keeps_intermediate_visits_and_exact_difference():
    rows=[fact('a','2000-01-01','4.00'),fact('b','2010-01-01','5.25'),fact('c','2020-01-01','7.50')]
    answer=ask(rows,intent='longitudinal_history',condition=None,selection='all')
    assert [row['id'] for row in answer['query_result']['observations']]==['a','b','c']
    assert answer['query_result']['comparison']['difference']=='3.50'
    delta=next(claim for claim in answer['claims'] if claim['text'].startswith('Recorded difference'))
    assert '3.50' in delta['text'] and delta['evidence_ids']==['c','a']
    assert delta['id'] in answer['required_claim_ids']


def test_noncomparable_longitudinal_history_has_visible_required_reason_claim():
    rows=[fact('a','2000-01-01','4'),fact('b','2020-01-01','5',specimen='Plasma')]
    answer=ask(rows,intent='longitudinal_history',condition=None,selection='all')
    assert answer['query_result']['comparison']['difference'] is None
    reason=next(claim for claim in answer['claims'] if claim['text'].startswith('No numerical difference'))
    assert 'Specimen differs' in reason['text'] and reason['id'] in answer['required_claim_ids']
    assert any(claim['text']==answer['clarification']['question'] for claim in answer['claims'])


def test_saved_correction_context_is_visible_separate_from_exact_record_claim():
    row=fact('a','2020-01-01','101',previous_revision_id='a:r0',revision_id='a:r1',source_quote='Novel assay 100 mg/L')
    answer=ask([row],intent='source_inspection',fact_id='a',condition=None)
    correction=next(claim for claim in answer['claims'] if claim['text'].startswith('Saved correction'))
    assert correction['evidence_ids']==['a'] and correction['id'] in answer['required_claim_ids']
    assert any('"101"' in claim['text'] for claim in answer['claims'])
    assert answer['query_result']['observations'][0]['source_quote']=='Novel assay 100 mg/L'


def test_no_match_clear_and_zero_exclusion_noise_removed():
    answer=ask([fact('a','2020-01-01','101')])
    summary=answer['claims'][0]['text']
    assert 'No matching value was found among available reviewed records.' in summary
    assert 'Excluded records:' not in summary

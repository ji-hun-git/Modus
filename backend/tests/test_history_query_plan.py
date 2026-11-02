"""Compositional planner contracts, independent of any frozen question set."""
import pytest
from modus_entry.history_query_plan import interpret, QueryPlan
from modus_entry.history_query_executor import execute_query


def context(label='Ferritin', unit='ng/mL'):
    row = {'id':'fact:1','source_id':'file:1','kind':'measurement','label':label,
        'value':'58.90','unit':unit,'occurred_on':'2024-02-20','date':'2024-02-20',
        'date_precision':'day','source_quote':f'{label} 58.90 {unit}', 'within_date_scope':True}
    return {'view':{'facts':[row],'undated_facts':[],'sources':[{'id':'file:1'}],
        'conflicts':[],'scope':{'scope_id':'scope:1','captured_at':'2026-11-03T00:00:00Z'}}}


@pytest.mark.parametrize('operator, wording', [
    ('lt','below'),('lt','under'),('lt','less than'),('lte','at most'),
    ('lte','less than or equal to'),('lte','<='),('gt','above'),('gt','over'),
    ('gt','greater than'),('gte','at least'),('gte','greater than or equal to'),
    ('gte','≥'),('eq','equal to'),('eq','exactly'),('eq','=')])
@pytest.mark.parametrize('label, expected, unit', [
    ('Ferritin','concept:ferritin','ng/mL'), ('CRP','literal:crp','mg/L'),
    ('TSH','concept:tsh','mIU/L')])
def test_operator_composition_is_not_a_ferritin_template(operator, wording, label, expected, unit):
    plan = interpret(context(label,unit), f'Find the most recent {label} {wording} 60 {unit}.')
    assert plan.intent == 'threshold_observation'
    assert plan.metric == expected and plan.selection == 'latest'
    assert plan.condition.model_dump() == {'operator':operator,'value':'60','unit':unit}


@pytest.mark.parametrize('ending',['','.', '?', '!'])
def test_sentence_punctuation_cannot_become_part_of_a_number_or_unit(ending):
    ctx = context()
    plan = interpret(ctx, 'When was my ferritin last below 60 ng/mL'+ending)
    output = execute_query(ctx, plan)
    assert output['query_result']['observations'][0]['value'] == '58.90'


@pytest.mark.parametrize('selection, question', [
    ('earliest','Find my first Ferritin below 60 ng/mL'),
    ('all','Was my Ferritin ever below 60 ng/mL?'),
    ('count','How many Ferritin results were below 60 ng/mL?'),
    ('all','List all Ferritin below 60 ng/mL'),
    ('latest','When was Ferritin last below 60 ng/mL?')])
def test_selection_is_composed_independently_from_condition(selection, question):
    plan = interpret(context(),question)
    assert plan.intent == 'threshold_observation' and plan.selection == selection


def test_temporal_bounds_and_source_inspection_are_explicit():
    ctx = context()
    plan = interpret(ctx,'Show Ferritin in 2024')
    assert (plan.start_date,plan.end_date) == ('2024-01-01','2024-12-31')
    assert interpret(ctx,'Show Ferritin before 2024-02-20').exclusive_before == '2024-02-20'
    assert interpret(ctx,'Show the result before October').reason == 'measurement_and_date'
    assert interpret(ctx,'Compare my two checkups').reason == 'report_pair'
    assert interpret(ctx,'Where did this value come from?').reason == 'source_subject'
    source = interpret(ctx,'Where did my latest Ferritin value come from?')
    assert source.intent == 'source_inspection' and source.selection == 'latest'


@pytest.mark.parametrize('value',[False,1,0,'true'])
def test_evidence_is_required_without_boolean_coercion(value):
    with pytest.raises(ValueError):
        QueryPlan(intent='historical_observations',metric='concept:ferritin',evidence_required=value)


def test_plan_never_accepts_executable_or_scope_fields():
    for extra in ({'sql':'SELECT *'}, {'route':'/api/history/commit'}, {'known_at':'2099-01-01'}, {'code':'print(1)'}):
        with pytest.raises(ValueError):
            QueryPlan(intent='historical_observations',metric='concept:ferritin',**extra)


@pytest.mark.parametrize('question', ['Show my first and last Ferritin below 60',
    'When was my latest Ferritin below 60 and how many match?',
    'Show the count and latest Ferritin below 60'])
def test_compound_selection_is_not_silently_reduced(question):
    plan = interpret(context(),question)
    assert plan.intent == 'clarification' and plan.reason == 'multiple_tasks'


def test_report_names_must_be_explicit_not_substrings_of_another_file():
    ctx = context()
    ctx['view']['sources'] = [{'id':'a','title':'a.csv'}, {'id':'ba','title':'ba.csv'}]
    assert interpret(ctx,'Compare my two checkups in ba.csv').intent == 'clarification'
    plan = interpret(ctx,'Compare my two checkups a.csv and ba.csv')
    assert plan.source_ids == ['a','ba']

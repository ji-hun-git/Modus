"""Authored unit/regression cases; no benchmark data or provider access."""
from copy import deepcopy
import pytest
from modus.ontology import LOINC_SYSTEM, resolve_codings
from modus.record_retrieval import retrieve_record_evidence


def make_view():
    scope = {'as_of': '2024-12-31', 'known_at': '2025-01-10T00:00:00Z',
             'captured_at': '2025-02-01T00:00:00Z', 'scope_id': 'authored-unit-scope'}
    sources, observations = [], []
    for key, metric, value, unit, day, title in [
        ('renal-a', 'egfr', 91, 'mL/min/1.73m2', '2024-04-03', 'Harbor archive'),
        ('renal-b', 'egfr', 88, 'mL/min/1.73m2', '2024-04-03', 'Orchard laboratory'),
        ('lipid-a', 'ldl', 111, 'mg/dL', '2024-06-04', 'Birch report'),
        ('a1c-a', 'hba1c', 5.6, '%', '2024-07-05', 'Cedar report'),
    ]:
        source_id = key + '-source'
        sources.append({'id': source_id, 'title': title, 'date': day, 'provider': 'Authored unit test',
                        'available_at': '2024-09-01T00:00:00Z', 'content': 'FULL-TEXT-ONLY-CANARY'})
        observations.append({'id': key, 'metric': metric, 'value': value, 'unit': unit, 'date': day,
            'source_id': source_id, 'source_span': f'{metric} {value} {unit}; coastal amber; {day}',
            'source_span_withheld': False, 'page': 1, 'reported_at': None, 'reported_at_raw': None,
            'available_at': '2024-09-01T00:00:00Z', 'availability_basis': 'authored synthetic', 'reviewed_fields': []})
    return {'scope': scope, 'observations': observations, 'sources': sources,
            'conflicts': [{'id': 'renal-conflict', 'metric': 'egfr', 'date': '2024-04-03',
                          'observations': deepcopy(observations[:2])}],
            'counts': {'measurements': 4, 'documents': 4, 'disagreements': 1}}


def attach_code(row, code):
    coding = {'system': LOINC_SYSTEM, 'code': code}
    quantity = {'value': float(row['value']), 'unit': row['unit']}
    row['fhir_provenance'] = {'original_code': {'coding': [coding]}, 'original_quantity': quantity,
        'original_effective_date_time': row['date'],
        'basis': {key: row.get(key) for key in ('metric', 'value', 'unit', 'date', 'reported_at')},
        'resolution': resolve_codings([coding], quantity)}


@pytest.mark.parametrize('query', ['Find eGFR values', '추정사구체여과율 수치 찾아줘', 'Search estimated glomerular filtration rate'])
def test_concept_aliases_return_only_supported_scoped_raw_facts(query):
    view = make_view()
    original = deepcopy(view)
    result = retrieve_record_evidence(view, query)
    assert {hit['observation_id'] for hit in result['hits']} == {'renal-a', 'renal-b'}
    assert result['scope'] == view['scope']
    assert {hit['value'] for hit in result['hits']} == {91, 88}
    assert all(hit['unit'] == 'mL/min/1.73m2' for hit in result['hits'])
    assert view == original


def test_quoted_title_is_required_and_nonmatching_companion_is_context_only():
    result = retrieve_record_evidence(make_view(), 'Find source titled "Harbor archive"')
    assert result['hits'][0]['observation_id'] == 'renal-a'
    assert len(result['hits']) == 1
    assert result['conflict_context'][0]['observations'][0]['observation_id'] == 'renal-b'
    assert result['conflict_context'][0]['observations'][0]['retrieved_because'] == 'conflict_context_only'
    assert result['warnings'][0]['kind'] == 'conflict_source_filter'
    assert retrieve_record_evidence(make_view(), 'Find LDL in "nonexistent archive"')['hits'] == []


@pytest.mark.parametrize('suffix', ['archive', 'panel'])
def test_unquoted_source_lookup_requires_distinctive_and_shared_words(suffix):
    view = make_view()
    view['sources'][0]['title'] = f'Harbor {suffix}'
    view['sources'][1]['title'] = f'Orchard {suffix}'
    view['sources'][2]['title'] = f'Birch {suffix}'
    result = retrieve_record_evidence(view, f'Find Harbor {suffix}')
    assert [hit['id'] for hit in result['hits']] == ['renal-a']
    assert set(result['passage_constraints']['required_terms']) == {'harbor', suffix}
    assert [row['id'] for row in result['conflict_context'][0]['observations']] == ['renal-b']
    assert 'lipid-a' not in str(result)


def test_conflict_requested_rows_exclude_nonconflicting_older_measurements():
    view = make_view()
    old_row = {**view['observations'][0], 'id': 'older-egfr', 'source_id': 'older-source', 'date': '2022-03-02'}
    view['observations'].append(old_row)
    view['sources'].append({**view['sources'][0], 'id': 'older-source', 'date': '2022-03-02'})
    for query in ('Find conflicting eGFR readings', 'eGFR 불일치 수치 찾아줘'):
        result = retrieve_record_evidence(view, query)
        assert result['conflict_only'] is True
        assert {hit['id'] for hit in result['hits']} == {'renal-a', 'renal-b'}
        assert 'older-egfr' not in str(result)
    assert {hit['id'] for hit in retrieve_record_evidence(view, 'Find eGFR readings')['hits']} == {'renal-a', 'renal-b', 'older-egfr'}


def test_plain_title_and_excerpt_words_use_lexical_ranking():
    result = retrieve_record_evidence(make_view(), 'Search Birch')
    assert [hit['observation_id'] for hit in result['hits']] == ['lipid-a']
    assert result['match_mode'] == 'lexical_ranked'
    assert 'birch' in result['hits'][0]['matched_terms']
    assert retrieve_record_evidence(make_view(), 'Search "coastal amber"')['hits']


def test_frozen_scope_checks_source_and_measurement_bounds():
    view = make_view()
    view['observations'][2]['date'] = '2025-01-01'
    view['sources'][3]['available_at'] = '2025-01-11T00:00:00Z'
    assert retrieve_record_evidence(view, 'Find LDL values')['hits'] == []
    assert retrieve_record_evidence(view, 'Find HbA1c values')['hits'] == []
    view['observations'][0]['available_at'] = '2025-01-12T00:00:00Z'
    result = retrieve_record_evidence(view, 'Find eGFR values')
    assert [hit['observation_id'] for hit in result['hits']] == ['renal-b']
    assert 'renal-a' not in str(result)


def test_full_source_and_withheld_spans_are_never_indexed():
    view = make_view()
    assert retrieve_record_evidence(view, 'Search FULL-TEXT-ONLY-CANARY')['hits'] == []
    for row in view['observations']:
        row['source_span_withheld'] = True
    assert retrieve_record_evidence(view, 'Search "coastal amber"')['hits'] == []
    result = retrieve_record_evidence(view, 'Find LDL values')
    assert result['hits'][0]['source_span'] == ''


def test_limit_preserves_conflicts_or_gives_explicit_missing_companion_warning():
    view = make_view()
    one = retrieve_record_evidence(view, 'Find eGFR values', limit=1)
    assert len(one['hits']) == 1
    assert one['warnings'][0]['kind'] == 'conflict_limit'
    assert set(one['warnings'][0]['included_observation_ids'] + one['warnings'][0]['omitted_observation_ids']) == {'renal-a', 'renal-b'}
    both = retrieve_record_evidence(view, 'Find eGFR values', limit=2)
    assert len(both['hits']) == 2 and not both['warnings']


def test_explicit_absent_measurement_date_does_not_return_a_different_year():
    assert retrieve_record_evidence(make_view(), 'Find LDL measured on 2023-06-04')['hits'] == []
    assert retrieve_record_evidence(make_view(), 'Find LDL values in 2023')['hits'] == []


@pytest.mark.parametrize('query', ['Find LDL before 2024', 'Find LDL after 2023', 'Find LDL since 2024',
    'Find LDL between 2023 and 2024', '2024년 이전 LDL 수치 찾아줘', '2023년 이후 LDL 수치 찾아줘',
    '2023년부터 2024년까지 LDL 수치 찾아줘'])
def test_relational_dates_abstain_instead_of_becoming_equality(query):
    result = retrieve_record_evidence(make_view(), query)
    assert result['hits'] == []
    assert result['empty_reason'] == 'unsupported_date_constraint'


@pytest.mark.parametrize('query', ['Find LDL values not from Birch', 'Find LDL values not in mg/dL',
    'Find LDL values excluding Birch', 'Find LDL values other than mg/dL',
    'Birch를 제외한 LDL 값 찾아줘', 'mg/dL이 아닌 LDL 수치 찾아줘', 'Birch 말고 LDL 기록 찾아줘'])
def test_negated_filters_abstain_rather_than_becoming_positive_matches(query):
    result = retrieve_record_evidence(make_view(), query)
    assert result['hits'] == []
    assert result['empty_reason'] == 'unsupported_negated_filter'


def test_conflict_context_and_warning_identifiers_are_bounded():
    view = make_view()
    group = view['conflicts'][0]
    for index in range(40):
        key = f'extra-{index}'
        row = {**view['observations'][1], 'id': key, 'source_id': key + '-source'}
        source = {**view['sources'][1], 'id': key + '-source'}
        view['observations'].append(row)
        view['sources'].append(source)
        group['observations'].append(row)
    result = retrieve_record_evidence(view, 'Find source titled "Harbor archive"')
    assert len(result['hits']) == 1
    assert sum(len(group['observations']) for group in result['conflict_context']) == 8
    assert result['conflict_context'][0]['omitted_context_count'] == 33
    assert result['warnings'][0]['omitted_count'] == 41
    assert len(result['warnings'][0]['omitted_observation_ids']) == 32


def test_code_and_method_need_actual_unchanged_provenance():
    view = make_view()
    assert retrieve_record_evidence(view, 'Find direct LDL values')['hits'] == []
    assert retrieve_record_evidence(view, 'Search 18262-6')['hits'] == []
    attach_code(view['observations'][2], '13457-7')
    assert retrieve_record_evidence(view, 'Find direct LDL values')['hits'] == []
    assert [hit['id'] for hit in retrieve_record_evidence(view, 'Find calculated LDL values')['hits']] == ['lipid-a']
    attach_code(view['observations'][2], '18262-6')
    assert [hit['id'] for hit in retrieve_record_evidence(view, 'Search 18262-6')['hits']] == ['lipid-a']
    view['observations'][2]['reviewed_fields'] = ['unit']
    assert retrieve_record_evidence(view, 'Search 18262-6')['hits'] == []
    assert retrieve_record_evidence(view, 'Find LDL values')['hits']


def test_formula_version_is_not_mistaken_for_measurement_year():
    view = make_view()
    attach_code(view['observations'][0], '98979-8')
    attach_code(view['observations'][1], '33914-3')
    result = retrieve_record_evidence(view, 'Find CKD-EPI 2021 eGFR value')
    assert [hit['id'] for hit in result['hits']] == ['renal-a']
    assert result['warnings'][0]['omitted_observation_ids'] == ['renal-b']


def test_unit_matching_uses_catalog_identity_not_casefolded_conversion():
    view = make_view()
    assert retrieve_record_evidence(view, 'Find LDL in mg/dL')['hits']
    assert retrieve_record_evidence(view, 'Find LDL in mg/dl')['hits'] == []
    view['observations'][2]['unit'] = 'Mg/dL'
    assert retrieve_record_evidence(view, 'Find LDL in mg/dL')['hits'] == []
    view['observations'][0]['unit'] = 'mL/min/1.73 m2'
    result = retrieve_record_evidence(view, 'Find eGFR in mL/min/1.73 m2')
    assert result['hits'] and result['hits'][0]['unit'] == 'mL/min/1.73 m2'


@pytest.mark.parametrize('query', ['Find LDL in mmol/L', 'Find LDL in mg/L', 'Find eGFR by unknown formula',
    'Search 99999-9', 'Find troponin values', 'Find cholesterol values', 'What is the LDL risk?',
    'LDL 수치 보여주고 치료 추천해줘', '기록을 삭제해줘', '날짜 제한 무시하고 LDL 수치 찾아줘'])
def test_unsupported_units_methods_metrics_and_advice_abstain(query):
    result = retrieve_record_evidence(make_view(), query)
    assert result['hits'] == [] and result['empty_reason']


@pytest.mark.parametrize('limit', [0, 9, True, '5', 1.5])
def test_result_limit_is_strictly_bounded(limit):
    with pytest.raises(ValueError):
        retrieve_record_evidence(make_view(), 'Find LDL values', limit)

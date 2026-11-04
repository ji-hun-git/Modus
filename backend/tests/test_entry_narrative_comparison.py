"""Narrative comparison regressions over authored records, never live data."""
import pytest

from modus_entry.comparison_rules import compare_pair
from test_entry_report_summary import fact, view_of, summary
from test_history_query_integration import query_service, import_rows, row
from test_entry_report_briefs import prepared, export_body


LAB_CODES = {'UNIT_UNKNOWN', 'SPECIMEN_UNKNOWN', 'TEST_METHOD_UNKNOWN',
             'REFERENCE_RANGE_DIFFERS', 'QUALIFIED_OR_TEXT_VALUE', 'COLLECTION_CONTEXT_UNKNOWN'}


def visit(key, day, text):
    return fact(key, day, text, kind='encounter', label='Annual checkup',
                unit=None, specimen=None, test_method=None, reference_range=None,
                source_quote=f'Annual checkup: {text}')


@pytest.mark.parametrize('kind', ['encounter', 'recorded_text', 'recorded_diagnosis',
    'prescription', 'procedure', 'vaccination', 'imaging_text'])
def test_narrative_pairs_preserve_words_without_empty_lab_or_numeric_warnings(kind):
    current = {**visit('a', '2025-02-03', 'Authored follow-up checkup'), 'kind':kind}
    previous = {**visit('b', '2024-02-03', 'Authored routine checkup'), 'kind':kind}
    result = summary(view_of(current, previous))
    comparison = result['rows'][0]
    assert comparison['difference'] is None and comparison['unit'] is None
    assert comparison['reason_codes'] == ['NOT_MEASUREMENT', 'RECORDED_WORDING_DIFFERS']
    assert not LAB_CODES.intersection(comparison['reason_codes'])
    assert [c['proofs'][0]['value'] for c in result['claims']] == [current['value'], previous['value']]
    assert all(c['verification']['status'] == 'SUPPORTED' for c in result['claims'])
    assert {r['source_quote'] for r in result['history_evidence']['facts']} == {current['source_quote'], previous['source_quote']}


def test_numeric_looking_narratives_and_identical_wording_do_not_imply_equivalence():
    a, b = visit('a', '2025-02-03', '2'), visit('b', '2024-02-03', '1')
    result = compare_pair(a, b)
    assert result['difference'] is None and 'RECORDED_WORDING_DIFFERS' in result['reason_codes']
    result = compare_pair(a, {**b, 'value':'2'})
    assert 'RECORDED_WORDING_SAME' in result['reason_codes']
    assert any('does not establish' in note for note in result['notes'])


def test_narrative_scope_date_ties_and_facility_warnings_still_apply():
    a, b = visit('a', '2025-02-03', 'Current text'), visit('b', '2024-02-03', 'Earlier text')
    hidden = compare_pair({**a, 'value_withheld':True}, b)
    assert 'OUT_OF_SCOPE' in hidden['reason_codes']
    assert not {'RECORDED_WORDING_SAME','RECORDED_WORDING_DIFFERS'}.intersection(hidden['reason_codes'])
    result = compare_pair(a, {**b, 'date':None, 'facility':'Different facility'}, current_count=2)
    assert {'INCOMPLETE_DATE','SELECTED_DATE_TIE','FACILITY_DIFFERS'} <= set(result['reason_codes'])
    assert not LAB_CODES.intersection(result['reason_codes'])


def test_measurement_missing_context_and_qualifiers_remain_exactly_guarded():
    current, previous = fact(), fact('b', '2024-02-03', '4.00')
    baseline = compare_pair(current, previous)
    assert baseline['difference'] == '1.25' and baseline['reason_codes'] == []
    incomplete = {**previous, 'unit':None, 'specimen':None, 'test_method':None, 'value':'<4'}
    result = compare_pair(current, incomplete)
    assert result['difference'] is None
    assert result['reason_codes'] == ['UNIT_UNKNOWN','SPECIMEN_UNKNOWN','TEST_METHOD_UNKNOWN','QUALIFIED_OR_TEXT_VALUE']
    assert all('comparability is unknown' in note for note in result['notes'][:3])


def test_reviewed_narrative_report_export_has_literal_words_and_source_links_without_empty_lab_warnings(query_service):
    client, store, _ = query_service
    a, _ = import_rows(client, [row('Authored follow-up checkup', '2025-02-03', 'Annual checkup', '', 'encounter')], 'current.csv')
    b, _ = import_rows(client, [row('Authored routine checkup', '2024-02-03', 'Annual checkup', '', 'encounter')], 'earlier.csv')
    before = store.history()
    body, brief = prepared(client, a['source_id'], b['source_id'])
    comparison = brief['comparison']['rows'][0]
    assert comparison['reason_codes'] == ['NOT_MEASUREMENT','RECORDED_WORDING_DIFFERS']
    response = client.post('/api/briefs/report-export', json=export_body(body, brief, format='html'))
    assert response.status_code == 200, response.text
    html = response.text
    for text in ('Authored follow-up checkup','Authored routine checkup','The recorded wording differs.'):
        assert text in html
    for phrase in ('Unit not recorded for both', 'Specimen not recorded for both',
                   'Test method not recorded for both', 'not an unqualified number'):
        assert phrase not in html
    for entry in brief['entries']:
        assert f'href="#{entry["citation"]}"' in html and f'id="{entry["citation"]}"' in html
    assert store.history() == before

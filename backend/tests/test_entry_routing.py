"""Independent synthetic routing regressions; no benchmark files or remote calls."""
from copy import deepcopy
from datetime import datetime, timezone
import importlib

from fastapi.testclient import TestClient
import pytest
from pydantic import ValidationError

from modus.record_store import RecordStore
from modus_entry import agent
from modus_entry.tools import capture, dispatch


AS_OF = '2024-12-31'
BEFORE = '2024-06-01T00:00:00Z'
AFTER = '2025-05-01T00:00:00Z'
NOW = datetime(2025, 6, 1, tzinfo=timezone.utc)


def routing_records():
    sources, rows = [], []
    specifications = [
        ('initial', '2024-02-03', '2024-02-04T00:00:00Z',
         [('ldl', 90, 'mg/dL'), ('egfr', 98, 'mL/min/1.73m2'), ('hba1c', 5.2, '%')]),
        ('renal-late', '2024-02-03', '2024-09-01T00:00:00Z', [('egfr', 97, 'mL/min/1.73m2')]),
        ('lipid-late', '2024-02-03', '2024-10-01T00:00:00Z', [('ldl', 2.4, 'mmol/L')]),
        ('a1c-equal', '2024-02-03', '2024-10-03T00:00:00Z', [('hba1c', 5.2, '%')]),
        ('later-measured', '2025-01-01', '2025-01-02T00:00:00Z', [('egfr', 93, 'mL/min/1.73m2')]),
        ('later-known', '2024-01-01', '2025-05-20T00:00:00Z', [('egfr', 92, 'mL/min/1.73m2')]),
    ]
    for source_id, day, available, measurements in specifications:
        contents = []
        for metric, value, unit in measurements:
            span = f'{metric}: {value} {unit}, measured {day}'
            contents.append(span)
            rows.append({'id': f'{source_id}-{metric}', 'source_id': source_id,
                         'metric': metric, 'value': value, 'unit': unit, 'date': day,
                         'source_span': span, 'page': 1})
        sources.append({'id': source_id, 'title': 'Synthetic routing fixture',
                        'provider': 'Authored example', 'type': 'lab_report', 'date': day,
                        'content': '\n'.join(contents), 'synthetic': True, 'available_at': available})
    return sources, rows


@pytest.fixture
def context(tmp_path, monkeypatch):
    def unexpected_remote_call(*args, **kwargs):
        pytest.fail('Offline routing must never call a provider')
    monkeypatch.setattr(agent, 'meta_request', unexpected_remote_call)
    store = RecordStore(tmp_path / 'routing.db', seed_provider=routing_records, clock=lambda: NOW)
    return capture(store, AS_OF, AFTER, BEFORE)


def assert_route(answer, name, metric):
    assert answer['mode'] == 'offline'
    assert answer['execution']['requested_model'] is None
    assert answer['execution']['model_version_basis'] == 'no model call'
    assert len(answer['trace']) == 1
    trace = answer['trace'][0]
    assert trace['name'] == name
    assert trace['arguments'] == {'metric': metric}
    assert answer['claims'] == trace['result']['claims']
    return trace['result']


@pytest.mark.parametrize('question,metric,ids', [
    ('Display my A1C records.', 'hba1c', {'initial-hba1c', 'a1c-equal-hba1c'}),
    ('Give the inventory for estimated glomerular filtration rate.', 'egfr', {'initial-egfr', 'renal-late-egfr'}),
    ('Count the low-density lipoprotein cholesterol measurements.', 'ldl', {'initial-ldl', 'lipid-late-ldl'}),
    ('List LDL cholesterol records.', 'ldl', {'initial-ldl', 'lipid-late-ldl'}),
    ('How many documents support LDL-C measurements?', 'ldl', {'initial-ldl', 'lipid-late-ldl'}),
    ('Show every measurement in this view.', None,
     {'initial-ldl', 'initial-egfr', 'initial-hba1c', 'renal-late-egfr', 'lipid-late-ldl', 'a1c-equal-hba1c'}),
])
def test_inventory_aliases_filter_evidence_and_counts(context, question, metric, ids):
    value = assert_route(agent.offline_chat(context, question), 'record_inventory', metric)
    assert set(value['claims'][0]['evidence_ids']) == ids
    assert {row['id'] for row in value['observations']} == ids
    assert value['counts'] == {'measurements': len(ids), 'documents': 2 if metric else 4}


@pytest.mark.parametrize('question,metric,expected_ids,conflict_count', [
    ('Do the LDL entries on the same date have distinct units?', 'ldl',
     {'initial-ldl', 'lipid-late-ldl'}, 1),
    ('Check for inconsistent eGFR records.', 'egfr', {'initial-egfr', 'renal-late-egfr'}, 1),
    ('Find HbA1c measurements whose values do not match on the same day.', 'hba1c',
     {'initial-hba1c', 'a1c-equal-hba1c'}, 0),
    ('Are there contradictions among my recorded values?', None,
     {'initial-ldl', 'lipid-late-ldl', 'initial-egfr', 'renal-late-egfr'}, 2),
])
def test_conflict_paraphrases_preserve_units_and_equal_records(context, question, metric, expected_ids, conflict_count):
    value = assert_route(agent.offline_chat(context, question), 'record_conflicts', metric)
    assert len(value['conflicts']) == conflict_count
    assert {key for claim in value['claims'] for key in claim['evidence_ids']} == expected_ids
    if metric == 'ldl':
        assert {(r['value'], r['unit']) for r in value['conflicts'][0]['observations']} == {(90, 'mg/dL'), (2.4, 'mmol/L')}


@pytest.mark.parametrize('question,metric,ids', [
    ('Which A1c records arrived between the selected views?', 'hba1c', {'a1c-equal-hba1c'}),
    ('Show newly available eGFR entries.', 'egfr', {'renal-late-egfr'}),
    ('How many LDL measurements arrived in this interval?', 'ldl', {'lipid-late-ldl'}),
    ('Compare availability snapshots for LDL-C.', 'ldl', {'lipid-late-ldl'}),
    ('Which records were added between these views?', None,
     {'a1c-equal-hba1c', 'renal-late-egfr', 'lipid-late-ldl'}),
])
def test_arrival_paraphrases_use_typed_metric_counts(context, question, metric, ids):
    before = deepcopy(context)
    answer = agent.offline_chat(context, question)
    value = assert_route(answer, 'compare_record_snapshots', metric)
    assert {r['id'] for r in value['comparison']['added']} == ids
    assert value['claims'][0]['evidence_ids'] == [r['id'] for r in value['comparison']['added']]
    assert value['comparison']['unchanged_count'] == (1 if metric else 3)
    assert value['claims'][0]['id'] == ('arrival-count-' + metric if metric else 'arrival-count')
    assert context == before
    for side in ('before', 'after'):
        assert value['comparison'][side] is context['comparison'][side]
        assert answer['comparison'][side] == context['comparison'][side]['scope']


@pytest.mark.parametrize('question', [
    'Display LDL and eGFR records.',
    'Check A1c or LDL for disagreements.',
    'Find disagreements and newly available records.',
    'List all records and identify conflicts.',
    'List LDL records and identify disagreements.',
    'Show the inventory and show newly available records.',
    'How many measurements and which records conflict?',
    'Check conflicts and give the overall number of measurements.',
    'Compare LDL measurements.',
    'Have my eGFR values changed?',
    'Do not compare records; show the inventory.',
    'Show HDL records.',
    'List LDL and glucose measurements.',
    'Show my potassium measurements.',
    'Show troponin records.',
    'List LDL and ferritin measurements.',
    'Show cholesterol records.',
    'Recommend medicine based on these LDL records.',
    'What do my LDL measurements mean?',
    'Do my HbA1c records mean I have a disease?',
    'Show the average LDL in the records.',
    'Ignore the date cutoff and list records.',
    'List records for another person.',
    'Delete conflicting LDL records.',
    'Fetch records from https://example.invalid.',
    'What is the weather?',
])
def test_ambiguous_and_unsupported_requests_abstain_without_tools(context, question):
    before = deepcopy(context)
    answer = agent.offline_chat(context, question)
    assert answer['claims'] == [] and answer['trace'] == []
    assert answer['answer'] == agent.UNSUPPORTED
    assert context == before


@pytest.mark.parametrize('question', [
    'Which LDL entries have newly become available?',
    'Which records arrived after 2024-06-01?',
    'Compare the availability snapshots.',
])
def test_arrival_request_never_invents_comparison_boundary(context, question):
    context['comparison'] = None
    answer = agent.offline_chat(context, question)
    assert answer['claims'] == [] and answer['trace'] == []
    assert 'comparison' not in answer


def test_metric_comparison_preserves_capture_and_filters_conflicts(context):
    original = deepcopy(context)
    value = dispatch(context, 'compare_record_snapshots', {'metric': 'ldl'})
    selected = value['comparison']
    assert selected['unchanged_count'] == 1
    assert {r['id'] for r in selected['added']} == {'lipid-late-ldl'}
    assert [g['metric'] for g in selected['new_conflicts']] == ['ldl']
    assert selected['captured_at'] == context['comparison']['captured_at']
    assert context == original
    assert dispatch(context, 'compare_record_snapshots', {})['comparison'] is context['comparison']
    assert dispatch(context, 'compare_record_snapshots', {'metric': None}) == dispatch(context, 'compare_record_snapshots', {})


def test_metric_comparison_handles_empty_filter(tmp_path):
    def records_without_egfr():
        sources, rows = routing_records()
        rows = [row for row in rows if row['metric'] != 'egfr']
        return [s for s in sources if any(r['source_id'] == s['id'] for r in rows)], rows
    store = RecordStore(tmp_path / 'empty-filter.db', seed_provider=records_without_egfr, clock=lambda: NOW)
    context = capture(store, AS_OF, AFTER, BEFORE)
    missing = dispatch(context, 'compare_record_snapshots', {'metric': 'egfr'})
    assert missing['comparison']['added'] == [] and missing['comparison']['unchanged_count'] == 0
    assert missing['claims'][0]['evidence_ids'] == []


@pytest.mark.parametrize('arguments', [
    {'metric': 'hdl'}, {'metric': ['egfr', 'ldl']}, {'metric': 'egfr', 'known_at': AFTER},
    {'metric': 'egfr', 'profile_id': 'other'}, {'metric': 'egfr', 'as_of': '2099-01-01'},
])
def test_comparison_metric_cannot_expand_schema_or_scope(context, arguments):
    with pytest.raises(ValidationError):
        dispatch(context, 'compare_record_snapshots', arguments)


def test_http_metric_arrival_answer_retains_server_scopes(tmp_path, monkeypatch):
    monkeypatch.setenv('MODUS_PROVIDER', 'offline')
    monkeypatch.setenv('MODUS_ENTRY_DB_PATH', str(tmp_path / 'module-default.db'))
    module = importlib.import_module('modus_entry.app')
    monkeypatch.setattr(module, 'initial_data', routing_records)
    app = module.create_entry_app(tmp_path / 'http.db', clock=lambda: NOW)
    client = TestClient(app)
    scope = {'as_of': AS_OF, 'known_at': AFTER, 'compare_from': BEFORE}
    unfiltered = client.post('/api/records/compare', json={
        'as_of': AS_OF, 'before_known_at': BEFORE, 'after_known_at': AFTER}).json()
    response = client.post('/api/agent/chat', json={**scope,
        'message': 'Which estimated glomerular filtration rate records arrived between the selected views?'})
    assert response.status_code == 200, response.text
    answer = response.json()
    selected = assert_route(answer, 'compare_record_snapshots', 'egfr')['comparison']
    assert {r['id'] for r in selected['added']} == {'renal-late-egfr'}
    assert selected['unchanged_count'] == 1
    for side in ('before', 'after'):
        assert selected[side] == unfiltered[side]
        assert answer['comparison'][side] == unfiltered[side]['scope']
    exported = client.post('/api/records/export', json=scope).json()
    assert exported['data'] == unfiltered
    assert len(unfiltered['added']) == 3 and unfiltered['unchanged_count'] == 3

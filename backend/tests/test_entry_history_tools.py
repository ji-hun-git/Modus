"""Authored tool contracts; no external data, provider calls or evaluation sets."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json

from pydantic import ValidationError
import pytest

from modus.record_history import commit_history, update_profile
from modus.record_history_models import ReviewedFact
from modus.record_history_view import history_view
from modus.record_store import RecordStore
from modus_entry.history_tools import ARGUMENTS, capture_history, dispatch


NOW = datetime(2026, 10, 28, 8, tzinfo=timezone.utc)


@pytest.fixture
def memory(tmp_path):
    clock = [NOW]
    store = RecordStore(tmp_path / 'authored.db', seed_provider=lambda: ([], []), clock=lambda: clock[0])
    return store, clock


def field(kind='measurement', label='Ferritin', value='22.40', unit='ng/mL', day='2021-04-05', **updates):
    return {'kind': kind, 'label': label, 'value': value, 'unit': unit, 'occurred_on': day,
            'facility': 'Authored clinic', 'source_quote': f'{label} {value} {unit or ""} {day or ""}',
            'page': 1, 'bbox': None, 'model_confidence': None, 'extractor': 'authored-test', **updates}


def commit(store, rows, title='authored-record.json', accepted=None):
    rows = [dict(row, id=f'field-{index}') for index, row in enumerate(rows)]
    raw = json.dumps({'title': title, 'facts': rows}, ensure_ascii=False).encode()
    digest = sha256(raw).hexdigest()
    sid = 'import-' + digest[:20]
    draft = {'id': sid, 'source': {'id': sid, 'title': title, 'type': 'Document',
        'provider': 'Authored test', 'date': '', 'content': 'Never send this raw content',
        'synthetic': True, 'sha256': digest}, 'facts': rows, 'observations': [], 'extraction_mode': 'manual'}
    store.add_draft(draft, raw, title, 'application/json')
    reviewed = [{key: row.get(key) for key in ReviewedFact.model_fields} for row in rows]
    if accepted is not None:
        reviewed = [row for index, row in enumerate(reviewed) if index in accepted]
    return commit_history(store, sid, reviewed)


def diverse_rows():
    return [field(), field('encounter', 'Visit', 'Follow-up printed', None),
        field('recorded_diagnosis', 'Provider wording', 'As printed in source', None),
        field('procedure', 'Procedure note', 'Procedure as printed', None),
        field('prescription', 'Example medicine', 'Recorded instruction once daily', None),
        field('vaccination', 'MMR', 'Recorded dose', None, '2012'),
        field('imaging_text', 'Head scan', 'Report wording only', None, None),
        field('recorded_text', 'Family note', 'Source narrative', None)]


def test_all_kinds_inventory_exact_values_and_labels(memory):
    store, _ = memory
    commit(store, diverse_rows())
    context = capture_history(store)
    result = dispatch(context, 'history_inventory', {'limit': 8})
    assert result['counts']['facts'] == 8
    assert len(result['counts']['by_kind']) == 8
    assert result['next_offset'] is None and not result['truncated']
    measurement = dispatch(context, 'history_inventory', {'label': 'fErRiTiN'})
    assert measurement['facts'][0]['value'] == '22.40'
    assert '22.40' in measurement['claims'][1]['text'] and 'ng/mL' in measurement['claims'][1]['text']
    assert dispatch(context, 'history_inventory', {'label': 'iron stores'})['counts']['facts'] == 0
    prescription = dispatch(context, 'history_inventory', {'kind': 'prescription'})
    assert 'does not establish current medication use' in prescription['claims'][1]['text']
    diagnosis = dispatch(context, 'history_inventory', {'kind': 'recorded_diagnosis'})
    assert 'not a diagnosis made by Modus' in diagnosis['claims'][1]['text']
    vaccination = dispatch(context, 'history_inventory', {'kind': 'vaccination'})
    assert vaccination['facts'][0]['occurred_on'] == '2012'
    assert '2012-01-01' not in json.dumps(vaccination)
    imaging = dispatch(context, 'history_inventory', {'kind': 'imaging_text'})
    assert '; date not recorded.' in imaging['claims'][1]['text']
    assert 'recorded date date' not in imaging['claims'][1]['text']


@pytest.mark.parametrize('query,kind,label', [
    ('Find records mentioning "Ferritin"', None, 'Ferritin'),
    ('Find my prescriptions for "Example medicine"', 'prescription', 'Example medicine'),
    ('Find my imaging reports containing "Head scan"', 'imaging_text', 'Head scan'),
    ('Find vaccination records for MMR', 'vaccination', 'MMR'),
    ('MMR 2012', None, 'MMR'),
    ('페리틴 기록 찾아줘', None, '페리틴'),
])
def test_named_search_preserves_literal_filter(memory, query, kind, label):
    store, _ = memory
    commit(store, diverse_rows() + [field(label='페리틴'), field('prescription', 'Different medicine', 'Different text', None)])
    result = dispatch(capture_history(store), 'search_history_evidence', {'query': query, 'kind': kind})
    assert [row['label'] for row in result['facts']] == [label]
    assert result['match_count'] == 1


def test_search_no_match_source_phrase_and_unknown_qualifier_never_broaden(memory):
    store, _ = memory
    commit(store, [field()], title='West Clinic.json')
    commit(store, [field(value='31.00')], title='East Clinic.json')
    context = capture_history(store)
    one = dispatch(context, 'search_history_evidence', {'query': 'Ferritin source:"West Clinic"'})
    assert one['match_count'] == 1 and one['facts'][0]['value'] == '22.40'
    for query in ('Ferritin source:"Unseen Clinic"', 'Ferritin imaginaryqualifier', 'ferritin 2018', 'unknownmarker', '"unclosed'):
        result = dispatch(context, 'search_history_evidence', {'query': query})
        assert result['facts'] == [] and result['match_count'] == 0
        assert any('No visible recorded fact matched' in claim['text'] for claim in result['claims'])
        assert result['claims'][0]['evidence_ids'] == []


def test_private_profile_proposals_and_review_identity_never_enter_context(memory):
    store, _ = memory
    update_profile(store, '1997-02-03')
    commit(store, [field()])
    context = capture_history(store)
    encoded = json.dumps(context)
    for forbidden in ('date_of_birth', '1997-02-03', 'profile', 'age_years', 'source_proposal', 'reviewer', 'local-owner', 'Never send this raw content'):
        assert forbidden not in encoded
    assert history_view(store)['facts'][0]['age_years'] == 24


def test_mixed_period_original_and_excluded_future_rows_remain_withheld(memory):
    store, _ = memory
    commit(store, [field('prescription', 'Old medicine', 'PRIVATE_VALUE_SENTINEL', None, '2019-01-02',
                         source_quote='PRIVATE_QUOTE_SENTINEL'),
                   field('imaging_text', 'Future scan', 'FUTURE_VALUE_SENTINEL', None, '2025-03-04')], accepted=[0])
    context = capture_history(store, '2020-01-01')
    encoded = json.dumps(context)
    assert 'PRIVATE_VALUE_SENTINEL' not in encoded and 'PRIVATE_QUOTE_SENTINEL' not in encoded
    assert 'FUTURE_VALUE_SENTINEL' not in encoded
    assert context['view']['facts'][0]['original_available'] is False
    assert dispatch(context, 'history_inventory', {})['counts']['facts'] == 0
    result = dispatch(context, 'search_history_evidence', {'query': 'PRIVATE_VALUE_SENTINEL'})
    assert result['match_count'] == 0


def test_frozen_pair_captures_one_clock_and_late_arrivals_only(memory):
    store, clock = memory
    commit(store, [field()], title='first.json')
    clock[0] += timedelta(hours=2)
    commit(store, [field('prescription', 'Example medicine', 'Historical directions', None, '2009-02-03')], title='late.json')
    calls = []
    def capture_clock():
        calls.append(True)
        return clock[0]
    store.clock = capture_clock
    context = capture_history(store, compare_from=NOW)
    assert len(calls) == 1
    pair = context['comparison']
    assert pair['captured_at'] == pair['before']['scope']['captured_at'] == pair['after']['scope']['captured_at']
    assert len(pair['added']) == 1 and pair['unchanged_count'] == 1
    frozen = deepcopy(context)
    clock[0] += timedelta(hours=2)
    commit(store, [field(value='90.0')], title='after-capture.json')
    result = dispatch(context, 'compare_history_snapshots', {'kind': 'prescription'})
    assert result['added_count'] == 1 and result['unchanged_count'] == 0
    assert result['facts'][0]['occurred_on'] == '2009-02-03'
    assert context == frozen
    assert dispatch(context, 'history_inventory', {})['counts']['facts'] == 2


def test_temporal_validation_and_future_clamp(memory):
    store, _ = memory
    future = capture_history(store, known_at='2099-01-01T00:00:00Z')
    assert future['view']['scope']['known_at'] == future['view']['scope']['captured_at']
    with pytest.raises(ValueError):
        capture_history(store, known_at='2020-01-01T00:00:00Z', compare_from='2021-01-01T00:00:00Z')
    with pytest.raises(ValueError):
        capture_history(store, as_of='2020')
    with pytest.raises(ValueError):
        dispatch(future, 'compare_history_snapshots', {})


def test_discrepancies_preserve_both_records_without_clinical_claims(memory):
    store, _ = memory
    commit(store, [field(), field(value='35.10')])
    context = capture_history(store)
    result = dispatch(context, 'history_conflicts', {'label': 'ferritin'})
    assert result['group_count'] == 1 and len(result['facts']) == 2
    assert {row['value'] for row in result['facts']} == {'22.40', '35.10'}
    assert 'specimen equivalence is unknown' in result['claims'][0]['text']
    unsupported_kind = dispatch(context, 'history_conflicts', {'kind': 'prescription'})
    assert unsupported_kind['group_count'] == 0
    assert 'does not establish consistency' in unsupported_kind['claims'][0]['text']


def test_large_inventory_and_discrepancies_have_bounded_inspectable_pages(memory):
    store, _ = memory
    commit(store, [field(label=f'Test {index}', value=str(number)) for index in range(9) for number in (1, 2)])
    context = capture_history(store)
    first = dispatch(context, 'history_inventory', {'limit': 8})
    assert first['counts']['facts'] == 18 and first['next_offset'] == 8 and first['truncated']
    second = dispatch(context, 'history_inventory', {'limit': 8, 'offset': first['next_offset']})
    assert not {row['id'] for row in first['facts']}.intersection(row['id'] for row in second['facts'])
    conflicts = dispatch(context, 'history_conflicts', {})
    assert conflicts['group_count'] == 9 and conflicts['truncated']
    assert len(conflicts['facts']) <= 8
    assert all(row['evidence_ids'] for row in conflicts['claims'])
    assert conflicts['warnings']
    assert 'Only part of the discrepancy evidence' in conflicts['claims'][0]['text']
    assert conflicts['required_claim_ids'] == [conflicts['claims'][0]['id']]


@pytest.mark.parametrize('day', ['2021-04-05', None])
def test_oversized_record_never_cuts_value_or_exceeds_tool_budget(memory, day):
    store, _ = memory
    huge = '한' * 15000
    commit(store, [field('recorded_text', 'Long authored note', huge, None, day, source_quote=huge)])
    result = dispatch(capture_history(store), 'history_inventory', {})
    assert result['facts'][0]['content_omitted'] is True
    assert result['facts'][0]['value'] is None and result['facts'][0]['source_quote'] is None
    assert 'exceed this tool response budget' in result['claims'][1]['text']
    assert 'recorded date date' not in result['claims'][1]['text']
    if day is None:
        assert '; date not recorded.' in result['claims'][1]['text']
    assert result['truncated'] and 'long recorded values' in result['claims'][0]['text']
    assert result['required_claim_ids'] == [result['claims'][0]['id']]
    assert len(json.dumps(result).encode()) < 100000


def test_search_warning_claims_make_truncation_conflicts_and_bad_phrases_visible(memory):
    store, _ = memory
    commit(store, [field(value=str(index)) for index in range(12)])
    context = capture_history(store)
    result = dispatch(context, 'search_history_evidence', {'query': 'Ferritin'})
    text = result['claims'][0]['text']
    assert result['match_count'] == 12 and len(result['facts']) == 5 and result['truncated']
    assert 'Showing 5 of 12' in text and 'recorded discrepancies' in text
    assert result['required_claim_ids'] == [result['claims'][0]['id']]
    malformed = dispatch(context, 'search_history_evidence', {'query': '"Ferritin'})
    assert any('Unclosed quoted phrase' in claim['text'] for claim in malformed['claims'])
    assert malformed['required_claim_ids'] == [malformed['claims'][0]['id']]


@pytest.mark.parametrize('name,args', [
    ('history_inventory', {'limit': True}), ('history_inventory', {'limit': 9}),
    ('history_inventory', {'offset': -1}), ('history_inventory', {'as_of': '2019-01-01'}),
    ('history_inventory', {'kind': 'risk'}), ('history_inventory', {'label': ' '}),
    ('search_history_evidence', {'query': ' ' }), ('search_history_evidence', {'query': 'x', 'url': 'https://example.com'}),
    ('history_conflicts', {'subject_id': 'someone'}), ('compare_history_snapshots', {'known_at': '2020'}),
])
def test_tool_arguments_cannot_widen_scope_or_authority(name, args):
    with pytest.raises(ValidationError):
        ARGUMENTS[name].model_validate(args)

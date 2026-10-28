"""Independent adversarial review of the whole-history boundaries; authored data only."""
from datetime import datetime, timedelta, timezone
import json

import pytest

from modus.history_ingest import make_history_draft
from modus.record_history import commit_history, get_profile, history_view, update_profile
from modus.record_history_models import ReviewedFact
from modus.record_store import RecordStore
from modus_entry.tools import capture


@pytest.mark.parametrize('content', [
    'label,value,value,unit,date\nLDL,100,999,mg/dL,2020-01-01\n',
    'label,metric,value,unit,date\nLDL,HbA1c,5.6,%,2020-01-01\n',
    'label,value,unit,date,occurred_on\nLDL,100,mg/dL,2020-01-01,2025-01-01\n',
])
def test_competing_csv_columns_cannot_silently_choose_one_value(content):
    with pytest.raises(ValueError):
        make_history_draft('ambiguous.csv', content.encode())


def test_reference_row_identical_to_result_remains_in_document_text():
    row = 'HbA1c 5.6 % 2024-02-03'
    raw = f'Results\n{row}\nReference example\n{row}\n'.encode()
    draft = make_history_draft('repeated.txt', raw)
    facts = draft['facts']
    assert len([fact for fact in facts if fact['kind'] == 'measurement']) == 1
    archive = '\n'.join(fact['value'] for fact in facts if fact['kind'] == 'recorded_text')
    assert f'Reference example\n{row}' in archive


@pytest.fixture
def memory(tmp_path):
    now = [datetime(2026, 10, 28, 12, tzinfo=timezone.utc)]
    store = RecordStore(tmp_path / 'audit.db', seed_provider=lambda: ([], []), clock=lambda: now[0])
    return store, now


def save_csv(store, content):
    raw = content.encode()
    draft = make_history_draft('authored.csv', raw)
    store.add_draft(draft, raw, 'authored.csv', 'text/csv')
    rows = [{key: fact[key] for key in ReviewedFact.model_fields} for fact in draft['facts']]
    return draft, rows


def test_exact_decimal_does_not_round_in_legacy_projection(memory):
    store, _ = memory
    value = '80.123456789123456789'
    draft, rows = save_csv(store, f'label,value,unit,date\neGFR,{value},mL/min/1.73m2,2021-04-08\n')
    receipt = commit_history(store, draft['id'], rows)
    assert receipt['observation_ids'] == []
    assert history_view(store)['facts'][0]['value'] == value
    assert store.observations() == []


def test_scientific_notation_compares_exactly_without_changing_original(memory):
    store, _ = memory
    draft, rows = save_csv(store, 'label,value,unit,date\nExample test,1e2,U/L,2021-04-08\nExample test,200,U/L,2021-04-08\n')
    commit_history(store, draft['id'], rows)
    view = history_view(store)
    assert len(view['conflicts']) == 1
    assert {f['value'] for f in view['facts']} == {'1e2', '200'}


def test_exact_retry_can_reorder_rows_but_cannot_change_review(memory):
    store, now = memory
    draft, rows = save_csv(store, 'label,value,unit,date\nHbA1c,5.6,%,2024-01-01\nHeight,1.2,m,2010-01-01\n')
    first = commit_history(store, draft['id'], rows)
    now[0] += timedelta(hours=1)
    retry = commit_history(store, draft['id'], list(reversed(rows)))
    assert retry['duplicate'] is True and retry['inserted'] == 0
    assert retry['fact_ids'] == first['fact_ids'] and retry['available_at'] == first['available_at']
    changed = [{**rows[0], 'value': '9.9'}, rows[1]]
    with pytest.raises(ValueError, match='different reviewed facts'):
        commit_history(store, draft['id'], changed)
    assert history_view(store)['counts']['facts'] == 2


def test_profile_is_local_versioned_metadata_outside_agent_context(memory):
    store, now = memory
    draft, rows = save_csv(store, 'label,value,unit,date\nHeight,120,cm,2010-01-01\n')
    commit_history(store, draft['id'], rows)
    earlier = now[0].isoformat()
    now[0] += timedelta(seconds=1)
    update_profile(store, '2001-02-03')
    assert get_profile(store, earlier)['date_of_birth'] is None
    assert history_view(store, known_at=earlier)['facts'][0]['age_years'] is None
    assert history_view(store)['facts'][0]['age_years'] == 8
    assert '2001-02-03' not in json.dumps(capture(store, '2026-10-28'))
    now[0] += timedelta(seconds=1)
    update_profile(store, None)
    assert get_profile(store)['date_of_birth'] is None


def test_bridge_after_date_and_facility_edit_remains_readable(memory):
    store, _ = memory
    draft, rows = save_csv(store, 'label,value,unit,date\nHbA1c,5.6,%,2024-01-01\n')
    rows[0].update(occurred_on='2023-01-01', facility='Corrected facility')
    commit_history(store, draft['id'], rows)
    view = capture(store, '2026-10-28')['view']
    assert view['observations'][0]['date'] == '2023-01-01'
    assert view['observations'][0]['reviewed_fields'] == ['date']


def test_unknown_date_text_does_not_escape_historical_filter_via_value(memory):
    store, _ = memory
    draft, rows = save_csv(store, 'kind,label,value,date\nmeasurement,HbA1c,5.6,2019-01-01\nrecorded_text,Note,FUTURE_PRIVATE_EXCERPT,2027\n')
    commit_history(store, draft['id'], rows)
    view = history_view(store, as_of='2020-12-31')
    assert 'FUTURE_PRIVATE_EXCERPT' not in json.dumps(view)
    assert view['undated_facts'][0]['value_withheld'] is True
    assert view['undated_facts'][0]['normalization'] is None
    assert all(source['original_available'] is False for source in view['sources'])


def test_large_reviewed_measurement_text_does_not_make_saved_history_unreadable(memory):
    store, _ = memory
    draft, rows = save_csv(store, 'label,value,unit,date\nUnknown analyte,5.6,U/L,2020-01-01\n')
    rows[0]['value'] = 'Original unparsed result ' * 50
    commit_history(store, draft['id'], rows)
    fact = history_view(store)['facts'][0]
    assert fact['value'] == rows[0]['value']
    assert fact['normalization']['normalized'] is None

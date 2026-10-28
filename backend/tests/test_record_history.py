"""Owner-reviewed mixed records, immutable evidence and both temporal boundaries."""
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import json

import pytest

from modus.record_history import commit_history, get_profile, history_view, update_profile
from modus.record_history_models import ReviewedFact
from modus.record_models import Observation
from modus.record_store import RecordStore


@pytest.fixture
def memory(tmp_path):
    now = [datetime(2026, 10, 28, 9, tzinfo=timezone.utc)]
    store = RecordStore(tmp_path / 'records.db', seed_provider=lambda: ([], []), clock=lambda: now[0],
                        commit_event_factory=lambda receipt: {'kind': 'import', **receipt})
    return store, now


def fact(**updates):
    return {'id': 'field-1', 'kind': 'measurement', 'label': 'HbA1c', 'value': '5.6', 'unit': '%',
            'occurred_on': '2024-02-03', 'facility': None, 'source_quote': 'HbA1c 5.6 % 2024-02-03',
            'page': 1, 'bbox': None, 'model_confidence': None, 'extractor': 'authored-test', **updates}


def draft(store, facts=None, *, salt='one', legacy=False):
    facts = facts or [fact()]
    raw = json.dumps({'salt': salt, 'facts': facts}, ensure_ascii=False).encode()
    digest = sha256(raw).hexdigest()
    sid = 'import-' + digest[:20]
    value = {'id': sid, 'source': {'id': sid, 'title': salt + '.json', 'type': 'Recorded document',
        'provider': 'Authored test', 'date': '', 'content': 'Original content', 'synthetic': True,
        'sha256': digest}, 'facts': facts, 'observations': [], 'extraction_mode': 'manual'}
    if legacy:
        value['observations'] = [{'id': sid + '-0', 'metric': 'hba1c', 'value': 5.6, 'unit': '%',
            'date': '2024-02-03', 'source_id': sid, 'source_span': 'HbA1c 5.6 % 2024-02-03', 'page': 1}]
    return store.add_draft(value, raw, salt + '.json', 'application/json')


def reviewed(value):
    keys = ReviewedFact.model_fields.keys()
    return [{key: row.get(key) for key in keys} for row in value['facts']]


def table_count(store, table):
    with store.connect() as db:
        return db.execute('SELECT count(*) FROM ' + table).fetchone()[0]


def test_generic_commit_bridges_old_measurement_without_double_count(memory):
    store, _ = memory
    source = draft(store)
    result = commit_history(store, source['id'], reviewed(source))
    assert result['inserted'] == 1 and len(result['observation_ids']) == 1
    view = history_view(store)
    assert view['counts']['facts'] == 1 and len(store.observations()) == 1
    assert view['facts'][0]['source_quote'] == source['facts'][0]['source_quote']
    assert view['facts'][0]['available_at'] == '2026-10-28T09:00:00.000000Z'
    assert view['facts'][0]['reviewer'] == 'local-owner'
    assert len(view['facts'][0]['id']) < 160


@pytest.mark.parametrize('kind', ['encounter', 'recorded_diagnosis', 'procedure', 'prescription', 'vaccination', 'imaging_text', 'recorded_text'])
def test_broader_types_are_committed_verbatim_without_generated_meaning(memory, kind):
    store, _ = memory
    source = draft(store, [fact(kind=kind, label='As printed', value='Recorded phrase; no interpretation', unit=None)])
    receipt = commit_history(store, source['id'], reviewed(source))
    saved = history_view(store)['facts'][0]
    assert saved['kind'] == kind and saved['value'] == 'Recorded phrase; no interpretation'
    assert saved['numeric_value'] is None and saved['normalization'] is None
    assert receipt['observation_ids'] == []


def test_reviewed_edits_preserve_proposals_and_original_document(memory):
    store, _ = memory
    source = draft(store)
    rows = reviewed(source)
    rows[0].update(label='eGFR', value='83', unit='mL/min/1.73m2', occurred_on='2023-03-02', facility='A clinic')
    commit_history(store, source['id'], rows)
    saved = history_view(store)['facts'][0]
    assert saved['value'] == '83' and saved['source_proposal']['value'] == '5.6'
    assert saved['source_quote'] == 'HbA1c 5.6 % 2024-02-03'
    assert set(saved['reviewed_fields']) == {'label', 'value', 'unit', 'occurred_on', 'facility'}
    bridge = store.observations()[0]
    Observation.model_validate(bridge)
    assert set(bridge['reviewed_fields']) == {'metric', 'value', 'unit', 'date'}
    assert store.document(source['id'])['raw']


def test_late_upload_does_not_backdate_fact_availability(memory):
    store, _ = memory
    source = draft(store, [fact(occurred_on='2000-01-01')])
    commit_history(store, source['id'], reviewed(source))
    assert history_view(store, known_at='2026-10-28T08:59:59Z')['facts'] == []
    assert len(history_view(store, as_of='2000-01-01')['facts']) == 1
    assert history_view(store, as_of='1999-12-31')['facts'] == []


@pytest.mark.parametrize('raw_date,precision', [(None, 'unknown'), ('2024', 'year'), ('2024-03', 'month'),
    ('03/04/2024', 'unresolved'), ('2024-02-31', 'unresolved')])
def test_unknown_partial_or_ambiguous_dates_never_become_invented_days(memory, raw_date, precision):
    store, _ = memory
    source = draft(store, [fact(occurred_on=raw_date)])
    commit_history(store, source['id'], reviewed(source))
    all_history = history_view(store)
    assert all_history['facts'] == []
    row = all_history['undated_facts'][0]
    assert row['occurred_on'] == raw_date and row['date'] is None and row['date_precision'] == precision
    assert row['value'] == '5.6' and row['original_available']
    scoped = history_view(store, as_of='2025-01-01')['undated_facts'][0]
    assert scoped['value'] is None and scoped['value_withheld'] and not scoped['within_date_scope']
    assert scoped['source_quote'] is None and not scoped['original_available']
    assert scoped['numeric_value'] is None and scoped['normalization'] is None
    assert 'source_proposal' not in scoped


def test_unparsed_text_cannot_leak_future_events_in_scoped_view(memory):
    store, _ = memory
    fields = [fact(kind='recorded_text', label='Recorded page', value='Future visit 2030-01-01',
                   occurred_on=None, unit=None), fact(id='field-2', occurred_on='2024-01-01')]
    source = draft(store, fields)
    commit_history(store, source['id'], reviewed(source))
    view = history_view(store, as_of='2024-12-31')
    assert 'Future visit' not in json.dumps(view)
    assert view['facts'][0]['value'] == '5.6'
    assert view['undated_facts'][0]['value'] is None
    assert view['sources'][0]['original_available'] is False


def test_dated_text_of_partial_source_is_withheld_too(memory):
    store, _ = memory
    fields = [fact(kind='recorded_text', label='Recorded page', value='Future visit 2030-01-01',
                   occurred_on='2024-01-01', unit=None), fact(id='field-2', occurred_on='2030-01-01')]
    source = draft(store, fields)
    commit_history(store, source['id'], reviewed(source))
    view = history_view(store, as_of='2024-12-31')
    assert len(view['facts']) == 1 and view['facts'][0]['value'] is None
    assert 'Future visit' not in json.dumps(view)


def test_excluded_future_proposal_still_blocks_original_and_legacy_quote(memory):
    store, _ = memory
    source = draft(store, [fact(), fact(id='field-2', occurred_on='2030-01-01')])
    commit_history(store, source['id'], reviewed(source)[:1])
    view = history_view(store, as_of='2024-12-31')
    assert not view['sources'][0]['original_available']
    assert view['facts'][0]['source_quote'] is None
    legacy = store.snapshot()
    assert legacy.observations('2024-12-31')[0]['source_span_withheld'] is True
    assert legacy.sources('2024-12-31')[0]['original_available'] is False


def test_idempotency_receipt_preserves_original_clock_and_rejects_different_review(memory):
    store, now = memory
    source = draft(store)
    first = commit_history(store, source['id'], reviewed(source))
    now[0] = datetime(2026, 10, 29, tzinfo=timezone.utc)
    retry = commit_history(store, source['id'], reviewed(source))
    assert retry['duplicate'] and retry['inserted'] == 0 and retry['available_at'] == first['available_at']
    assert table_count(store, 'history_facts') == table_count(store, 'runs') == 1
    changed = reviewed(source)
    changed[0]['value'] = '6.1'
    with pytest.raises(ValueError, match='different reviewed facts'):
        commit_history(store, source['id'], changed)


@pytest.mark.parametrize('injection', [{'available_at': '2000-01-01T00:00:00Z'}, {'source_quote': 'Forged'},
    {'page': 4}, {'bbox': [0, 0, 1, 1]}, {'reviewer': 'someone'}, {'source_id': 'other'}, {'normalized_unit': 'mmol/L'}])
def test_client_cannot_supply_provenance_or_server_fields(memory, injection):
    store, _ = memory
    source = draft(store)
    rows = reviewed(source)
    rows[0].update(injection)
    with pytest.raises(ValueError):
        commit_history(store, source['id'], rows)
    assert table_count(store, 'history_facts') == table_count(store, 'sources') == table_count(store, 'runs') == 0


def test_callback_failure_rolls_back_facts_bridge_source_and_receipt(memory):
    store, _ = memory
    source = draft(store)
    store._commit_event_factory = lambda receipt: None
    with pytest.raises(TypeError):
        commit_history(store, source['id'], reviewed(source))
    for table in ('history_facts', 'observations', 'sources', 'history_commits', 'record_commits', 'runs'):
        assert table_count(store, table) == 0
    assert store.draft(source['id'])['already_committed'] is False


def test_conflicts_require_exact_label_unit_day_and_numeric_values(memory):
    store, _ = memory
    for n, row in enumerate([fact(label='Weight', value='60', unit='kg'), fact(label='Weight', value='65', unit='kg'),
        fact(label='Weight', value='60000', unit='g'), fact(label='weight', value='70', unit='kg'),
        fact(label='Weight', value='<65', unit='kg')]):
        source = draft(store, [row], salt=str(n))
        commit_history(store, source['id'], reviewed(source))
    conflicts = history_view(store)['conflicts']
    assert len(conflicts) == 1 and set(conflicts[0]['values']) == {'60', '65', '60000', '<65'}
    assert conflicts[0]['reason'] == 'different_recorded_units'
    assert conflicts[0]['comparison_basis'] == 'different_recorded_units_not_numerically_compared'
    assert conflicts[0]['resolution'] == 'unresolved'
    assert table_count(store, 'history_facts') == 5


def test_exact_unit_numeric_disagreement_does_not_compare_censored_values(memory):
    store, _ = memory
    for n, value in enumerate(['60', '60.0', '65', '<65']):
        source = draft(store, [fact(label='Weight', value=value, unit='kg')], salt=str(n))
        commit_history(store, source['id'], reviewed(source))
    differences = history_view(store)['conflicts']
    assert len(differences) == 1 and set(differences[0]['values']) == {'60', '60.0', '65'}
    assert differences[0]['reason'] == 'different_numeric_values'
    assert differences[0]['unit'] == 'kg'


def test_equivalent_decimal_spellings_are_not_a_numeric_disagreement(memory):
    store, _ = memory
    for n, value in enumerate(['60', '60.0']):
        source = draft(store, [fact(label='Weight', value=value, unit='kg')], salt=str(n))
        commit_history(store, source['id'], reviewed(source))
    assert history_view(store)['conflicts'] == []


def test_profile_revision_visibility_and_age_at_record(memory):
    store, now = memory
    update_profile(store, '2000-02-04')
    source = draft(store)
    commit_history(store, source['id'], reviewed(source))
    assert history_view(store)['facts'][0]['age_years'] == 23
    old = '2026-10-28T09:00:00Z'
    now[0] = datetime(2026, 10, 29, tzinfo=timezone.utc)
    update_profile(store, '1999-02-04')
    assert history_view(store)['facts'][0]['age_years'] == 24
    assert history_view(store, known_at=old)['facts'][0]['age_years'] == 23
    assert get_profile(store, known_at='2026-10-27T00:00:00Z')['date_of_birth'] is None
    update_profile(store, None)
    assert get_profile(store)['date_of_birth'] is None


@pytest.mark.parametrize('bad', ['2027-01-01', '2000', '2024-02-31', 20000101])
def test_profile_rejects_future_partial_or_malformed_birth_dates(memory, bad):
    store, _ = memory
    with pytest.raises(ValueError):
        update_profile(store, bad)


def test_reset_clears_generic_tables_before_shared_sources(memory):
    store, _ = memory
    source = draft(store)
    commit_history(store, source['id'], reviewed(source))
    update_profile(store, '2000-01-01')
    store.reset()
    assert history_view(store)['facts'] == [] and get_profile(store)['date_of_birth'] is None
    for table in ('history_facts', 'history_commits', 'history_profiles', 'record_commits'):
        assert table_count(store, table) == 0


def test_legacy_commit_cannot_expose_unaccepted_later_generic_fact(memory):
    store, _ = memory
    source = draft(store, [fact(), fact(id='field-2', kind='recorded_text', value='future event', occurred_on='2030-01-01')], legacy=True)
    row = source['observations'][0]
    selected = [{key: row[key] for key in ('id', 'metric', 'value', 'unit', 'date')}]
    store.commit_draft(source['id'], selected)
    assert store.snapshot().sources('2024-12-31')[0]['original_available'] is False
    assert store.snapshot().observations('2024-12-31')[0]['source_span_withheld'] is True
    with pytest.raises(ValueError, match='already committed'):
        commit_history(store, source['id'], reviewed(source))
    assert table_count(store, 'history_facts') == 0


def test_legacy_retry_after_generic_commit_does_not_duplicate_or_overwrite(memory):
    store, _ = memory
    source = draft(store, legacy=True)
    original = commit_history(store, source['id'], reviewed(source))
    row = source['observations'][0]
    selected = [{key: row[key] for key in ('id', 'metric', 'value', 'unit', 'date')}]
    retried = store.commit_draft(source['id'], selected)
    assert retried['duplicate'] and retried['fact_ids'] == original['fact_ids']
    assert table_count(store, 'observations') == table_count(store, 'history_facts') == table_count(store, 'runs') == 1


def test_source_evidence_must_be_valid_even_when_reviewed_values_are_valid(memory):
    store, _ = memory
    source = draft(store, [fact(bbox=[1, 0, 0, 1])])
    with pytest.raises(ValueError):
        commit_history(store, source['id'], reviewed(source))
    assert table_count(store, 'sources') == table_count(store, 'history_facts') == 0


@pytest.mark.parametrize('cutoff', ['2024', '2024-02-31', '2024-01-01T00:00:00Z'])
def test_history_rejects_ambiguous_date_cutoff(memory, cutoff):
    with pytest.raises(ValueError):
        history_view(memory[0], as_of=cutoff)


def test_scope_identity_binds_projected_content_not_just_fact_ids(memory):
    store, _ = memory
    source = draft(store)
    commit_history(store, source['id'], reviewed(source))
    before = history_view(store)
    update_profile(store, '2000-01-01')
    after = history_view(store)
    assert before['scope']['captured_at'] == after['scope']['captured_at']
    assert before['facts'][0]['id'] == after['facts'][0]['id']
    assert before['scope']['scope_id'] != after['scope']['scope_id']

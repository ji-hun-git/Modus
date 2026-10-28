"""Generic replay over newly authored records only; no models or evaluation sets."""
import csv
from datetime import datetime, timedelta, timezone
import importlib
import io
import json

from fastapi.testclient import TestClient
import pytest


NOW = datetime(2026, 10, 29, 8, 0, 0, 123456, tzinfo=timezone.utc)


@pytest.fixture
def api(tmp_path, monkeypatch):
    monkeypatch.setenv('MODUS_ENTRY_DB_PATH', str(tmp_path / 'module.db'))
    module = importlib.import_module('modus_entry.app')
    monkeypatch.setattr(module, 'initial_data', lambda: ([], []))
    async def no_model(*args, **kwargs):
        pytest.fail('Replay must not call a model')
    monkeypatch.setattr(module.agent, 'meta_request', no_model)
    monkeypatch.setattr(module, 'extract_record_document', no_model)
    clock = [NOW]
    app = module.create_entry_app(tmp_path / 'replay.db', clock=lambda: clock[0])
    with TestClient(app) as client:
        yield client, app.state.store, clock


def save(client, rows, *, corrected=None, filename='authored.csv'):
    stream = io.StringIO(newline='')
    writer = csv.writer(stream)
    writer.writerow(['kind', 'label', 'value', 'unit', 'date', 'facility'])
    writer.writerows(rows)
    raw = stream.getvalue().encode('utf-8')
    response = client.post('/api/imports/preview', data={'synthetic_confirmed': 'true'},
                           files={'file': (filename, raw, 'text/csv')})
    assert response.status_code == 200, response.text
    draft = response.json()
    keys = ('id', 'kind', 'label', 'value', 'unit', 'occurred_on', 'facility')
    reviewed = [{key: row[key] for key in keys} for row in draft['facts']]
    if corrected is not None:
        reviewed[0]['value'] = corrected
    receipt = client.post('/api/history/commit', json={'draft_id': draft['id'],
        'synthetic_confirmed': True, 'reviewed_facts': reviewed})
    assert receipt.status_code == 200, receipt.text
    return receipt.json(), draft, raw


def compare(client, before, **kwargs):
    return client.post('/api/history/compare', json={'before_known_at': before, **kwargs})


@pytest.mark.parametrize('old_values', [('72.00',), ('72.00', '76.00')])
def test_late_pulse_record_exact_scope_conflict_and_reviewed_quote(api, old_values):
    client, store, clock = api
    save(client, [['measurement', 'Pulse', value, 'bpm', '2021-04-05', 'Authored clinic']
                  for value in old_values], filename='early-pulse.csv')
    before = client.get('/api/history/view', params={'as_of': '2021-12-31'}).json()['scope']
    assert before['known_at'].endswith('.123456Z')
    clock[0] += timedelta(seconds=1, microseconds=1)
    receipt, draft, raw = save(client,
        [['measurement', 'Pulse', '74.50', 'bpm', '2021-04-05', 'Authored lab']],
        corrected='75.0', filename='late-pulse.csv')
    changes = client.get('/api/changes').json()
    capture_calls = []
    def counted_clock():
        capture_calls.append(True)
        return clock[0]
    store.clock = counted_clock
    response = compare(client, before['known_at'], as_of='2021-12-31')
    assert response.status_code == 200, response.text
    result = response.json()
    assert len(capture_calls) == 1
    assert result['format'] == 'modus-history-comparison-v1'
    assert result['before']['scope']['known_at'] == before['known_at']
    assert result['after']['scope']['known_at'] == receipt['available_at']
    assert result['after']['scope']['known_at'].endswith('.123457Z')
    assert result['captured_at'] == result['before']['scope']['captured_at'] == result['after']['scope']['captured_at']
    assert result['before']['scope']['as_of'] == result['after']['scope']['as_of'] == '2021-12-31'
    assert {f['value'] for f in result['before']['facts']} == set(old_values)
    assert result['unchanged_count'] == len(old_values)
    assert result['added_counts'] == {'total': 1, 'dated': 1, 'undated': 0}
    added = result['added'][0]
    assert added['id'] == receipt['fact_ids'][0]
    assert added['label'] == 'Pulse' and added['value'] == '75.0' and added['unit'] == 'bpm'
    assert added['occurred_on'] == '2021-04-05'
    assert added['source_quote'] == draft['facts'][0]['source_quote']
    assert '74.50' in added['source_quote'] and 'value' in added['reviewed_fields']
    group = result['new_conflicts'][0]
    assert set(group['values']) == {*old_values, '75.0'}
    assert group['resolution'] == 'unresolved' and group['specimen_equivalence'] == 'unknown'
    if len(old_values) > 1:
        assert group['id'] == result['before']['conflicts'][0]['id']
        assert len(group['fact_ids']) == len(result['before']['conflicts'][0]['fact_ids']) + 1
    original = f"/api/history/sources/{receipt['source_id']}/original"
    assert client.get(original, params={'as_of': '2021-12-31', 'known_at': before['known_at']}).status_code == 404
    assert client.get(original, params={'as_of': '2021-12-31', 'known_at': receipt['available_at']}).content == raw
    assert client.get('/api/changes').json() == changes
    assert client.get('/api/history/view').json()['counts']['facts'] == len(old_values) + 1


def test_all_kinds_partial_unknown_dates_and_safe_fields(api):
    client, _, clock = api
    before = client.get('/api/history/view').json()['scope']['known_at']
    clock[0] += timedelta(seconds=1)
    rows = [
        ['measurement', 'Pulse', '72.0', 'bpm', '2021-04-05', 'Authored clinic'],
        ['encounter', 'Visit', 'Visit as printed', '', '2021-04-05', 'Authored clinic'],
        ['recorded_diagnosis', 'Source diagnosis', 'Verbatim diagnostic wording', '', '2021-04-05', 'Authored clinic'],
        ['procedure', 'Source procedure', 'Verbatim procedure wording', '', '2021-04-05', 'Authored clinic'],
        ['prescription', 'Source prescription', 'Verbatim prescription wording', '', '2021-04-05', 'Authored clinic'],
        ['vaccination', 'Source vaccination', 'Verbatim vaccination wording', '', '2012', 'Authored clinic'],
        ['imaging_text', 'Source report', 'Verbatim report wording', '', '2020-08', 'Authored clinic'],
        ['recorded_text', 'Source note', 'Verbatim undated wording', '', '', 'Authored clinic'],
    ]
    save(client, rows)
    assert client.put('/api/profile', json={'date_of_birth': '1990-01-01'}).status_code == 200
    result = compare(client, before, as_of=None).json()
    assert len({row['kind'] for row in result['added']}) == 8
    assert result['added_counts'] == {'total': 8, 'dated': 5, 'undated': 3}
    assert {row['occurred_on'] for row in result['after']['undated_facts']} == {'2012', '2020-08', None}
    assert all(row['value'] is not None for row in result['after']['undated_facts'])
    for forbidden in ('profile', 'date_of_birth', 'age_years', 'reviewer', 'source_proposal', '1990-01-01'):
        assert forbidden not in json.dumps(result)
    scoped = compare(client, before, as_of='2021-12-31').json()
    assert all(row['value_withheld'] and row['value'] is None and row['source_quote'] is None
               for row in scoped['after']['undated_facts'])
    assert all(not row['original_available'] for row in scoped['after']['sources'])
    assert 'Verbatim undated wording' not in json.dumps(scoped)


def test_event_cutoff_future_availability_clamp_and_equivalent_offsets(api):
    client, _, clock = api
    before = client.get('/api/history/view').json()['scope']['known_at']
    clock[0] += timedelta(seconds=1)
    save(client, [['measurement', 'Pulse', '72', 'bpm', '2025-04-05', 'Authored clinic']])
    earlier = compare(client, before, as_of='2024-12-31', after_known_at='2099-01-01T00:00:00Z').json()
    assert earlier['added'] == []
    assert earlier['after']['scope']['known_at'] == earlier['captured_at']
    same = compare(client, '2026-10-29T17:00:00.123456+09:00', after_known_at=before).json()
    assert same['before']['scope']['known_at'] == same['after']['scope']['known_at'] == before
    assert same['added'] == []
    reversed_bounds = compare(client, '2099-01-01T00:00:00Z', after_known_at=before)
    assert reversed_bounds.status_code == 422


@pytest.mark.parametrize('body', [
    {}, {'before_known_at': None}, {'before_known_at': '2026-10-29T08:00:00'},
    {'before_known_at': 1793260800}, {'before_known_at': True},
    {'before_known_at': '1793260800'},
    {'before_known_at': '2026-10-29T08:00:00.1234567Z'},
    {'before_known_at': '2026-10-29T08:00:00Z', 'after_known_at': '2026-10-29'},
    {'before_known_at': '2026-10-29T08:00:00Z', 'as_of': '2021'},
    {'before_known_at': '2026-10-29T08:00:00Z', 'as_of': '2021-02-30'},
    {'before_known_at': '2026-10-29T08:00:00Z', 'as_of': '2021-01-01T00:00:00Z'},
    {'before_known_at': '2026-10-29T08:00:00Z', 'as_of': 1609459200},
    {'before_known_at': '2026-10-29T08:00:00Z', 'subject_id': 'other-owner'},
])
def test_invalid_or_extra_scope_authority_rejected(api, body):
    client, _, _ = api
    assert client.post('/api/history/compare', json=body).status_code == 422


@pytest.mark.parametrize('limit,value', [('MAX_FACTS_PER_VIEW', 0), ('MAX_RESPONSE_BYTES', 10)])
def test_oversized_comparison_rejects_instead_of_truncating_or_writing(api, monkeypatch, limit, value):
    client, _, _ = api
    save(client, [['measurement', 'Pulse', '72', 'bpm', '2021-04-05', 'Authored clinic']])
    changes = client.get('/api/changes').json()
    module = importlib.import_module('modus_entry.history_compare')
    monkeypatch.setattr(module, limit, value)
    response = compare(client, NOW.isoformat())
    assert response.status_code == 422
    assert 'exceeds' in response.json()['detail']
    assert 'added' not in response.json()
    assert client.get('/api/changes').json() == changes

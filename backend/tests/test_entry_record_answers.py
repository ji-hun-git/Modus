"""Independent synthetic answer regressions; no private corpus or model requests."""
from datetime import datetime, timezone

from fastapi.testclient import TestClient
import pytest

from modus_entry.app import create_entry_app
from modus_entry import agent
from modus_entry.tools import capture, conflict_text, dispatch


@pytest.fixture
def record_app(tmp_path, monkeypatch):
    monkeypatch.setenv('MODUS_PROVIDER', 'offline')
    monkeypatch.setenv('MODEL_API_KEY', '')
    now = [datetime(2026, 10, 28, 1, 0, tzinfo=timezone.utc)]
    app = create_entry_app(tmp_path / 'answers.db', clock=lambda: now[0])
    return app, TestClient(app), now


def save_late_record(client, now, *, metric='egfr', value='82', unit='mL/min/1.73m2'):
    content = f'metric,value,unit,date\n{metric},{value},{unit},2021-04-08\n'.encode()
    preview = client.post('/api/imports/preview', data={'synthetic_confirmed': 'true'},
                          files={'file': ('late-answer.csv', content, 'text/csv')})
    assert preview.status_code == 200, preview.text
    draft = preview.json()
    now[0] = datetime(2026, 10, 28, 2, 0, tzinfo=timezone.utc)
    response = client.post('/api/imports/commit', json={
        'draft_id': draft['id'], 'synthetic_confirmed': True,
        'reviewed_observations': [{key: row[key] for key in ('id', 'metric', 'value', 'unit', 'date')}
                                  for row in draft['observations']],
    })
    assert response.status_code == 200, response.text
    return response.json()


def test_answer_is_exact_selected_tool_findings_not_generic_prose(record_app):
    app, client, now = record_app
    receipt = save_late_record(client, now)
    response = client.post('/api/agent/chat', json={
        'as_of': '2021-12-31', 'message': 'Which eGFR values disagree?',
    })
    assert response.status_code == 200
    answer = response.json()
    assert answer['answer'] == '\n'.join(item['text'] for item in answer['claims'])
    assert answer['claims'] == answer['trace'][0]['result']['claims']
    assert 'Kidney filtering (eGFR)' in answer['answer']
    assert '2021-04-08' in answer['answer']
    assert '82.0 mL/min/1.73m2' in answer['answer'] and '96.0 mL/min/1.73m2' in answer['answer']
    assert set(receipt['observation_ids']) <= set(answer['claims'][0]['evidence_ids'])
    assert len(answer['claims'][0]['evidence_ids']) == 2
    assert answer['mode'] == 'offline' and answer['execution']['requested_model'] is None


def test_historical_negative_names_its_bounds_and_never_includes_late_conflict(record_app):
    app, client, now = record_app
    before = capture(app.state.store, '2021-12-31')['view']
    receipt = save_late_record(client, now)
    old = client.post('/api/agent/chat', json={
        'as_of': before['scope']['as_of'], 'known_at': before['scope']['known_at'],
        'message': 'Which eGFR values disagree?',
    }).json()
    assert old['scope']['known_at'] == before['scope']['known_at']
    assert old['trace'][0]['result']['conflicts'] == []
    assert 'among 2 recorded Kidney filtering (eGFR) measurements' in old['answer']
    assert 'measured through 2021-12-31' in old['answer']
    assert before['scope']['known_at'] in old['answer']
    assert 'Later arrivals are outside this captured view.' in old['answer']
    assert not set(receipt['observation_ids']) & set(old['claims'][0]['evidence_ids'])

    current = client.post('/api/agent/chat', json={
        'as_of': '2021-12-31', 'message': 'Which eGFR values disagree?',
    }).json()
    assert current['scope']['known_at'] != old['scope']['known_at']
    assert len(current['trace'][0]['result']['conflicts']) == 1
    assert set(receipt['observation_ids']) <= set(current['claims'][0]['evidence_ids'])


def test_empty_scope_does_not_claim_measurements_were_checked(record_app):
    app, client, now = record_app
    context = capture(app.state.store, '2000-01-01')
    result = dispatch(context, 'record_conflicts', {'metric': 'hba1c'})
    assert result['claims'][0]['evidence_ids'] == []
    assert result['claims'][0]['text'].startswith(
        'No recorded Average blood sugar (HbA1c) measurements are available to compare')
    assert 'No same-day disagreement was found' not in result['claims'][0]['text']
    assert '2000-01-01' in result['claims'][0]['text']


def test_different_units_and_decimal_precision_survive_answer(record_app):
    app, client, now = record_app
    save_late_record(client, now, metric='ldl', value='2.41234567', unit='mmol/L')
    result = agent.offline_chat(capture(app.state.store, '2021-12-31'), 'Which LDL values disagree?')
    assert '116.0 mg/dL' in result['answer'] and '2.41234567 mmol/L' in result['answer']
    assert 'Cholesterol (LDL)' in result['answer']
    assert 'specimen equivalence is unknown' in result['answer']
    assert len(result['claims'][0]['evidence_ids']) == 2


def test_large_conflict_summary_is_bounded_without_choosing_a_winner():
    group = {'metric': 'ldl', 'date': '2020-01-01', 'observations': [
        {'value': value, 'unit': 'mg/dL'} for value in range(10, 20)]}
    text = conflict_text(group)
    assert '10 mg/dL; 11 mg/dL' in text and '15 mg/dL' in text
    assert 'and 4 other recorded values' in text
    assert '16 mg/dL' not in text and 'All affected records are retained' in text


def test_unsupported_question_keeps_abstention_without_fabricated_findings(record_app):
    app, client, now = record_app
    result = agent.offline_chat(capture(app.state.store, '2021-12-31'), 'Do I need treatment?')
    assert result['answer'] == agent.UNSUPPORTED and result['claims'] == []
    assert result['trace'] == []

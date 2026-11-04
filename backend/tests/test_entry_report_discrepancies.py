"""Authored regression cases, separate from all evaluation and held-out sets."""
from copy import deepcopy
from datetime import timedelta

import pytest

from modus_entry.history_agent import offline_chat
from modus_entry.report_discrepancies import value_key
from modus.record_history_models import ReviewedFact
from test_entry_history_api import api, NOW
from test_entry_report_summary import fact
from test_entry_report_investigation import (
    QUESTION, context_of, model_run, request_for, import_report)


def related(left='4.00', right='4.00', **updates):
    return context_of(fact(), fact('b', '2024-02-03', left),
        fact('c', '2024-02-03', right, **updates))


@pytest.mark.parametrize('left,right', [
    ('4.00', '4.000'), ('4e0', '+4'), ('-0.0', '+0'),
    ('<0.50', '<0.5'), ('≤0.50', '<=0.5'), ('≥4.0', '>=4'),
    ('> 4.00', '>4'), ('Not detected', 'Not  detected'),
    ('Not\tdetected', 'Not detected'),
])
def test_formatting_only_does_not_flag_or_rewrite_originals(left, right):
    context = related(left, right)
    before = deepcopy(context)
    answer, calls = model_run(context)
    assert answer['report_investigation']['counts']['discrepancies'] == 0
    assert answer['answer'] == offline_chat(context, QUESTION)['answer']
    assert len(calls) == 3 and context == before
    assert context['view']['facts'][1]['value'] == left
    assert context['view']['facts'][2]['value'] == right


@pytest.mark.parametrize('left,right', [
    ('<0.5', '<5'), ('<0.5', '<=0.5'), ('>=4', '>4'), ('≤4', '≥4'),
    ('-4', '+4'), ('Not detected', 'Negative'), ('trace', 'Trace'),
    ('1,234', '1234'), ('0–4', '0-4'), ('<0.5', '0.5'),
    ('12345678901234567890123456789', '12345678901234567890123456788'),
])
def test_meaning_and_arbitrary_punctuation_are_not_normalized(left, right):
    answer = offline_chat(related(left, right), QUESTION)
    issue = answer['claims'][0]
    assert issue['category'] == 'discrepancy'
    assert set(issue['evidence_ids']) == {'b', 'c'}
    assert 'Recorded difference:' not in answer['answer']
    assert value_key(left) != value_key(right)


@pytest.mark.parametrize('field,printed,title', [
    ('test_method', 'Method B', 'Test method'),
    ('specimen', 'Plasma', 'Specimen'),
    ('reference_range', '2–7', 'Reference range'),
    ('facility', 'Other authored lab', 'Lab or facility'),
    ('unit', 'g/L', 'Printed unit'),
    ('unit', 'MG/L', 'Printed unit'),  # Unit case must not disappear.
])
def test_same_value_different_lab_context_is_source_backed(field, printed, title):
    context = related(**{field: printed})
    answer, _ = model_run(context)
    issue = answer['claims'][0]
    assert issue['category'] == 'discrepancy' and issue['status'] == 'conflict'
    assert title in issue['text'] and printed in issue['text']
    assert set(issue['evidence_ids']) == {'b', 'c'}
    assert answer['report_investigation']['counts']['discrepancies'] == 1
    assert {p['proofs'][0][field] for p in issue['record_proofs']} == {
        context['view']['facts'][1][field], printed}
    assert {r['id'] for r in answer['history_evidence']['facts']} == {'a', 'b', 'c'}
    assert 'neither is chosen as correct' in issue['text']


@pytest.mark.parametrize('field', ['unit', 'specimen', 'test_method', 'reference_range', 'facility'])
def test_missing_metadata_is_context_not_a_contradiction_or_all_clear(field):
    answer = offline_chat(related(**{field: None}), QUESTION)
    counts = answer['report_investigation']['counts']
    assert counts['discrepancies'] == 0 and counts['related_needs_context'] == 1
    related_claim = next(c for c in answer['claims'] if set(c['evidence_ids']) == {'b', 'c'})
    assert related_claim['category'] == 'needs_context'
    assert 'not recorded' in related_claim['text'] and 'unknown, not a contradiction' in related_claim['text']
    assert 'No differing same-day' not in answer['answer']
    assert {r['id'] for r in answer['history_evidence']['facts']} == {'a', 'b', 'c'}


def test_mixed_known_and_missing_context_reports_both_without_dropping_copies():
    context = related(test_method='Method B')
    context = context_of(*context['view']['facts'], fact('d', '2024-02-03', '4.00', test_method=None))
    answer = offline_chat(context, QUESTION)
    issue = answer['claims'][0]
    assert issue['category'] == 'discrepancy' and set(issue['evidence_ids']) == {'b', 'c', 'd'}
    assert 'Method A' in issue['text'] and 'Method B' in issue['text'] and 'not recorded' in issue['text']
    assert 'unknown, not a contradiction' in issue['text']


def test_missing_source_excerpt_prevents_a_supported_metadata_discrepancy():
    answer = offline_chat(related(test_method='Method B', source_quote=None), QUESTION)
    assert answer['report_investigation']['counts']['discrepancies'] == 0
    issue = next(c for c in answer['claims'] if set(c['evidence_ids']) == {'b', 'c'})
    assert issue['category'] == 'needs_context' and 'original excerpt is unavailable' in issue['text']
    assert 'Method B' not in issue['text']


def test_lab_context_spacing_only_is_not_a_conflict():
    answer = offline_chat(related(test_method='Method  A', specimen=' Serum '), QUESTION)
    assert answer['report_investigation']['counts']['discrepancies'] == 0


def test_metadata_correction_requires_review_preserves_capture_and_originals(api):
    client, store = api
    a, raw_a = import_report(client, 'Selected.csv', '5.25', '2025-02-03')
    b, raw_b = import_report(client, 'Earlier.csv', '4.00', '2024-02-03')
    c, raw_c = import_report(client, 'Copy.csv', '4.000', '2024-02-03')
    assert c != b  # Distinct file bytes; exact duplicate imports are idempotent.
    request = request_for(client, a, b)
    before = client.post('/api/history/report-investigation', json=request).json()
    assert before['report_investigation']['counts']['discrepancies'] == 0
    row = next(r for r in client.get('/api/history/view').json()['facts'] if r['source_id'] == c)
    store.clock = lambda: NOW + timedelta(seconds=10)
    corrected = {k: row.get(k) for k in ReviewedFact.model_fields} | {'test_method': 'Method B'}
    change = {'expected_revision_id': row['revision_id'], 'reason': 'Correct reviewed method', 'corrected': corrected}
    preview = client.post('/api/history/amendments/preview', json=change)
    assert preview.status_code == 200
    body = {**change, 'preview_id': preview.json()['preview_id']}
    assert client.post('/api/history/amendments/commit', json={**body, 'reviewed': False}).status_code == 422
    assert client.post('/api/history/amendments/commit', json={**body, 'reviewed': True}).status_code == 200
    latest = client.post('/api/history/report-investigation', json=request_for(client, a, b)).json()
    assert latest['report_investigation']['counts']['discrepancies'] == 1
    assert 'Method B' in latest['claims'][0]['text']
    old = client.post('/api/history/report-investigation', json=request).json()
    assert old['claims'] == before['claims']
    for sid, raw in ((a, raw_a), (b, raw_b), (c, raw_c)):
        assert client.get(f'/api/history/sources/{sid}/original', params={
            'known_at': (NOW + timedelta(seconds=10)).isoformat()}).content == raw

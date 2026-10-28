"""Fresh authored record-brief contracts; no network or private evaluation data."""
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from html.parser import HTMLParser
import json

from pydantic import ValidationError
import pytest

from modus.record_history import commit_history, update_profile
from modus.record_history_models import ReviewedFact
from modus.record_store import RecordStore
from modus_entry.briefs import (BriefRequest, BriefExportRequest, BriefChangedError,
    build_brief, validate_export, render_html, render_json)


NOW = datetime(2026, 10, 28, 10, tzinfo=timezone.utc)


@pytest.fixture
def memory(tmp_path):
    clock = [NOW]
    store = RecordStore(tmp_path / 'brief-authored.db', seed_provider=lambda: ([], []), clock=lambda: clock[0])
    return store, clock


def fact(kind='measurement', label='Example reading', value='12.30', unit='example-unit', day='2020-04-05', **updates):
    return {'kind': kind, 'label': label, 'value': value, 'unit': unit,
        'occurred_on': day, 'facility': 'Authored clinic',
        'source_quote': f'{label} {value} {unit or ""} {day or ""}',
        'page': 1, 'bbox': None, 'model_confidence': None, 'extractor': 'authored-test', **updates}


def commit(store, rows, title='brief-authored-record.json'):
    rows = [dict(row, id=f'field-{index}') for index, row in enumerate(rows)]
    raw = json.dumps({'title': title, 'facts': rows}, ensure_ascii=False).encode()
    digest = sha256(raw).hexdigest()
    sid = 'import-' + digest[:20]
    draft = {'id': sid, 'source': {'id': sid, 'title': title, 'type': 'Document',
        'provider': 'Authored source', 'date': '', 'content': 'RAW_SOURCE_NOT_FOR_BRIEF_817',
        'synthetic': True, 'sha256': digest}, 'facts': rows, 'observations': [], 'extraction_mode': 'manual'}
    store.add_draft(draft, raw, title, 'application/json')
    selected = [{key: row.get(key) for key in ReviewedFact.model_fields} for row in rows]
    return commit_history(store, sid, selected)


def request(ids, **updates):
    return BriefRequest.model_validate({'known_at': NOW, 'selected_fact_ids': ids, **updates})


def export_request(preview, ids, **updates):
    return BriefExportRequest.model_validate({'as_of': preview['scope']['as_of'],
        'known_at': preview['scope']['known_at'], 'selected_fact_ids': ids,
        'title': preview['title'], 'owner_note': preview['owner_note'],
        'reviewed': True, 'preview_id': preview['preview_id'], **updates})


def test_all_kinds_dates_values_and_citations_are_source_exact(memory):
    store, _ = memory
    rows = [fact(), fact('encounter', 'Visit', 'Visit as recorded', None),
        fact('recorded_diagnosis', 'Provider wording', 'Original diagnosis statement', None),
        fact('procedure', 'Procedure', 'Recorded procedure', None),
        fact('prescription', 'Example medicine', 'Original instruction text', None),
        fact('vaccination', 'Recorded vaccine', 'Recorded dose', None, '2012'),
        fact('imaging_text', 'Report', 'Original imaging report wording', None, None),
        fact('recorded_text', 'Letter', 'Source-recorded text', None, '2020-04')]
    receipt = commit(store, rows)
    brief = build_brief(store, request(receipt['fact_ids']))
    assert brief['counts'] == {'selected': 8, 'conflict_companions': 0, 'total': 8, 'sources': 1}
    assert len({row['kind'] for row in brief['entries']}) == 8
    assert [row['citation'] for row in brief['entries']] == [f'R{i}' for i in range(1, 9)]
    assert all(row['source_citation'] == 'S1' for row in brief['entries'])
    by_label = {row['label']: row for row in brief['entries']}
    assert by_label['Example reading']['value'] == '12.30'
    assert by_label['Example reading']['unit'] == 'example-unit'
    assert by_label['Recorded vaccine']['occurred_on'] == '2012'
    assert by_label['Recorded vaccine']['date'] is None
    assert by_label['Report']['occurred_on'] is None
    assert by_label['Letter']['occurred_on'] == '2020-04'
    assert '2012-01-01' not in json.dumps(brief)
    assert len(brief['history_evidence']['facts']) == 5
    assert len(brief['history_evidence']['undated_facts']) == 3
    assert any('current medication use' in warning for warning in brief['warnings'])
    assert all(row['selected_by_owner'] and not row['added_for_conflict'] for row in brief['entries'])
    html = render_html(validate_export(store, export_request(brief, receipt['fact_ids'])))
    assert 'Imaging report text · Date not recorded' in html
    assert 'Recorded date not recorded' not in html
    assert '8 records in this brief.' in html


def test_conflict_selection_keeps_every_value_and_marks_added_companions(memory):
    store, _ = memory
    first = commit(store, [fact(value='12.30')], 'first.json')
    second = commit(store, [fact(value='19.40')], 'second.json')
    brief = build_brief(store, request(first['fact_ids']))
    assert brief['counts'] == {'selected': 1, 'conflict_companions': 1, 'total': 2, 'sources': 2}
    assert {row['value'] for row in brief['entries']} == {'12.30', '19.40'}
    added = next(row for row in brief['entries'] if row['id'] == second['fact_ids'][0])
    assert added['added_for_conflict'] and not added['selected_by_owner']
    assert brief['conflicts'][0]['resolution'] == 'unresolved'
    assert set(brief['conflicts'][0]['fact_ids']) == set(first['fact_ids'] + second['fact_ids'])
    assert set(row['id'] for row in brief['history_evidence']['facts']) == set(first['fact_ids'] + second['fact_ids'])
    checked = validate_export(store, export_request(brief, first['fact_ids']))
    html = render_html(checked)
    assert 'Unresolved differences' in html and 'No value has been selected as correct' in html
    assert '12.30' in html and '19.40' in html
    assert '1 additional record is included' in html
    assert '1 record in this brief.' in html
    assert '1 records' not in html


@pytest.mark.parametrize('changes', [
    {'selected_fact_ids': []}, {'selected_fact_ids': ['same', 'same']},
    {'selected_fact_ids': ['x' * 161]}, {'selected_fact_ids': [str(i) for i in range(81)]},
    {'selected_fact_ids': [123]}, {'selected_fact_ids': [' ']},
    {'title': '  '}, {'title': 'x' * 101}, {'owner_note': 'x' * 1201},
    {'known_at': '2026-10-28T00:00:00'}, {'known_at': 1793145600}, {'as_of': 1793145600}, {'profile_id': 'other'},
    {'known_at': '1793145600'}, {'as_of': '2026-10-28T00:00:00Z'},
    {'source_quote': 'client-provided source'}, {'execute_sql': 'SELECT anything'},
])
def test_request_rejects_unbounded_or_authority_input(changes):
    with pytest.raises(ValidationError):
        BriefRequest.model_validate({'known_at': NOW, 'selected_fact_ids': ['one'], **changes})


@pytest.mark.parametrize('reviewed', [False, None, 1, 'true'])
def test_export_requires_actual_explicit_confirmation(reviewed):
    with pytest.raises(ValidationError):
        BriefExportRequest.model_validate({'known_at': NOW, 'selected_fact_ids': ['one'],
            'preview_id': 'sha256:' + 'a' * 64, 'reviewed': reviewed})


def test_unknown_future_and_late_records_cannot_be_selected(memory):
    store, clock = memory
    old = commit(store, [fact()], 'old.json')
    future = commit(store, [fact(day='2030-01-01')], 'future.json')
    clock[0] += timedelta(days=1)
    late = commit(store, [fact('prescription', 'Late medicine', 'LATE_VALUE_492', None)], 'late.json')
    for ids, overrides in [(['unavailable'], {}), (future['fact_ids'], {'as_of': '2021-01-01'}), (late['fact_ids'], {})]:
        with pytest.raises(ValueError, match='unavailable'):
            build_brief(store, request(ids, **overrides))
    visible = build_brief(store, request(old['fact_ids']))
    assert 'LATE_VALUE_492' not in json.dumps(visible)


def test_historical_numeric_fact_does_not_leak_mixed_source_text(memory):
    store, _ = memory
    receipt = commit(store, [fact(source_quote='WITHHELD_QUOTE_392'),
        fact('recorded_text', 'Old letter', 'WITHHELD_VALUE_527', None),
        fact('imaging_text', 'Future report', 'FUTURE_REPORT_932', None, '2030-01-01')])
    brief = build_brief(store, request([receipt['fact_ids'][0]], as_of='2021-01-01'))
    text = json.dumps(brief)
    assert all(word not in text for word in ('WITHHELD_QUOTE_392', 'WITHHELD_VALUE_527', 'FUTURE_REPORT_932'))
    assert brief['entries'][0]['value'] == '12.30'
    assert brief['entries'][0]['source_quote'] is None
    assert not brief['sources'][0]['original_available']
    with pytest.raises(ValueError, match='unavailable'):
        build_brief(store, request([receipt['fact_ids'][1]], as_of='2021-01-01'))


def test_profile_and_unreviewed_proposals_are_excluded(memory):
    store, _ = memory
    receipt = commit(store, [fact()])
    update_profile(store, '1984-09-13')
    brief = build_brief(store, request(receipt['fact_ids']))
    encoded = json.dumps(brief)
    for forbidden in ('1984-09-13', 'source_proposal', 'reviewer', 'age_years', 'RAW_SOURCE_NOT_FOR_BRIEF_817'):
        assert forbidden not in encoded


def test_digest_stable_across_clock_profile_and_selection_order(memory):
    store, clock = memory
    receipt = commit(store, [fact(label='First'), fact(label='Second')])
    first = build_brief(store, request(receipt['fact_ids']))
    clock[0] += timedelta(hours=1)
    update_profile(store, '1984-09-13')
    second = build_brief(store, request(list(reversed(receipt['fact_ids']))))
    assert second['scope']['captured_at'] != first['scope']['captured_at']
    assert first['preview_id'] == second['preview_id']
    validated = validate_export(store, export_request(first, receipt['fact_ids']))
    assert validated['reviewed'] is True
    assert validated['reviewed_at'] == second['generated_at']


@pytest.mark.parametrize('change', ['title', 'owner_note', 'selection', 'availability', 'occurrence'])
def test_export_rejects_changed_review_content(memory, change):
    store, _ = memory
    receipt = commit(store, [fact(label='First'), fact(label='Second')])
    preview = build_brief(store, request(receipt['fact_ids']))
    changes = {'title': {'title': 'Changed brief'}, 'owner_note': {'owner_note': 'Changed note'},
        'selection': {'selected_fact_ids': receipt['fact_ids'][:1]},
        'availability': {'known_at': NOW - timedelta(seconds=1)}, 'occurrence': {'as_of': '2021-01-01'}}[change]
    with pytest.raises(ValueError):
        validate_export(store, export_request(preview, receipt['fact_ids'], **changes))


@pytest.mark.parametrize('target', ['source_quote', 'source_title'])
def test_export_digest_covers_source_evidence(memory, target):
    store, _ = memory
    receipt = commit(store, [fact()])
    preview = build_brief(store, request(receipt['fact_ids']))
    # A local integrity change must invalidate review even with unchanged value.
    with store.connect() as db:
        table, key = ('history_facts', receipt['fact_ids'][0]) if target == 'source_quote' else ('sources', receipt['source_id'])
        row = json.loads(db.execute(f'SELECT data FROM {table} WHERE id=?', (key,)).fetchone()[0])
        row['source_quote' if target == 'source_quote' else 'title'] = 'Altered original evidence'
        db.execute(f'UPDATE {table} SET data=? WHERE id=?', (json.dumps(row), key))
    with pytest.raises(BriefChangedError):
        validate_export(store, export_request(preview, receipt['fact_ids']))


def test_later_conflicting_upload_does_not_enter_pinned_brief(memory):
    store, clock = memory
    first = commit(store, [fact(value='12.30')], 'first.json')
    preview = build_brief(store, request(first['fact_ids']))
    clock[0] += timedelta(minutes=1)
    commit(store, [fact(value='19.40')], 'later.json')
    validated = validate_export(store, export_request(preview, first['fact_ids']))
    assert validated['counts']['total'] == 1 and validated['conflicts'] == []
    assert validated['preview_id'] == preview['preview_id']
    refreshed = build_brief(store, request(first['fact_ids'], known_at=clock[0]))
    assert refreshed['counts']['total'] == 2 and len(refreshed['conflicts']) == 1


def test_conflict_expansion_never_silently_truncates(memory):
    store, _ = memory
    receipt = commit(store, [fact(value=str(i)) for i in range(121)])
    with pytest.raises(ValueError, match='exceed 120'):
        build_brief(store, request(receipt['fact_ids'][:1]))


class Tags(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []
    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


def test_export_escapes_sources_owner_note_and_has_only_internal_links(memory):
    store, _ = memory
    injection = '</title><script>fetch("https://example.invalid")</script><img src=x onerror=alert(1)>'
    receipt = commit(store, [fact('recorded_text', injection, injection, None, source_quote=injection)], injection)
    preview = build_brief(store, request(receipt['fact_ids'], title='<b>My brief</b>', owner_note=injection))
    with pytest.raises(ValueError, match='reviewed'):
        render_html(preview)
    checked = validate_export(store, export_request(preview, receipt['fact_ids']))
    html = render_html(checked)
    parser = Tags()
    parser.feed(html)
    assert not {'script', 'img', 'iframe', 'form', 'object', 'embed'}.intersection(tag for tag, _ in parser.tags)
    assert all(not key.startswith('on') for _, attrs in parser.tags for key in attrs)
    assert all(attrs['href'].startswith('#') for _, attrs in parser.tags if 'href' in attrs)
    assert '&lt;script&gt;' in html and 'Written by the owner' in html
    assert json.loads(render_json(checked))['owner_note'] == injection


def test_preview_and_export_do_not_write_records_or_runs(memory):
    store, _ = memory
    receipt = commit(store, [fact()])
    def stored():
        with store.connect() as db:
            return {table: [tuple(row) for row in db.execute('SELECT * FROM ' + table)]
                for table in ('history_facts', 'history_commits', 'sources', 'documents', 'runs', 'record_commits')}
    before = stored()
    preview = build_brief(store, request(receipt['fact_ids'], owner_note='A note for this visit.'))
    checked = validate_export(store, export_request(preview, receipt['fact_ids']))
    render_html(checked)
    render_json(checked)
    assert stored() == before

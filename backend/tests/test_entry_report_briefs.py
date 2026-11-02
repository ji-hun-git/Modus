"""New authored offline HTTP checks; never use model or frozen evaluation data."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import json

import pytest
from test_entry_history_api import api, NOW
from test_entry_lab_context import imported, CSV
from test_entry_report_summary import two_reports, request_for
from modus.record_history_models import ReviewedFact


def prepared(client, first, second, **scope):
    body = request_for(client, first, second, **scope)
    result = client.post('/api/briefs/report-preview', json=body)
    assert result.status_code == 200, result.text
    return body, result.json()


def export_body(body, brief, **updates):
    return {**body, 'reviewed': True, 'preview_id': brief['preview_id'], 'format': 'json', **updates}


def test_compare_review_export_binds_numbers_sources_originals_and_does_not_write(api):
    client, store = api
    a, b = two_reports(client)
    before = store.history()
    body, brief = prepared(client, a, b)
    assert brief['comparison']['rows'][0]['difference'] == '1.25'
    assert brief['counts']['total'] == 2
    assert {r['source_id'] for r in brief['entries']} == {a, b}
    result = client.post('/api/briefs/report-export', json=export_body(body, brief))
    assert result.status_code == 200, result.text
    data = result.json()
    assert data['reviewed'] is True
    assert data['preview_id'] == brief['preview_id']
    assert data['comparison'] == brief['comparison']
    assert data['entries'] == brief['entries']
    html = client.post('/api/briefs/report-export', json=export_body(body, brief, format='html'))
    assert html.status_code == 200
    assert 'Two-report comparison' in html.text and '1.25' in html.text
    for row in brief['entries']:
        assert f'href="#{row["citation"]}"' in html.text
        assert f'id="{row["citation"]}"' in html.text
    assert "default-src 'none'" in html.headers['content-security-policy']
    assert html.headers['cache-control'] == 'no-store'
    assert store.history() == before


@pytest.mark.parametrize('reviewed', [False, 1, 'true', None])
def test_export_requires_literal_owner_confirmation(api, reviewed):
    client, _ = api
    body, brief = prepared(client, *two_reports(client))
    assert client.post('/api/briefs/report-export', json=export_body(body, brief, reviewed=reviewed)).status_code == 422


@pytest.mark.parametrize('change', [
    {'title':'Different title'}, {'owner_note':'Different note'}, {'preview_id':'sha256:'+'0'*64},
])
def test_changed_content_needs_new_preview(api, change):
    client, _ = api
    body, brief = prepared(client, *two_reports(client))
    assert client.post('/api/briefs/report-export', json=export_body(body, brief, **change)).status_code == 409


def test_reversed_reports_cannot_export_another_preview(api):
    client, _ = api
    a, b = two_reports(client)
    body, brief = prepared(client, a, b)
    payload = export_body(body, brief, selected_source_id=b, comparison_source_id=a)
    assert client.post('/api/briefs/report-export', json=payload).status_code == 409
    assert client.post('/api/briefs/report-preview', json={**body, 'comparison':{}}).status_code == 422
    assert client.post('/api/briefs/report-preview', json={**body, 'known_at':'2030-01-01T00:00:00Z'}).status_code == 422


def test_correction_invalidates_export_but_fresh_historical_view_remains_available(api):
    client, store = api
    a, b = two_reports(client)
    body, brief = prepared(client, a, b)
    original = client.get(f'/api/history/sources/{a}/original', params={'known_at':NOW.isoformat()}).content
    row = next(r for r in brief['entries'] if r['source_id'] == a)
    store.clock = lambda: NOW + timedelta(seconds=10)
    corrected = {key:row.get(key) for key in ReviewedFact.model_fields}
    corrected['value'] = '5.50'
    change = {'expected_revision_id':row['revision_id'], 'reason':'Correct a reviewed value', 'corrected':corrected}
    preview = client.post('/api/history/amendments/preview', json=change).json()
    saved = client.post('/api/history/amendments/commit', json={**change, 'preview_id':preview['preview_id'], 'reviewed':True})
    assert saved.status_code == 200, saved.text
    assert client.post('/api/briefs/report-export', json=export_body(body, brief)).status_code == 409
    assert client.post('/api/briefs/report-preview', json=body).status_code == 409
    _, current = prepared(client, a, b)
    assert current['comparison']['rows'][0]['difference'] == '1.50'
    historical_body, historical = prepared(client, a, b, known_at=NOW.isoformat())
    assert historical['comparison']['rows'][0]['difference'] == '1.25'
    assert client.post('/api/briefs/report-export', json=export_body(historical_body, historical)).status_code == 200
    assert client.get(f'/api/history/sources/{a}/original', params={'known_at':store.clock().isoformat()}).content == original


def test_related_conflicting_file_is_kept_and_no_winner_or_delta_is_exported(api):
    client, _ = api
    a, b = two_reports(client)
    header, *rows = CSV.splitlines(keepends=True)
    c = imported(client, header+rows[1].replace(b'5.25', b'5.75'))[2]['source_id']
    body, brief = prepared(client, a, b)
    assert brief['counts']['conflict_companions'] == 1
    assert {r['source_id'] for r in brief['entries']} == {a, b, c}
    assert not any('Open the Home' in warning for warning in brief['warnings'])
    assert brief['comparison']['rows'][0]['difference'] is None
    html = client.post('/api/briefs/report-export', json=export_body(body, brief, format='html')).text
    assert '5.25' in html and '5.75' in html and 'No numerical difference is shown' in html
    assert 'No value has been selected as correct' in html


def test_hidden_future_evidence_does_not_leak_through_export(api):
    client, _ = api
    header, *rows = CSV.splitlines(keepends=True)
    future = b'recorded_text,Future secret,FUTURE_ONLY_TOKEN,,2030-01-01,Example lab,,,\n'
    a = imported(client, header+rows[1]+future)[2]['source_id']
    b = imported(client, header+rows[0])[2]['source_id']
    body, brief = prepared(client, a, b, as_of='2025-12-31')
    assert brief['counts']['total'] == 2
    assert any(row['source_quote_withheld'] for row in brief['entries'])
    for format in ('html','json'):
        result = client.post('/api/briefs/report-export', json=export_body(body, brief, format=format))
        assert result.status_code == 200
        assert 'FUTURE_ONLY_TOKEN' not in result.text and 'Future secret' not in result.text


def test_expired_capture_unavailable_sources_and_untrusted_title(api):
    client, store = api
    a, b = two_reports(client)
    body = {**request_for(client,a,b), 'title':'<script>alert(1)</script>', 'owner_note':'<img src=x onerror=alert(1)>'}
    brief = client.post('/api/briefs/report-preview', json=body).json()
    html = client.post('/api/briefs/report-export', json=export_body(body,brief,format='html')).text
    assert '&lt;script&gt;' in html and '<script>' not in html
    assert '&lt;img' in html and '<img' not in html
    assert client.post('/api/briefs/report-preview', json={**body,'selected_source_id':'unknown'}).status_code == 422
    store.history_pages.captures.clear()
    assert client.post('/api/briefs/report-export', json=export_body(body,brief)).status_code == 409


def test_all_120_records_are_exported_without_selection_or_page_truncation(api):
    client, _ = api
    header = CSV.splitlines(keepends=True)[0]
    def report(year, extra=0):
        return header + ''.join(f'measurement,Test {i},{i+year-2023}.00,mg/L,{year}-02-03,Example lab,1-200,Serum,Method A\n' for i in range(60+extra)).encode()
    a, b = [imported(client,report(year))[2]['source_id'] for year in (2025,2024)]
    body, brief = prepared(client,a,b)
    assert brief['counts']['total'] == 120 and brief['counts']['selected'] == 120
    result = client.post('/api/briefs/report-export',json=export_body(body,brief)).json()
    assert len(result['entries']) == 120
    c = imported(client,report(2023,1))[2]['source_id']
    oversized = client.post('/api/briefs/report-preview',json=request_for(client,a,c))
    assert oversized.status_code == 422 and '120-record' in oversized.text


def test_parallel_exports_retain_one_review_identity(api):
    client, store = api
    body, brief = prepared(client,*two_reports(client))
    before = store.history()
    with ThreadPoolExecutor(max_workers=4) as pool:
        responses = list(pool.map(lambda _: client.post('/api/briefs/report-export',json=export_body(body,brief)), range(12)))
    assert all(r.status_code == 200 and r.json()['preview_id'] == brief['preview_id'] for r in responses)
    assert store.history() == before

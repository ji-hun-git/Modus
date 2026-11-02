"""Reviewed two-report exports reuse the existing brief evidence/size contract."""
from hmac import compare_digest
from html import escape
from typing import Literal

from pydantic import Field, field_validator

from .briefs import BriefRequest, BriefExportRequest, BriefChangedError, compile_brief, seal_brief
from .history_pages import SnapshotExpired
from .report_summary import ReportSummaryRequest, build_report_summary


class ReportBriefRequest(ReportSummaryRequest):
    title: str = Field(default='My checkup comparison', strict=True, min_length=1, max_length=100)
    owner_note: str = Field(default='', strict=True, max_length=1200)

    @field_validator('title')
    @classmethod
    def meaningful_title(cls, value):
        return BriefRequest.meaningful_title(value)


class ReportBriefExportRequest(ReportBriefRequest):
    reviewed: Literal[True]
    preview_id: str = Field(strict=True, pattern=r'^sha256:[0-9a-f]{64}$')
    format: Literal['html', 'json'] = 'html'

    @field_validator('reviewed', mode='before')
    @classmethod
    def actual_confirmation(cls, value):
        return BriefExportRequest.actual_confirmation(value)


def build_report_brief(store, request):
    if not isinstance(request, ReportBriefRequest):
        request = ReportBriefRequest.model_validate(request)
    captured = store.history_pages.get(request.snapshot_id)
    # Browsing may retain a frozen comparison. Preparing/downloading a brief
    # additionally requires a fresh capture, including for historical scopes.
    with store.connect() as db:
        revision = db.execute("SELECT value FROM record_store_meta WHERE key='history_revision'").fetchone()[0]
    if captured['revision'] != revision:
        raise SnapshotExpired('Records changed after this view was opened. Refresh history and review the comparison again.')
    selection = ReportSummaryRequest.model_validate({key: getattr(request, key) for key in ReportSummaryRequest.model_fields})
    summary = build_report_summary(captured['view'], selection)
    evidence = summary['history_evidence']
    ids = [row['id'] for row in evidence['facts'] + evidence['undated_facts']]
    brief = compile_brief(captured['view'], ids, request.title, request.owner_note)
    brief['comparison'] = {key: value for key, value in summary.items() if key != 'history_evidence'}
    # The comparison supplies the more specific scope note. Conflict companions
    # are already included here, so do not send an exported-file reader Home.
    brief['warnings'] = [warning for warning in brief['warnings']
                         if not warning.startswith('This brief contains selected records;')]
    brief['warnings'].extend(note for note in summary['limitations']
                             if not note.startswith('Related discrepancies also involve other files.'))
    return seal_brief(brief)


def validate_report_export(store, request):
    if not isinstance(request, ReportBriefExportRequest):
        request = ReportBriefExportRequest.model_validate(request)
    brief = build_report_brief(store, request)
    if not compare_digest(brief['preview_id'], request.preview_id):
        raise BriefChangedError('The report selection or brief changed. Prepare and review it again.')
    brief['reviewed'] = True
    brief['reviewed_at'] = brief['generated_at']
    return brief


def render_comparison(brief):
    """Internal evidence citations only; no executable or remote content."""
    e = lambda value: escape(str(value), quote=True)
    summary = brief['comparison']
    citations = {row['id']: row['citation'] for row in brief['entries']}
    claims = {claim['id']: claim for claim in summary['claims']}
    parts = ['<section><h2>Two-report comparison</h2>',
             f'<p>Selected report: {e(summary["current_source"]["title"])}<br>',
             f'Compared with: {e(summary["previous_source"]["title"])}</p>']
    for row in summary['rows']:
        parts.append(f'<article><h3>{e(row["label"])}</h3>')
        for label, key in [('Selected report', 'current_ids'), ('Comparison report', 'previous_ids')]:
            refs = ', '.join(f'<a href="#{citations[fid]}">{citations[fid]}</a>' for fid in row[key])
            parts.append(f'<p>{label}: {refs or "No matching reviewed item"}</p>')
        supported = [claims[cid] for cid in row['claim_ids']
                     if claims[cid]['type'] == 'difference' and claims[cid]['verification']['status'] == 'SUPPORTED']
        if supported:
            parts.extend(f'<p>{e(claim["text"])}</p>' for claim in supported)
        elif row['current_ids'] and row['previous_ids']:
            parts.append('<p>No numerical difference is shown.</p>')
        parts.extend(f'<p class="meta">{e(note)}</p>' for note in row['notes'])
        parts.append('</article>')
    parts.append(f'<p class="meta">Comparison policy: {e(summary["policy_version"])}</p></section>')
    return ''.join(parts)

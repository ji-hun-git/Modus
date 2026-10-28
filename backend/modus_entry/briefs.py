"""Deterministic, owner-reviewed compilations of selected source-linked records.

The digest binds displayed content, not a person's identity or clinical accuracy.
No model, external service or persistent write is involved in this workflow.
"""
from copy import deepcopy
from datetime import date, datetime
from hashlib import sha256
from hmac import compare_digest
from html import escape
import json
import re
from typing import Annotated, Literal

from pydantic import AwareDatetime, Field, field_validator

from .history_tools import available_fact, capture_history
from .models import Strict
from .runtime import BUNDLE_ID


FORMAT = 'modus-record-brief-v1'
MAX_TOTAL_RECORDS = 120
MAX_BRIEF_BYTES = 2_000_000
FactId = Annotated[str, Field(strict=True, min_length=1, max_length=160)]
KIND_LABELS = {
    'measurement': 'Measurement', 'encounter': 'Visit',
    'recorded_diagnosis': 'Diagnosis as recorded', 'procedure': 'Procedure',
    'prescription': 'Historical prescription', 'vaccination': 'Vaccination',
    'imaging_text': 'Imaging report text', 'recorded_text': 'Other recorded text',
}


class BriefRequest(Strict):
    as_of: date | None = None
    known_at: AwareDatetime
    selected_fact_ids: list[FactId] = Field(min_length=1, max_length=80)
    title: str = Field(default='Record brief', strict=True, min_length=1, max_length=100)
    owner_note: str = Field(default='', strict=True, max_length=1200)

    @field_validator('as_of', mode='before')
    @classmethod
    def exact_date_input(cls, value):
        if value is not None and not (type(value) is date or isinstance(value, str)):
            raise ValueError('Use an ISO date or null for the recorded-date cutoff')
        if isinstance(value, str) and not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', value):
            raise ValueError('Use an exact YYYY-MM-DD recorded-date cutoff')
        return value

    @field_validator('known_at', mode='before')
    @classmethod
    def timestamp_input(cls, value):
        if not isinstance(value, (str, datetime)):
            raise ValueError('Use an aware timestamp for file availability')
        if isinstance(value, str):
            datetime.fromisoformat(value.replace('Z', '+00:00'))
        return value

    @field_validator('title')
    @classmethod
    def meaningful_title(cls, value):
        if not value.strip():
            raise ValueError('Give the brief a title')
        return value.strip()

    @field_validator('selected_fact_ids')
    @classmethod
    def distinct_records(cls, value):
        if len(value) != len(set(value)) or any(not item.strip() for item in value):
            raise ValueError('Select distinct record IDs')
        return value


class BriefExportRequest(BriefRequest):
    reviewed: Literal[True]
    preview_id: str = Field(strict=True, pattern=r'^sha256:[0-9a-f]{64}$')
    format: Literal['html', 'json'] = 'html'

    @field_validator('reviewed', mode='before')
    @classmethod
    def actual_confirmation(cls, value):
        if value is not True:
            raise ValueError('Review the complete brief before downloading it')
        return value


class BriefChangedError(ValueError):
    """The requested export no longer matches its reviewed preview."""


def _binding(brief):
    return {key: brief[key] for key in (
        'format', 'bundle_id', 'title', 'owner_note', 'entries', 'sources',
        'conflicts', 'warnings', 'counts',
    )} | {'scope': {key: brief['scope'][key] for key in ('as_of', 'known_at')}}


def build_brief(store, request):
    if not isinstance(request, BriefRequest):
        request = BriefRequest.model_validate(request)
    context = capture_history(store, request.as_of, request.known_at)
    view = context['view']
    rows = view['facts'] + view['undated_facts']
    visible = {row['id']: row for row in rows if available_fact(row) and row.get('value') is not None}
    selected = set(request.selected_fact_ids)
    if not selected <= visible.keys():
        raise ValueError('Some selected records are unavailable in this view. Refresh the selection.')

    groups = [group for group in view['conflicts'] if selected.intersection(group['fact_ids'])]
    included = selected | {key for group in groups for key in group['fact_ids']}
    if not included <= visible.keys():
        raise ValueError('The complete discrepancy evidence is unavailable in this view.')
    if len(included) > MAX_TOTAL_RECORDS:
        raise ValueError('This selection and its discrepancy evidence exceed 120 records. Choose a smaller group.')

    # Sort independently of client order. Exact-date records form the timeline;
    # partial/unknown dates stay at the end without invented precision.
    ordered = sorted((visible[key] for key in included),
        key=lambda row: (row.get('date') is None, row.get('date') or '', row['id']))
    source_ids = {row['source_id'] for row in ordered}
    sources = sorted((deepcopy(source) for source in view['sources'] if source['id'] in source_ids), key=lambda row: row['id'])
    source_citations = {source['id']: f'S{index}' for index, source in enumerate(sources, 1)}
    for source in sources:
        source['citation'] = source_citations[source['id']]
        source['brief_fact_count'] = sum(row['source_id'] == source['id'] for row in ordered)
    entries = [deepcopy(row) | {'citation': f'R{index}', 'source_citation': source_citations[row['source_id']],
        'selected_by_owner': row['id'] in selected, 'added_for_conflict': row['id'] not in selected}
        for index, row in enumerate(ordered, 1)]
    warnings = ['This brief contains selected records; it is not a complete health history.']
    companion_count = len(included - selected)
    if companion_count:
        companion_wording = 'record is' if companion_count == 1 else 'records are'
        warnings.append(f'{companion_count} additional {companion_wording} included to preserve the selected discrepancies.')
    undated_count = sum(row.get('date') is None for row in entries)
    if undated_count:
        warnings.append(f'{undated_count} records have partial or unknown dates and are kept separate from the dated history.')
    if any(row.get('source_quote_withheld') for row in entries):
        warnings.append('Some original excerpts are withheld by the selected date scope; the permitted recorded values remain visible.')
    kinds = {row['kind'] for row in entries}
    if 'prescription' in kinds:
        warnings.append('Historical prescription records do not establish current medication use.')
    if 'recorded_diagnosis' in kinds:
        warnings.append('Diagnoses are statements recorded in the sources, not diagnoses made by Modus.')
    if 'imaging_text' in kinds:
        warnings.append('Imaging entries reproduce report text; Modus has not interpreted scan images.')
    evidence_sources = [deepcopy(source) for source in view['sources'] if source['id'] in source_ids]
    facts = [deepcopy(row) for row in ordered if row.get('date')]
    undated = [deepcopy(row) for row in ordered if not row.get('date')]
    evidence = {'scope': deepcopy(view['scope']), 'facts': facts, 'undated_facts': undated,
        'sources': evidence_sources, 'conflicts': deepcopy(groups),
        'counts': {'facts': len(ordered), 'sources': len(source_ids), 'conflicts': len(groups),
            'undated_facts': len(undated), 'measurements': sum(row['kind'] == 'measurement' for row in ordered)},
        'projection': 'selected_brief_evidence', 'truncated': False}
    brief = {'format': FORMAT, 'bundle_id': BUNDLE_ID, 'title': request.title, 'owner_note': request.owner_note,
        'scope': deepcopy(view['scope']), 'generated_at': view['scope']['captured_at'], 'reviewed': False,
        'entries': entries, 'sources': sources, 'conflicts': deepcopy(groups), 'warnings': warnings,
        'counts': {'selected': len(selected), 'conflict_companions': companion_count,
            'total': len(ordered), 'sources': len(sources)}, 'history_evidence': evidence}
    encoded = json.dumps(_binding(brief), sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    if len(encoded) > MAX_BRIEF_BYTES:
        raise ValueError('This complete brief exceeds the export size limit. Select fewer records.')
    brief['preview_id'] = 'sha256:' + sha256(encoded).hexdigest()
    return brief


def validate_export(store, request):
    if not isinstance(request, BriefExportRequest):
        request = BriefExportRequest.model_validate(request)
    brief = build_brief(store, request)
    if not compare_digest(brief['preview_id'], request.preview_id):
        raise BriefChangedError('The brief changed after review. Preview and review the updated brief before downloading.')
    brief['reviewed'] = True
    brief['reviewed_at'] = brief['generated_at']
    return brief


def _reviewed(brief):
    if brief.get('reviewed') is not True:
        raise ValueError('A reviewed brief is required for export')


def render_json(brief):
    _reviewed(brief)
    return json.dumps(brief, ensure_ascii=False, indent=2) + '\n'


def render_html(brief):
    """An offline document, with internal citations and no executable content."""
    _reviewed(brief)
    e = lambda value: escape(str(value), quote=True)
    row_citations = {row['id']: row['citation'] for row in brief['entries']}
    parts = ['<!doctype html><html lang="en"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width,initial-scale=1">',
        '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; base-uri \'none\'; form-action \'none\'">',
        '<meta name="referrer" content="no-referrer">',
        f'<title>{e(brief["title"])}</title>',
        '<style>body{font:16px/1.55 system-ui,"Segoe UI",Arial,sans-serif;color:#17212e;background:#f5f7fa;margin:0;padding:40px 20px}main{max-width:900px;margin:auto;background:white;padding:40px;border:1px solid #dce2e9;border-radius:20px}h1{font-size:32px;line-height:1.15;margin:8px 0 16px}h2{font-size:22px;margin-top:32px}h3{font-size:17px;margin:0 0 8px}p{margin:8px 0}small,.meta{color:#4b5d70;font-size:13px}a{color:#0759bb;text-decoration:underline}article{padding:18px 0;border-top:1px solid #dce2e9;break-inside:avoid}blockquote{margin:12px 0;padding:12px 16px;background:#f3f6fa;border-left:3px solid #587ba5}.value,.note,blockquote{white-space:pre-wrap;overflow-wrap:anywhere}.tag{display:inline-block;background:#edf3fc;color:#234e86;padding:2px 7px;border-radius:6px;font-size:12px}.notice{background:#fff8e8;border:1px solid #e9d69a;border-radius:10px;padding:12px 16px}.source-list{padding-left:24px}.source-list li{padding:10px 0;overflow-wrap:anywhere}.source-id{font:11px/1.4 monospace;overflow-wrap:anywhere}footer{margin-top:36px;padding-top:16px;border-top:1px solid #dce2e9;font-size:12px;color:#4b5d70}@page{size:A4;margin:18mm}@media print{body{background:white;padding:0;font-size:10pt}main{border:0;padding:0;max-width:none;border-radius:0}h1{font-size:23pt}h2{font-size:15pt}h3{font-size:12pt}a{color:inherit}footer{font-size:8pt}.meta,small{font-size:9pt}}@media(max-width:600px){body{padding:12px}main{padding:22px}h1{font-size:27px}}</style></head><body><main>',
        '<header><p class="meta">MODUS · RECORD BRIEF</p>', f'<h1>{e(brief["title"])}</h1>',
        '<p>Reviewed compilation of selected records. Original wording and unresolved differences are preserved.</p>',
        f'<p class="meta">Recorded dates: {e("through " + brief["scope"]["as_of"] if brief["scope"]["as_of"] else "all recorded dates")}<br>',
        f'Files available in Modus through {e(brief["scope"]["known_at"])}<br>',
        f'Prepared {e(brief["generated_at"])} · {brief["counts"]["total"]} records · {brief["counts"]["sources"]} sources</p></header>']
    if brief['owner_note']:
        parts += ['<section aria-labelledby="owner-note"><h2 id="owner-note">Your note</h2>',
            '<p class="meta">Written by the owner; separate from source-recorded facts.</p>',
            f'<p class="note">{e(brief["owner_note"])}</p></section>']
    parts += ['<section aria-labelledby="scope-notes"><h2 id="scope-notes">Scope and limits</h2><ul>']
    parts += [f'<li>{e(warning)}</li>' for warning in brief['warnings']]
    parts.append('</ul></section>')
    if brief['conflicts']:
        parts += ['<section class="notice" aria-labelledby="differences"><h2 id="differences">Unresolved differences</h2>',
            '<p>No value has been selected as correct. Whether these records refer to the same specimen is unknown.</p>']
        for group in brief['conflicts']:
            refs = ', '.join(f'<a href="#{row_citations[key]}">{row_citations[key]}</a>' for key in group['fact_ids'])
            reason = 'Different recorded units' if group.get('reason') == 'different_recorded_units' else 'Different recorded numeric values'
            parts.append(f'<p><strong>{e(group["label"])}</strong> · {e(group["date"])}<br>{reason}. Records {refs}.</p>')
        parts.append('</section>')
    for title, dated in [('Dated history', True), ('Dates not fully known', False)]:
        selected = [row for row in brief['entries'] if bool(row.get('date')) == dated]
        if not selected:
            continue
        parts.append(f'<section><h2>{title}</h2>')
        for row in selected:
            recorded_date = f'Recorded {row["occurred_on"]}' if row.get('occurred_on') else 'Date not recorded'
            parts += [f'<article id="{row["citation"]}"><h3>{row["citation"]} · {e(row["label"])}</h3>',
                f'<p class="meta">{e(KIND_LABELS[row["kind"]])} · {e(recorded_date)}',
                (f' · {e(row["facility"])}' if row.get('facility') else '') + '</p>']
            if row['added_for_conflict']:
                parts.append('<p class="tag">Included to preserve a recorded difference</p>')
            value = e(row['value']) + (f' {e(row["unit"])}' if row.get('unit') else '')
            parts.append(f'<p class="value">{value}</p>')
            if row.get('reviewed_fields'):
                fields = ', '.join(row['reviewed_fields'])
                parts.append(f'<p class="meta">Fields edited during record review: {e(fields)}. The excerpt preserves the original wording.</p>')
            if row.get('source_quote_withheld'):
                parts.append('<p class="meta">Original excerpt withheld by the selected date scope.</p>')
            elif row.get('source_quote'):
                parts.append(f'<blockquote>{e(row["source_quote"])}</blockquote>')
            else:
                parts.append('<p class="meta">No source excerpt is recorded.</p>')
            parts.append(f'<p class="meta">Source <a href="#{row["source_citation"]}">{row["source_citation"]}</a>' +
                (f' · page {e(row["page"])}' if row.get('page') else '') + '</p></article>')
        parts.append('</section>')
    parts += ['<section><h2>Sources</h2><ol class="source-list">']
    for source in brief['sources']:
        record_word = 'record' if source['brief_fact_count'] == 1 else 'records'
        parts.append(f'<li id="{source["citation"]}"><strong>{source["citation"]} · {e(source.get("title") or "Untitled source")}</strong><br>' +
            (f'{e(source["provider"])}<br>' if source.get('provider') else '') +
            f'<small>Available in Modus: {e(source["available_at"])}. {source["brief_fact_count"]} {record_word} in this brief.</small><br>' +
            f'<span class="source-id">Source ID: {e(source["id"])}</span></li>')
    parts += ['</ol></section><footer><p>Authored synthetic demonstration. This document records selected source information and owner notes; it provides no medical advice.</p>',
        '<p>Evidence references point within this document. Original files remain in the owner’s Modus history; they are not embedded here.</p>',
        f'<p class="source-id">Content identity: {e(brief["preview_id"])}</p></footer></main></body></html>']
    return ''.join(parts)

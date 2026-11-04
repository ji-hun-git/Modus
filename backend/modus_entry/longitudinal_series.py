"""Paged, source-linked observations with server-authorized comparison edges.

No inferred observations, unit conversion, model calls or persistent writes.
"""
from copy import deepcopy
from decimal import Decimal
import json
import math
from typing import Any, Literal

from pydantic import Field

from modus.record_history_models import date_information, numeric_value
from .models import Strict
from .comparison_rules import POLICY_VERSION, contextual_pair, test_key
from .claim_verification import VerificationContext, make_claim, verify_claim

MAX_EVIDENCE_FACTS = 120
MAX_SERIES_BYTES = 2_000_000


class SeriesEdge(Strict):
    from_id: str
    to_id: str
    status: Literal['comparable', 'not_comparable']
    connectable: bool
    difference: str | None
    unit: str | None
    reason_codes: list[str]
    notes: list[str]


class PlotPoint(Strict):
    fact_id: str
    date: str
    value: float = Field(allow_inf_nan=False)
    unit: str


class ObservationNote(Strict):
    fact_id: str
    reason_codes: list[str]
    notes: list[str]


class SeriesPage(Strict):
    offset: int
    limit: int
    returned: int
    total: int
    next_offset: int | None
    previous_offset: int | None


class SeriesResponse(Strict):
    format: Literal['modus-longitudinal-series-v1']
    snapshot_id: str
    scope: dict[str, Any]
    policy_version: str
    anchor_id: str
    label: str
    kind: Literal['measurement']
    observations: list[dict[str, Any]]
    plot_points: list[PlotPoint]
    observation_notes: list[ObservationNote]
    edges: list[SeriesEdge]
    history_evidence: dict[str, Any]
    page: SeriesPage
    counts: dict[str, int]
    limitations: list[str]


def visible(row):
    return not row.get('value_withheld') and row.get('within_date_scope') is not False


def plot_observation(row, date_count):
    codes, notes = [], []
    def add(code, note):
        codes.append(code)
        notes.append(note)
    if not row.get('date'):
        add('INCOMPLETE_DATE', 'No full recorded date; this record stays outside the time axis.')
    if not row.get('unit'):
        add('UNIT_UNKNOWN', 'No recorded unit; this value stays outside the chart.')
    number = numeric_value(row.get('value'))
    value = None
    if number is None:
        add('QUALIFIED_OR_TEXT_VALUE', 'The recorded value is not an unqualified number; its exact wording is retained.')
    else:
        value = float(number)
        if not math.isfinite(value) or Decimal(str(value)) != Decimal(number):
            add('PLOT_PRECISION_UNSUPPORTED', 'A chart number would lose recorded precision; inspect the exact value instead.')
    point = None if codes else {'fact_id': row['id'], 'date': row['date'], 'value': value, 'unit': row['unit']}
    if row.get('source_quote_withheld') or not (row.get('source_quote') or '').strip():
        add('SOURCE_EXCERPT_UNAVAILABLE', 'The original excerpt is unavailable in this view; connecting comparisons are withheld.')
    if row.get('date') and date_count > 1:
        add('SAME_DATE_MULTIPLE_RECORDS', 'Multiple observations share this date; no single value is selected.')
    return point, {'fact_id': row['id'], 'reason_codes': codes, 'notes': notes}


def build_series(view, snapshot_id, fact_id, offset=0, limit=50):
    if type(offset) is not int or type(limit) is not int or not 0 <= offset <= 100000 or not 1 <= limit <= 50:
        raise ValueError('Choose a valid series page of 1 to 50 observations.')
    verification = VerificationContext(view)
    anchor = verification.facts.get(fact_id)
    if not anchor or not visible(anchor) or anchor['source_id'] not in verification.sources:
        raise ValueError('This result is unavailable in the captured history. Refresh and choose a visible result.')
    if anchor['kind'] != 'measurement':
        raise ValueError('Choose a measurement to explore its recorded series.')
    key = test_key(anchor)
    matching = sorted((row for row in verification.facts.values()
                       if visible(row) and row['source_id'] in verification.sources and test_key(row) == key),
                      key=lambda row: (not bool(row.get('date')), row.get('date') or '', row['id']))
    selected = matching[offset:offset + limit]
    selected_ids = {row['id'] for row in selected}
    evidence_ids = selected_ids | {anchor['id']}
    conflicts = [group for group in view['conflicts'] if evidence_ids.intersection(group['fact_ids'])]
    # A conflict's companions remain inspectable even when pagination separates
    # them. Never serialize a partial conflict as if it were complete.
    evidence_ids.update(identity for group in conflicts for identity in group['fact_ids'])
    if len(evidence_ids) > MAX_EVIDENCE_FACTS:
        raise ValueError('This page and its conflict companions exceed the 120-record evidence limit. Choose a smaller page; no evidence was truncated.')
    if any(identity not in verification.facts or not visible(verification.facts[identity]) or
           verification.facts[identity]['source_id'] not in verification.sources for identity in evidence_ids):
        raise ValueError('Complete conflict evidence is unavailable in this captured view.')
    evidence_rows = [verification.facts[identity] for identity in sorted(evidence_ids)]
    source_ids = {row['source_id'] for row in evidence_rows}
    source_map = {source['id']: source for source in view['sources']}
    observations = [deepcopy(row) for row in selected]
    for row in observations:
        row.setdefault('date_precision', date_information(row.get('occurred_on'))['date_precision'])
    date_counts = verification.comparisons.get(key, {})
    points, annotations = [], []
    for row in observations:
        point, annotation = plot_observation(row, date_counts.get(row.get('date'), 0))
        if point is not None:
            points.append(point)
        annotations.append(annotation)
    plotted = {point['fact_id'] for point in points}
    edges = []
    dated = [row for row in selected if row.get('date')]
    for previous, current in zip(dated, dated[1:]):
        rules = contextual_pair(view, current, previous, context=verification.comparisons)
        if rules['difference'] is not None:
            claim = make_claim(view, [current, previous], difference=rules['difference'])
            if verify_claim(claim, view, context=verification)['status'] != 'SUPPORTED':
                rules = {**rules, 'status': 'not_comparable', 'difference': None,
                         'reason_codes': [*rules['reason_codes'], 'SOURCE_SUPPORT_MISSING'],
                         'notes': [*rules['notes'], 'Original excerpt support is unavailable; no connecting comparison is authorized.']}
        edges.append({'from_id': previous['id'], 'to_id': current['id'],
            'status': rules['status'], 'connectable': rules['difference'] is not None and
                current['id'] in plotted and previous['id'] in plotted,
            'difference': rules['difference'], 'unit': rules['unit'],
            'reason_codes': rules['reason_codes'], 'notes': rules['notes']})
    evidence = {'scope': deepcopy(view['scope']),
        'facts': [deepcopy(row) for row in evidence_rows if row.get('date')],
        'undated_facts': [deepcopy(row) for row in evidence_rows if not row.get('date')],
        'sources': [deepcopy(source_map[identity]) for identity in sorted(source_ids)],
        'conflicts': deepcopy(conflicts),
        'counts': {'facts': len(evidence_rows), 'sources': len(source_ids), 'conflicts': len(conflicts),
            'undated_facts': sum(not row.get('date') for row in evidence_rows),
            'measurements': sum(row['kind'] == 'measurement' for row in evidence_rows)}}
    all_ids = {row['id'] for row in matching}
    result = {'format': 'modus-longitudinal-series-v1', 'snapshot_id': snapshot_id,
        'scope': deepcopy(view['scope']), 'policy_version': POLICY_VERSION, 'anchor_id': anchor['id'],
        'label': anchor['label'], 'kind': 'measurement', 'observations': observations,
        'plot_points': points, 'observation_notes': annotations, 'edges': edges, 'history_evidence': evidence,
        'page': {'offset': offset, 'limit': limit, 'returned': len(selected), 'total': len(matching),
            'next_offset': offset + limit if offset + limit < len(matching) else None,
            'previous_offset': max(0, offset - limit) if offset else None},
        'counts': {'dated': sum(bool(row.get('date')) for row in matching),
            'undated': sum(not row.get('date') for row in matching),
            'sources': len({row['source_id'] for row in matching}),
            'conflicts': sum(bool(all_ids.intersection(group['fact_ids'])) for group in view['conflicts'])},
        'limitations': ['Only reviewed observations in this captured history are included; missing records do not establish missed testing or care.',
            'Connections are authorized only between adjacent observations on this page. They do not establish intermediate measurements or clinical equivalence.',
            'Exact units stay separate. Partial dates and values that cannot be plotted remain available as recorded evidence.']}
    if len(json.dumps(result, ensure_ascii=False).encode()) > MAX_SERIES_BYTES:
        raise ValueError('This series page exceeds the evidence size limit. Choose a smaller page; no content was truncated.')
    return result

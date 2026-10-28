"""Record-only projections and frozen scopes. No clinical computation."""
from collections import defaultdict
from datetime import date
from hashlib import sha256
from typing import Literal
from pydantic import Field
from modus.bundle import identity
from modus.record_models import METRICS, Observation
from modus.record_conflicts import conflicts
from modus.record_retrieval import retrieve_record_evidence
from modus.temporal import instant
from .models import Strict
from .runtime import BUNDLE_ID

SOURCE_FIELDS = ('id', 'title', 'provider', 'date', 'type', 'content', 'synthetic',
    'original_available', 'available_at', 'availability_basis', 'ingested_at', 'sha256', 'extraction_mode')

RECORD_LABELS = {'hba1c': 'Average blood sugar (HbA1c)',
                 'egfr': 'Kidney filtering (eGFR)', 'ldl': 'Cholesterol (LDL)'}


def observation(raw):
    result = Observation.model_validate({k: v for k, v in raw.items() if k in Observation.model_fields}).model_dump(mode='json')
    if result.get('fhir_provenance') is None:
        result.pop('fhir_provenance', None)
    return result


def source(raw):
    result = {k: raw[k] for k in SOURCE_FIELDS if k in raw}
    result.setdefault('original_available', False)
    return result


def disagreement_groups(rows):
    return [{k: group[k] for k in ('id', 'metric', 'date', 'reason', 'observations')} for group in conflicts(rows)]


def view(snapshot, as_of):
    rows = [observation(r) for r in snapshot.observations(as_of)]
    sources = [source(s) for s in snapshot.sources(as_of)]
    groups = disagreement_groups(rows)
    scope = {'as_of': as_of, 'known_at': snapshot.known_at, 'captured_at': snapshot.captured_at}
    scope['scope_id'] = identity({'as_of': as_of, 'known_at': snapshot.known_at,
        'observations': rows, 'sources': sources, 'bundle_id': BUNDLE_ID})
    return {'scope': scope, 'observations': rows, 'sources': sources, 'conflicts': groups,
        'counts': {'measurements': len(rows), 'documents': len(sources), 'disagreements': len(groups)}}


def capture(store, as_of, known_at=None, compare_from=None):
    frozen = store.snapshot()
    after = view(frozen.narrow(known_at or frozen.known_at), as_of)
    if compare_from is None:
        return {'view': after, 'comparison': None}
    before = view(frozen.narrow(compare_from), as_of)
    if before['scope']['known_at'] > after['scope']['known_at']:
        raise ValueError('The earlier availability bound must not follow the later bound')
    before_ids = {r['id'] for r in before['observations']}
    before_groups = {g['id']: {r['id'] for r in g['observations']} for g in before['conflicts']}
    new_conflicts = [g for g in after['conflicts'] if {r['id'] for r in g['observations']} != before_groups.get(g['id'], set())]
    comparison = {'before': before, 'after': after, 'captured_at': frozen.captured_at,
        'added': [r for r in after['observations'] if r['id'] not in before_ids],
        'unchanged_count': sum(r['id'] in before_ids for r in after['observations']), 'new_conflicts': new_conflicts}
    return {'view': after, 'comparison': comparison}


class MetricArgs(Strict):
    metric: Literal['hba1c', 'egfr', 'ldl'] | None = None


class InventoryArgs(MetricArgs):
    offset: int = Field(default=0, ge=0, le=100000)
    limit: int = Field(default=30, ge=1, le=100)


class SelectionArgs(Strict):
    claim_ids: list[str] = Field(max_length=8)


class SearchArgs(Strict):
    query: str = Field(min_length=1, max_length=2000)
    limit: int = Field(default=5, ge=1, le=8, strict=True)


ARGUMENTS = {'record_inventory': InventoryArgs, 'record_conflicts': MetricArgs,
             'compare_record_snapshots': MetricArgs, 'search_record_evidence': SearchArgs,
             'select_claims': SelectionArgs}
DESCRIPTIONS = {'record_inventory': 'Read recorded facts and document/measurement counts in the fixed scope.',
    'record_conflicts': 'Inspect same-day different recorded values or units; specimen equivalence is unknown.',
    'compare_record_snapshots': 'Compare the already bound availability views, optionally filtering derived counts and added evidence by metric; measurement dates and original views stay fixed.',
    'search_record_evidence': 'Retrieve bounded raw recorded facts by source words or supported measurement names/codes using lexical ranking and versioned ontology lookup. Uses only the frozen view. Exact method/code requests require matching source provenance; inspect warnings for omitted conflict companions. No diagnosis, interpretation, ranges, unit conversion or scope changes.',
    'select_claims': 'Finish using exact claim IDs already returned. Empty if unsupported.'}


def claim(key, text, evidence, tool, status='observed'):
    return {'id': key, 'text': text, 'evidence_ids': evidence, 'tool_name': tool, 'status': status}


def conflict_text(group):
    # Exact printed units and stored numbers; equality does not merge source identities.
    values = list(dict.fromkeys((row['value'], row['unit']) for row in group['observations']))
    displayed = '; '.join(f'{value} {unit}' for value, unit in values[:6])
    if len(values) > 6:
        displayed += f'; and {len(values) - 6} other recorded values'
    return (f"On {group['date']}, {RECORD_LABELS[group['metric']]} has different recorded values: "
            f'{displayed}. All affected records are retained; specimen equivalence is unknown.')


def no_conflict_text(current, rows, metric):
    scope = current['scope']
    label = RECORD_LABELS[metric] + ' ' if metric else ''
    bounds = (f"measured through {scope['as_of']}, using records available by {scope['known_at']}")
    if not rows:
        return f'No recorded {label}measurements are available to compare in this view ({bounds}).'
    return (f'No same-day disagreement was found among {len(rows)} recorded {label}measurements '
            f'in this view ({bounds}). Later arrivals are outside this captured view.')


def dispatch(context, name, arguments):
    if name not in ARGUMENTS or name == 'select_claims':
        raise ValueError('Tool not permitted')
    args = ARGUMENTS[name].model_validate(arguments).model_dump()
    current = context['view']
    if name == 'search_record_evidence':
        retrieved = retrieve_record_evidence(current, args['query'], args['limit'])
        items = []
        query_id = sha256((args['query'] + '\0' + str(args['limit'])).encode('utf-8')).hexdigest()[:12]
        for hit in retrieved['hits']:
            context_only = hit['retrieved_because'] == 'conflict_companion'
            prefix = 'Conflicting source context: ' if context_only else ''
            text = (f"{prefix}{METRICS[hit['metric']]['label']}: {hit['value']} {hit['unit']}, "
                    f"measured {hit['date']}.")
            limited_conflict = any(hit['observation_id'] in warning['included_observation_ids'] for warning in retrieved['warnings'])
            if limited_conflict:
                text += ' Other conflicting values are outside this retrieval result; no value is chosen as correct.'
            items.append(claim('retrieval-' + query_id + '-' + hit['observation_id'], text,
                               [hit['observation_id'], hit['source_id']], name,
                               'conflict' if hit.get('conflict_ids') or context_only or limited_conflict else 'observed'))
        return {**retrieved, 'claims': items}
    if name == 'record_inventory':
        rows = [r for r in current['observations'] if args['metric'] is None or r['metric'] == args['metric']]
        page = rows[args['offset']:args['offset'] + args['limit']]
        documents = len({r['source_id'] for r in rows})
        counts = {'measurements': len(rows), 'documents': documents}
        key = 'inventory-' + (args['metric'] or 'all')
        return {'scope': current['scope'], 'observations': page, 'counts': counts,
            'next_offset': args['offset'] + len(page) if args['offset'] + len(page) < len(rows) else None,
            'claims': [claim(key, f'This view contains {len(rows)} recorded measurements from {documents} documents.',
                             [r['id'] for r in rows], name)]}
    if name == 'record_conflicts':
        groups = [g for g in current['conflicts'] if args['metric'] is None or g['metric'] == args['metric']]
        items = [claim('disagreement-' + g['id'],
            conflict_text(g),
            [r['id'] for r in g['observations']], name, 'conflict') for g in groups]
        if not items:
            rows = [r for r in current['observations'] if args['metric'] is None or r['metric'] == args['metric']]
            items = [claim('disagreement-none-' + (args['metric'] or 'all'), no_conflict_text(current, rows, args['metric']),
                           [r['id'] for r in rows], name)]
        return {'scope': current['scope'], 'conflicts': groups, 'claims': items}
    comparison = context['comparison']
    if comparison is None:
        raise ValueError('Compare two availability views before asking what arrived later')
    metric = args['metric']
    if metric is not None:
        before_ids = {r['id'] for r in comparison['before']['observations'] if r['metric'] == metric}
        comparison = {**comparison,
            'added': [r for r in comparison['added'] if r['metric'] == metric],
            'unchanged_count': sum(r['metric'] == metric and r['id'] in before_ids for r in comparison['after']['observations']),
            'new_conflicts': [g for g in comparison['new_conflicts'] if g['metric'] == metric]}
    label = f'recorded {metric} measurements' if metric else 'recorded measurements'
    return {'comparison': comparison, 'claims': [claim('arrival-count' + ('-' + metric if metric else ''),
        f"{len(comparison['added'])} {label} became available between these views; {comparison['unchanged_count']} were already present. The measurement cutoff is unchanged.",
        [r['id'] for r in comparison['added']], name)]}

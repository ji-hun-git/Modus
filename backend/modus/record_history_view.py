"""Frozen factual timeline projections; no interpretation or storage capability."""
from collections import defaultdict
from copy import deepcopy
from datetime import date
from decimal import Decimal
from hashlib import sha256
import json

from .record_history_models import date_information, numeric_value, temporal_original_allowed
from .record_models import METRICS
from .record_units import normalize_recorded_value
from .temporal import instant


def _legacy_fact(observation, source):
    return {
        'id': observation['id'], 'source_id': source['id'], 'observation_id': observation['id'],
        'kind': 'measurement', 'label': METRICS[observation['metric']]['label'],
        'value': str(observation['value']), 'unit': observation['unit'],
        'occurred_on': observation['date'], 'date': observation['date'], 'date_precision': 'day',
        'facility': source.get('provider'), 'source_quote': observation.get('source_span'),
        'page': observation.get('page'), 'bbox': None, 'extractor': source.get('extraction_mode', 'authored_seed'),
        'available_at': source['available_at'], 'availability_basis': source.get('availability_basis'),
        'reviewer': source.get('review', {}).get('reviewer'),
        'reviewed_at': source.get('review', {}).get('reviewed_at'),
        'reviewed_fields': observation.get('reviewed_fields', []), 'legacy_projection': True,
    }


def _age(day, dob):
    if not day or not dob or day < dob:
        return None
    event, birth = date.fromisoformat(day), date.fromisoformat(dob)
    return event.year - birth.year - ((event.month, event.day) < (birth.month, birth.day))


def _conflicts(facts):
    groups = defaultdict(list)
    for fact in facts:
        if fact['kind'] == 'measurement' and fact['date']:
            groups[(fact['label'], fact['date'])].append(fact)
    disagreements = []
    for (label, day), group in groups.items():
        units = {row['unit'] for row in group}
        mixed_units = len(units) > 1
        comparable = [row for row in group if row['numeric_value'] is not None]
        numeric_difference = not mixed_units and len({Decimal(row['numeric_value']) for row in comparable}) > 1
        if mixed_units or numeric_difference:
            selected = group if mixed_units else comparable
            identity = sha256(json.dumps([label, day], ensure_ascii=False).encode()).hexdigest()[:20]
            disagreements.append({'id': 'history-conflict-' + identity, 'kind': 'measurement',
                'label': label, 'unit': None if mixed_units else next(iter(units)), 'date': day,
                'fact_ids': [row['id'] for row in selected], 'source_ids': sorted({row['source_id'] for row in selected}),
                'values': [row['value'] for row in selected], 'units': [row['unit'] for row in selected], 'resolution': 'unresolved',
                'reason': 'different_recorded_units' if mixed_units else 'different_numeric_values',
                'comparison_basis': 'different_recorded_units_not_numerically_compared' if mixed_units else 'same_exact_recorded_label_unit_and_day',
                'specimen_equivalence': 'unknown'})
    return sorted(disagreements, key=lambda item: (item['date'], item['label'], item['unit'] or ''))


def history_view(store, as_of=None, known_at=None):
    if isinstance(as_of, date):
        as_of = as_of.isoformat()
    if as_of is not None and (not isinstance(as_of, str) or date_information(as_of)['date'] is None):
        raise ValueError('History cutoff must be an exact ISO date or null')
    with store.connect() as db:
        db.execute('BEGIN IMMEDIATE')
        captured = instant(store.clock())
        cutoff = min(instant(known_at), captured) if known_at is not None else captured
        sources = {row['id']: json.loads(row['data']) for row in db.execute('SELECT id,data FROM sources WHERE available_at<=?', (cutoff,))}
        generic = [json.loads(row[0]) for row in db.execute(
            'SELECT h.data FROM history_facts h JOIN sources s ON s.id=h.source_id WHERE h.available_at<=? AND s.available_at<=? ORDER BY h.date,h.id', (cutoff, cutoff))]
        legacy = [json.loads(row[0]) for row in db.execute(
            'SELECT o.data FROM observations o JOIN sources s ON s.id=o.source_id WHERE s.available_at<=? ORDER BY o.date,o.id', (cutoff,))]
        originals = {row[0] for row in db.execute('SELECT id FROM documents')}
        profile_row = db.execute('SELECT data FROM history_profiles WHERE updated_at<=? ORDER BY updated_at DESC,id DESC LIMIT 1', (cutoff,)).fetchone()
        profile = json.loads(profile_row['data']) if profile_row else {'date_of_birth': None, 'updated_at': None, 'storage': 'local'}
    bridge_ids = {fact.get('observation_id') for fact in generic}
    all_facts = generic + [_legacy_fact(row, sources[row['source_id']]) for row in legacy if row['id'] not in bridge_ids]
    facts, undated = [], []
    for original in all_facts:
        fact = deepcopy(original)
        if as_of is not None and fact['date'] is not None and fact['date'] > as_of:
            continue
        source = sources[fact['source_id']]
        allowed = temporal_original_allowed(source, as_of)
        fact['source_quote_withheld'] = not allowed
        fact['value_withheld'] = not allowed and (fact['date'] is None or fact['kind'] != 'measurement')
        if not allowed:
            fact.update(source_quote=None, bbox=None)
            fact.pop('source_proposal', None)
        if fact['value_withheld']:
            fact['value'] = None
        fact['original_available'] = allowed and source['id'] in originals
        fact['numeric_value'] = numeric_value(fact['value']) if fact['kind'] == 'measurement' else None
        fact['normalization'] = normalize_recorded_value(fact['label'], fact['value'], fact['unit']) if fact['kind'] == 'measurement' and fact['value'] is not None else None
        fact['age_years'] = _age(fact['date'], profile['date_of_birth'])
        fact['within_date_scope'] = fact['date'] is not None or as_of is None
        (facts if fact['date'] is not None else undated).append(fact)
    facts.sort(key=lambda row: (row['date'], row['id']), reverse=True)
    undated.sort(key=lambda row: (row['available_at'], row['id']), reverse=True)
    visible_ids = {fact['source_id'] for fact in facts + undated}
    visible_sources = []
    for sid in sorted(visible_ids):
        source = sources[sid]
        allowed = temporal_original_allowed(source, as_of)
        visible_sources.append({key: deepcopy(source.get(key)) for key in (
            'id', 'title', 'type', 'provider', 'date', 'available_at', 'availability_basis')} | {
            'historical_projection': not allowed, 'original_available': allowed and sid in originals,
            'fact_count': sum(fact['source_id'] == sid for fact in facts + undated)})
    disagreements = _conflicts(facts)
    identity = {'as_of': as_of, 'known_at': cutoff, 'captured_at': captured,
                'facts': facts, 'undated_facts': undated, 'sources': visible_sources, 'profile': profile}
    return {'scope': {'as_of': as_of, 'known_at': cutoff, 'captured_at': captured,
                     'scope_id': 'sha256:' + sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()},
            'facts': facts, 'undated_facts': undated, 'sources': visible_sources,
            'conflicts': disagreements, 'profile': profile,
            'counts': {'facts': len(facts) + len(undated), 'dated_facts': len(facts), 'undated_facts': len(undated), 'sources': len(visible_sources),
                       'documents': len(visible_sources), 'undated': len(undated),
                       'measurements': sum(fact['kind'] == 'measurement' for fact in facts), 'conflicts': len(disagreements)}}

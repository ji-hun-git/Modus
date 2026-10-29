"""Read-only tools over a captured, source-preserving whole-history projection."""
from collections import Counter
from copy import deepcopy
from decimal import Decimal
from hashlib import sha256
import json
import re

from pydantic import Field, field_validator

from modus.record_history_models import FactKind
from modus.record_history_view import history_views
from .models import Strict


KIND_LABELS = {
    'measurement': 'measurement', 'encounter': 'visit record',
    'recorded_diagnosis': 'diagnosis as recorded', 'procedure': 'procedure record',
    'prescription': 'prescription record', 'vaccination': 'vaccination record',
    'imaging_text': 'imaging report text', 'recorded_text': 'recorded text',
}
FACT_FIELDS = (
    'id', 'source_id', 'kind', 'label', 'value', 'unit', 'occurred_on', 'date',
    'date_precision', 'facility', 'source_quote', 'source_quote_withheld',
    'value_withheld', 'page', 'bbox', 'available_at', 'availability_basis',
    'reviewed_fields', 'original_available', 'within_date_scope',
    'revision_id', 'previous_revision_id', 'first_available_at',
)
SOURCE_FIELDS = (
    'id', 'title', 'type', 'provider', 'date', 'available_at', 'availability_basis',
    'historical_projection', 'original_available', 'fact_count',
)
MAX_TOOL_BYTES = 24000


def safe_view(view):
    """Do not send profile, age, reviewer identity or original proposals to tools."""
    result = {key: deepcopy(view[key]) for key in ('scope', 'counts', 'conflicts')}
    for key in ('facts', 'undated_facts'):
        result[key] = [{field: deepcopy(row[field]) for field in FACT_FIELDS if field in row}
                       for row in view[key]]
    result['sources'] = [{field: deepcopy(row[field]) for field in SOURCE_FIELDS if field in row}
                         for row in view['sources']]
    return result


def capture_history(store, as_of=None, known_at=None, compare_from=None):
    bounds = (known_at,) if compare_from is None else (known_at, compare_from)
    captured = history_views(store, as_of, bounds)
    after = safe_view(captured[0])
    if compare_from is None:
        return {'view': after, 'comparison': None}
    before = safe_view(captured[1])
    if before['scope']['known_at'] > after['scope']['known_at']:
        raise ValueError('The earlier availability bound must not follow the later bound')
    before_ids = {row['id'] for row in all_facts(before)}
    before_rows = {row['id']: row for row in all_facts(before)}
    after_ids = {row['id'] for row in all_facts(after)}
    updated = [{'before': before_rows[row['id']], 'after': row} for row in all_facts(after)
               if row['id'] in before_rows and row.get('revision_id', row['id']) != before_rows[row['id']].get('revision_id', row['id'])]
    updated_ids = {item['after']['id'] for item in updated}
    before_groups = {group['id']: set(group['fact_ids']) for group in before['conflicts']}
    added = [row for row in all_facts(after) if row['id'] not in before_ids]
    return {'view': after, 'comparison': {
        'before': before, 'after': after, 'added': added,
        'updated': updated, 'removed_from_scope': [row for row in all_facts(before) if row['id'] not in after_ids],
        'unchanged_count': sum(row['id'] in before_ids and row['id'] not in updated_ids for row in all_facts(after)),
        'new_conflicts': [group for group in after['conflicts']
                          if set(group['fact_ids']) != before_groups.get(group['id'], set()) or updated_ids.intersection(group['fact_ids'])],
        'captured_at': after['scope']['captured_at'],
    }}


class FilterArgs(Strict):
    kind: FactKind | None = None
    label: str | None = Field(default=None, min_length=1, max_length=200, strict=True)

    @field_validator('label')
    @classmethod
    def nonblank_label(cls, value):
        if value is not None and not value.strip():
            raise ValueError('A label cannot be blank')
        return value


class InventoryArgs(FilterArgs):
    offset: int = Field(default=0, ge=0, le=100000, strict=True)
    limit: int = Field(default=5, ge=1, le=8, strict=True)


class SearchArgs(Strict):
    query: str = Field(min_length=1, max_length=2000, strict=True)
    kind: FactKind | None = None
    limit: int = Field(default=5, ge=1, le=8, strict=True)

    @field_validator('query')
    @classmethod
    def nonblank_query(cls, value):
        if not value.strip():
            raise ValueError('A query cannot be blank')
        return value


ARGUMENTS = {
    'history_inventory': InventoryArgs,
    'search_history_evidence': SearchArgs,
    'history_conflicts': FilterArgs,
    'compare_history_snapshots': FilterArgs,
}
DESCRIPTIONS = {
    'history_inventory': 'List and count recorded facts across all eight kinds in the captured history. Optional kind and exact case-insensitive label filters; bounded page. Records are source statements, not current medication use or new diagnoses.',
    'search_history_evidence': 'Find literal recorded names, text or source words across all eight kinds. Quoted phrases and source:"title" narrow matches. No inferred medical relationships, interpretation or scope changes. Empty means no supported match, not missing care.',
    'history_conflicts': 'Inspect only backend-declared same-day measurement discrepancies. Optional kind/exact-label filters. Both values remain recorded; sample equivalence is unknown. Other record kinds have no implemented conflict detector.',
    'compare_history_snapshots': 'Count newly available records of any kind between the already bound history views. Dates and availability remain server-owned. An old prescription appearing now does not establish current use, adherence, treatment effect or missed care.',
}


def all_facts(view):
    return view['facts'] + view['undated_facts']


def available_fact(row):
    return not row.get('value_withheld') and row.get('within_date_scope', True)


def matches_filter(row, args):
    return ((args.get('kind') is None or row['kind'] == args['kind']) and
            (args.get('label') is None or row['label'].casefold() == args['label'].casefold()))


def claim(key, text, evidence, tool, status='observed'):
    return {'id': key, 'text': text, 'evidence_ids': list(dict.fromkeys(evidence)),
            'tool_name': tool, 'status': status}


def scope_text(scope):
    occurrence = f"recorded through {scope['as_of']}" if scope['as_of'] else 'all recorded dates'
    return f"{occurrence}; available in Modus by {scope['known_at']}"


def fact_claim(row, tool, prefix):
    label = json.dumps(row['label'], ensure_ascii=False)
    recorded_date = f"recorded date {row['occurred_on']}" if row.get('occurred_on') else 'date not recorded'
    if row.get('content_omitted'):
        text = (f"Recorded {KIND_LABELS[row['kind']]} {label}; {recorded_date}. "
                'The complete recorded value and excerpt exceed this tool response budget; inspect the source-linked record for their text.')
        return claim(prefix + '-' + row['id'], text, [row['id'], row['source_id']], tool)
    value = json.dumps(row['value'], ensure_ascii=False)
    unit = f" {row['unit']}" if row.get('unit') else ''
    suffix = ''
    if row['kind'] == 'prescription':
        suffix = ' This historical prescription record does not establish current medication use.'
    elif row['kind'] == 'recorded_diagnosis':
        suffix = ' This is the source-recorded statement, not a diagnosis made by Modus.'
    elif row['kind'] == 'imaging_text':
        suffix = ' This is recorded report text, not an interpretation of scan images.'
    if row.get('previous_revision_id'):
        suffix += f" This saved value was corrected in Modus at {row['available_at']}; original source wording is retained."
    text = f"Recorded {KIND_LABELS[row['kind']]} {label}: {value}{unit}; {recorded_date}.{suffix}"
    return claim(prefix + '-' + row['id'], text, [row['id'], row['source_id']], tool)


def bounded_facts(rows, limit):
    page, size = [], 0
    for row in rows[:limit]:
        row = deepcopy(row)
        length = len(json.dumps(row, ensure_ascii=False).encode('utf-8'))
        # Never cut a quoted value mid-sentence or let one long record consume
        # the model's entire context. The UI resolves IDs to complete records.
        if length > MAX_TOOL_BYTES:
            row.update(value=None, source_quote=None, content_omitted=True,
                       content_omitted_reason='bounded_tool_response')
            length = len(json.dumps(row, ensure_ascii=False).encode('utf-8'))
        if page and size + length > MAX_TOOL_BYTES:
            break
        page.append(row)
        size += length
    return page


def evidence(view, rows):
    ids = {row['source_id'] for row in rows}
    return {'scope': deepcopy(view['scope']), 'facts': rows,
            'sources': [deepcopy(source) for source in view['sources'] if source['id'] in ids]}


def content_warning(rows):
    return (['Some long recorded values and excerpts are omitted from this bounded response; open their source-linked records for the complete text.']
            if any(row.get('content_omitted') for row in rows) else [])


# Literal matching strips only request grammar. Medical terms are not expanded.
STOP_WORDS = set('a an and any are as at available be by can containing contains could do does entries entry evidence find for from give has have history i in is it list look me mentioning mentions mention my of on or please record recorded records report reports result results retrieve search show source sources that the their these this to up value values was were what which with would you your 기록 기록을 내 나의 찾아줘 찾아주세요 보여줘 보여주세요'.split())
KIND_REQUEST_WORDS = {
    'measurement': {'measurement', 'measurements', '측정', '측정값'},
    'encounter': {'encounter', 'encounters', 'visit', 'visits', '방문', '진료'},
    'recorded_diagnosis': {'diagnosis', 'diagnoses', '진단'},
    'procedure': {'procedure', 'procedures', '시술', '수술'},
    'prescription': {'prescription', 'prescriptions', '처방'},
    'vaccination': {'vaccination', 'vaccinations', '예방접종', '접종'},
    'imaging_text': {'imaging', '영상'},
    'recorded_text': {'text', 'texts', '문서'},
}


def _tokens(text):
    return re.findall(r"[\w]+", text.casefold(), re.UNICODE)


def search_rows(view, args):
    query = args['query']
    if query.count('"') % 2:
        return [], ['Unclosed quoted phrase; no records were selected.']
    source_phrases, phrases = [], []
    pattern = re.compile(r'(?:(source|title|document|from)\s*:?\s*)?(?:"([^"]+)"|(?<!\w)\x27([^\x27]+)\x27(?!\w))', re.I)
    def remove_phrase(match):
        (source_phrases if match[1] else phrases).append((match[2] or match[3]).casefold())
        return ' '
    remaining = pattern.sub(remove_phrase, query)
    dates = re.findall(r'(?<!\w)(?:19|20)\d{2}(?:-\d{2}(?:-\d{2})?)?(?!\w)', remaining)
    for day in dates:
        remaining = remaining.replace(day, ' ')
    grammar = STOP_WORDS | KIND_REQUEST_WORDS.get(args.get('kind'), set())
    terms = [word for word in _tokens(remaining) if word not in grammar]
    sources = {source['id']: source for source in view['sources']}
    if not terms and not phrases and not source_phrases and not dates:
        return [], ['No literal search terms were supplied; use the inventory tool to list records.']
    hits = []
    for row in all_facts(view):
        if not available_fact(row) or not matches_filter(row, args):
            continue
        source = sources[row['source_id']]
        if source_phrases and not all(phrase in (source.get('title') or '').casefold() for phrase in source_phrases):
            continue
        occurred = row.get('occurred_on') or ''
        if dates and (row.get('date_precision') not in {'day', 'month', 'year'} or
                      not all(occurred.startswith(day) for day in dates)):
            continue
        permitted_quote = '' if row.get('source_quote_withheld') else row.get('source_quote') or ''
        text = ' '.join(str(value) for value in (
            row['label'], row['value'], row.get('unit') or '', row.get('facility') or '',
            permitted_quote, source.get('title') or '', source.get('provider') or '',
        )).casefold()
        if phrases and not all(phrase in text for phrase in phrases):
            continue
        words = set(_tokens(text))
        if terms and not all(word in words for word in terms):
            continue
        label_words = set(_tokens(row['label']))
        score = sum(3 if word in label_words else 1 for word in terms) + 2 * len(phrases)
        hits.append((score, row))
    hits.sort(key=lambda item: (item[0], item[1].get('date') or '', item[1]['id']), reverse=True)
    return [row for _, row in hits], []


def dispatch(context, name, arguments):
    if name not in ARGUMENTS:
        raise ValueError('Tool not permitted')
    args = ARGUMENTS[name].model_validate(arguments).model_dump()
    view = context['view']
    key = 'history-' + sha256(json.dumps([name, args, view['scope']['scope_id']], sort_keys=True).encode()).hexdigest()[:16]
    rows = [row for row in all_facts(view) if matches_filter(row, args)]
    visible = [row for row in rows if available_fact(row)]
    withheld = len(rows) - len(visible)
    if name == 'history_inventory':
        page = bounded_facts(visible[args['offset']:], args['limit'])
        count = len(visible)
        more = args['offset'] + len(page) < count
        documents = len({row['source_id'] for row in visible})
        text = (f"{count} matching {'record' if count == 1 else 'records'} in {documents} "
                f"{'document' if documents == 1 else 'documents'} ({scope_text(view['scope'])}). "
                f"Showing {len(page)} of {count}.")
        if withheld:
            text += f' {withheld} additional matching records are withheld by the selected occurrence cutoff.'
        if more:
            text += ' More matching records are available in the next page.'
        warnings = content_warning(page)
        if warnings:
            text += ' ' + ' '.join(warnings)
        result = evidence(view, page)
        return {**result, 'counts': {'facts': count, 'documents': len({row['source_id'] for row in visible}),
                    'by_kind': dict(Counter(row['kind'] for row in visible))},
                'withheld_count': withheld, 'next_offset': args['offset'] + len(page) if more else None,
                'truncated': more or bool(warnings), 'warnings': warnings,
                'required_claim_ids': [key + '-count'] if more or warnings or withheld else [],
                'claims': [claim(key + '-count', text, [row['id'] for row in page], name)] +
                    [fact_claim(row, name, key) for row in page]}
    if name == 'search_history_evidence':
        found, warnings = search_rows(view, args)
        page = bounded_facts(found, args['limit'])
        ids = {row['id'] for row in page}
        conflict_ids = [group['id'] for group in view['conflicts'] if ids.intersection(group['fact_ids'])]
        if len(page) < len(found):
            warnings.append('More literal matches exist than are shown; narrow the search or inspect the record list.')
        if conflict_ids:
            warnings.append('Some matches belong to recorded discrepancies. This search does not resolve them; inspect history_conflicts for all matching discrepancy groups.')
        omitted = content_warning(page)
        warnings.extend(omitted)
        claims = [fact_claim(row, name, key) for row in page]
        if not claims:
            claims = [claim(key + '-empty', f"No visible recorded fact matched this literal search ({scope_text(view['scope'])}). This does not establish that care was missed or that a condition is absent.", [], name)]
        if warnings:
            claims.insert(0, claim(key + '-limits', f"Showing {len(page)} of {len(found)} literal matching records. " + ' '.join(warnings),
                                   [row['id'] for row in page], name))
        return {**evidence(view, page), 'method': 'literal_terms_and_phrases_v1',
                'match_count': len(found), 'truncated': len(page) < len(found) or bool(omitted),
                'warnings': warnings, 'conflict_ids': conflict_ids,
                'required_claim_ids': [key + '-limits'] if warnings else [], 'claims': claims}
    if name == 'history_conflicts':
        groups = [group for group in view['conflicts'] if
                  (args['kind'] is None or args['kind'] == 'measurement') and
                  (args['label'] is None or group['label'].casefold() == args['label'].casefold())]
        groups = [group for group in groups if set(group['fact_ids']).intersection(row['id'] for row in visible)]
        selected, candidates = [], []
        indexed = {row['id']: row for row in visible}
        for group in groups:
            members = [indexed[fact_id] for fact_id in group['fact_ids'] if fact_id in indexed]
            if len(candidates) + min(2, len(members)) > 8:
                break
            selected.append(group)
            # Reserve an unlike representative before filling the remaining
            # places, so a long group does not hide all discrepant values.
            first = members[0]
            other = next((row for row in members[1:] if row['unit'] != first['unit'] or
                          (group['reason'] == 'different_numeric_values' and Decimal(row['value']) != Decimal(first['value']))), None)
            ordered = [first] + ([other] if other else [])
            ordered += [row for row in members if row['id'] not in {value['id'] for value in ordered}]
            candidates.extend(ordered[:8-len(candidates)])
        ids = {fact_id for group in selected for fact_id in group['fact_ids']}
        page = bounded_facts(candidates, 8)
        # Only emit groups for which the bounded response carries evidence.
        selected = [group for group in selected if set(group['fact_ids']).intersection(row['id'] for row in page)]
        included = {row['id'] for row in page}
        compact = [{field: deepcopy(group[field]) for field in ('id', 'kind', 'label', 'date', 'reason', 'specimen_equivalence')} |
                   {'fact_ids': [fact_id for fact_id in group['fact_ids'] if fact_id in included],
                    'total_records': len(group['fact_ids'])} for group in selected]
        claims = [claim(key + '-' + group['id'],
                        f"{len(group['fact_ids'])} measurement records named {json.dumps(group['label'], ensure_ascii=False)} on {group['date']} have different recorded units or numeric values. All remain separate; specimen equivalence is unknown and no value is selected as correct.",
                        [fact_id for fact_id in group['fact_ids'] if fact_id in included], name, 'conflict') for group in selected]
        if not claims:
            claims = [claim(key + '-none', f"No backend-declared measurement discrepancy matches this filter ({scope_text(view['scope'])}). Conflict detection does not establish consistency of prescriptions, diagnoses or other text records.", [], name)]
        omitted = content_warning(page)
        truncated = len(groups) > len(selected) or len(page) < len(ids) or bool(omitted)
        warnings = (['Only part of the discrepancy evidence is shown; narrow the exact-label filter.'] if truncated else []) + omitted
        if warnings:
            claims.insert(0, claim(key + '-limits', f"This view has {len(groups)} matching discrepancy groups; this response shows {len(selected)} groups and {len(page)} records. " + ' '.join(warnings),
                                   [row['id'] for row in page], name, 'conflict'))
        return {**evidence(view, page), 'conflicts': compact, 'group_count': len(groups),
                'truncated': truncated, 'warnings': warnings,
                'required_claim_ids': [key + '-limits'] if warnings else [], 'claims': claims}
    pair = context['comparison']
    if pair is None:
        raise ValueError('Compare two availability views before asking what arrived later')
    before = [row for row in all_facts(pair['before']) if matches_filter(row, args) and available_fact(row)]
    after = [row for row in all_facts(pair['after']) if matches_filter(row, args) and available_fact(row)]
    before_ids = {row['id'] for row in before}
    added = [row for row in after if row['id'] not in before_ids]
    before_rows = {row['id']: row for row in before}
    updated = [row for row in after if row['id'] in before_rows and row.get('revision_id', row['id']) != before_rows[row['id']].get('revision_id', row['id'])]
    updated_ids = {row['id'] for row in updated}
    removed = [row for row in before if row['id'] not in {item['id'] for item in after}]
    page = bounded_facts(added + updated, 5)
    count = sum(row['id'] in before_ids and row['id'] not in updated_ids for row in after)
    text = (f"{len(added)} matching records became available between {pair['before']['scope']['known_at']} and "
            f"{pair['after']['scope']['known_at']}; {len(updated)} saved records were corrected, {count} were unchanged, "
            f"and {len(removed)} left the selected date or label scope. The occurrence cutoff is unchanged. "
            f"Showing {len(page)} added or corrected records. This describes changes to records in Modus, not changes in health or current medication use.")
    warnings = content_warning(page)
    if len(page) < len(added) + len(updated):
        warnings.insert(0, 'More newly available matching records exist than are shown; narrow the exact-label filter or inspect the record list.')
    if warnings:
        text += ' ' + ' '.join(warnings)
    return {**evidence(view, page), 'comparison': {'before': deepcopy(pair['before']['scope']),
                'after': deepcopy(pair['after']['scope']), 'captured_at': pair['captured_at']},
            'added_count': len(added), 'updated_count': len(updated), 'removed_from_scope_count': len(removed), 'unchanged_count': count,
            'truncated': len(page) < len(added) + len(updated) or bool(warnings), 'warnings': warnings,
            'required_claim_ids': [key + '-count'] if warnings else [],
            'claims': [claim(key + '-count', text, [row['id'] for row in page], name)] +
                [fact_claim(row, name, key) for row in page]}

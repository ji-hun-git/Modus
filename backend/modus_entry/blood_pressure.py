"""Exact, read-only blood-pressure lookup. No clinical ranges or interpretation."""
from datetime import datetime, timezone
from decimal import Decimal
import re
from typing import Literal

from pydantic import Field
from .models import Strict

NUMBER = r'[0-9]{1,6}(?:\.[0-9]{1,3})?'
COMPONENT = r'systolic|diastolic|top number|bottom number'
LABEL = r'blood pressure|bp'
SUBJECT = rf'(?:(?P<before>{COMPONENT}) )?(?:{LABEL})(?: (?P<after>{COMPONENT}))?'
QUESTION = re.compile(
    rf'(?:when did i last have|find (?:my )?last|show (?:my )?last) {SUBJECT} '
    rf'(?:(?:reading )?(?:of|at|equal to) )?(?P<value>{NUMBER})(?: mmhg)?[?.!]*', re.I)
ALTERNATE = re.compile(
    rf'when was my {SUBJECT} last (?P<value>{NUMBER})(?: mmhg)?[?.!]*', re.I)
COMPONENTS = {'systolic': 'systolic', 'top number': 'systolic',
              'diastolic': 'diastolic', 'bottom number': 'diastolic'}
NAMES = {'systolic': 'top number (systolic)', 'diastolic': 'bottom number (diastolic)'}
ALIASES = {
    'systolic': {'systolic', 'sbp', 'systolic blood pressure', 'blood pressure systolic',
                 'systolic bp', 'bp systolic', '수축기 혈압', '수축기혈압'},
    'diastolic': {'diastolic', 'dbp', 'diastolic blood pressure', 'blood pressure diastolic',
                  'diastolic bp', 'bp diastolic', '이완기 혈압', '이완기혈압'},
}
PAIRED = {'blood pressure', 'bp', '혈압'}


class LastBloodPressureArgs(Strict):
    component: Literal['systolic', 'diastolic']
    value: str = Field(pattern=rf'^{NUMBER}$', strict=True)


def parse_question(message):
    """Full-match supported wording; never discard extra filters or qualifiers."""
    text = ' '.join(message.lower().split())
    match = QUESTION.fullmatch(text) or ALTERNATE.fullmatch(text)
    if not match:
        return None
    parts = {COMPONENTS[x] for x in (match['before'], match['after']) if x}
    if len(parts) > 1:
        return None
    return {'component': next(iter(parts), None), 'value': match['value']}


def clarification(parsed):
    value = parsed['value']
    return {'kind': 'blood_pressure_component',
            'question': f'Do you mean {value} as the top number (systolic) or the bottom number (diastolic)?',
            'choices': [{'label': NAMES[part].capitalize(),
                         'message': f'When did I last have {part} blood pressure of {value} mmHg?'}
                        for part in NAMES]}


def _reading(row, component):
    """Return (is relevant, exact decimal or None). Unit must be explicit."""
    label = ' '.join(row['label'].casefold().split())
    if row['kind'] != 'measurement' or label not in ALIASES[component] | PAIRED:
        return False, None
    if (row.get('unit') or '').strip().casefold() not in {'mmhg', 'mm hg', 'mm[hg]'}:
        return True, None
    value = (row.get('value') or '').strip()
    if label in PAIRED:
        pair = re.fullmatch(rf'({NUMBER})\s*/\s*({NUMBER})', value)
        return True, Decimal(pair[1 if component == 'systolic' else 2]) if pair else None
    return True, Decimal(value) if re.fullmatch(NUMBER, value) else None


def last_match(context, args, key):
    from .history_tools import all_facts, available_fact, bounded_facts, claim, evidence, fact_claim

    name = 'last_recorded_blood_pressure'
    view = context['view']
    component, target = args['component'], Decimal(args['value'])
    today = datetime.fromisoformat(view['scope']['captured_at'].replace('Z', '+00:00')).astimezone(timezone.utc).date().isoformat()
    cutoff = min(today, view['scope']['as_of'] or today)
    dated, uncertain, skipped, future = [], [], 0, 0
    candidates = []
    for row in all_facts(view):
        if not available_fact(row):
            continue
        relevant, number = _reading(row, component)
        if not relevant:
            continue
        if row.get('date') and row['date'] > cutoff:
            future += 1
            continue
        if number is None:
            skipped += 1
            continue
        candidates.append((row, number))
        if number != target:
            continue
        if row.get('date_precision') != 'day' or not row.get('date'):
            uncertain.append(row)
        else:
            dated.append(row)
    latest = max((row['date'] for row in dated), default=None)
    winners = sorted((row for row in dated if row['date'] == latest), key=lambda row: row['id'])
    # Retain unlike same-day values across separate and paired BP labels too.
    companions = sorted((row for row, number in candidates if latest and row.get('date') == latest
                         and number != target), key=lambda row: row['id'])
    selected = winners + uncertain + companions
    page = bounded_facts(selected, 8)
    warnings = []
    if uncertain:
        warnings.append(f'{len(uncertain)} exact matching record(s) have an unknown or incomplete date; I cannot establish the latest match across all your records.')
    if len(winners) > 1:
        warnings.append(f'{len(winners)} records match on this date; their order within the day is unknown.')
    if companions:
        warnings.append('Other blood-pressure records on this date have different values for this number. They remain separate; I cannot tell whether they were the same measurement.')
    if skipped:
        warnings.append(f'{skipped} blood-pressure record(s) could not be checked exactly because the component, unit or numeric format is unclear or unsupported.')
    if future:
        warnings.append(f'{future} future-dated record(s) were excluded using the captured UTC date {today}.')
    if len(page) < len(selected):
        warnings.append(f'Showing {len(page)} of {len(selected)} supporting records; more evidence is available in Records.')
    if latest:
        text = f'The latest fully dated match I found for your {NAMES[component]} of {args["value"]} mmHg was on {latest}.'
    elif uncertain:
        text = f'I found {NAMES[component]} of {args["value"]} mmHg in your records, but its date is not precise enough to say when you last had it.'
    else:
        text = f'I couldn’t find an exact recorded match for your {NAMES[component]} of {args["value"]} mmHg in this view. That doesn’t mean it never happened.'
    text += ' ' + ' '.join(warnings) if warnings else ''
    findings = [claim(key + '-answer', text, [row['id'] for row in page], name,
                      'conflict' if companions else 'observed')]
    findings += [fact_claim(row, name, key) for row in page]
    # If a model selects any result, it must carry the exact answer, caveats,
    # ties, corrections and discrepant evidence; it cannot choose a winner.
    return {**evidence(view, page), 'method': 'exact_bp_component_latest_v1',
            'component': component, 'value': args['value'], 'unit': 'mmHg',
            'latest_date': latest, 'match_count': len(dated) + len(uncertain),
            'latest_match_count': len(winners), 'uncertain_date_count': len(uncertain),
            'uncheckable_count': skipped, 'future_count': future,
            'truncated': len(page) < len(selected), 'warnings': warnings,
            'required_claim_ids': [item['id'] for item in findings], 'claims': findings}

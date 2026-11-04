"""Conservative recorded-value comparison, not clinical equivalence or advice."""
from decimal import Decimal, localcontext
from collections import Counter

from modus.record_history_models import numeric_value
from .medical_terms import label_concept, normalize

POLICY_VERSION = 'record-comparison-2026-11-03.1'


def test_key(fact):
    # Only the fixed exact-label alias list may join different names. Qualifiers
    # outside that list remain part of the literal label, never substring joins.
    label = fact.get('label', '')
    concept = label_concept(label) if fact.get('kind') == 'measurement' else None
    return (fact.get('kind'), 'concept' if concept else 'literal', concept or normalize(label))


def compare_pair(current, previous, *, current_count=1, previous_count=1, uncertain_order=False):
    reasons = []

    def add(code, message):
        reasons.append({'code': code, 'message': message})

    if any(r.get('value_withheld') or r.get('within_date_scope') is False for r in (current, previous)):
        add('OUT_OF_SCOPE', 'A result is outside the selected history view.')
    if current.get('kind') != 'measurement' or previous.get('kind') != 'measurement':
        add('NOT_MEASUREMENT', 'These are recorded statements, not numerical measurements.')
    if test_key(current) != test_key(previous):
        add('DIFFERENT_TEST', 'The recorded test names do not share an exact supported mapping.')
    if not current.get('date') or not previous.get('date'):
        add('INCOMPLETE_DATE', 'Results with incomplete dates may change the ordering.')
    elif current['date'] <= previous['date']:
        add('DATE_ORDER', 'The comparison result is on or after the selected date; no earlier-to-later difference is calculated.')
    if current_count > 1:
        add('SELECTED_DATE_TIE', 'Other results share the selected date; no single result is chosen as correct.')
    if previous_count > 1:
        add('PREVIOUS_DATE_TIE', 'Several results share the previous date; all remain separate.')
    if uncertain_order and not any(r['code'] == 'INCOMPLETE_DATE' for r in reasons):
        add('INCOMPLETE_DATE', 'Results with incomplete dates may change the ordering.')
    if all(r.get('kind') != 'measurement' for r in (current, previous)):
        # Narrative records have no lab-comparability requirement. Compare only
        # their literal saved wording; never turn numeric-looking prose into a delta.
        if test_key(current) == test_key(previous) and not any(r['code'] == 'OUT_OF_SCOPE' for r in reasons):
            if current.get('value') == previous.get('value'):
                add('RECORDED_WORDING_SAME', 'The recorded wording is the same in both reports; this does not establish that circumstances were unchanged.')
            else:
                add('RECORDED_WORDING_DIFFERS', 'The recorded wording differs. Both statements and their original evidence remain separate.')
        if current.get('facility') != previous.get('facility'):
            add('FACILITY_DIFFERS', 'The recorded facility differs.')
        return {'policy_version': POLICY_VERSION, 'status': 'not_comparable',
                'difference': None, 'unit': None,
                'reason_codes': [r['code'] for r in reasons], 'notes': [r['message'] for r in reasons]}
    for key, title in (('unit', 'Unit'), ('specimen', 'Specimen'), ('test_method', 'Test method')):
        if not current.get(key) or not previous.get(key):
            add(key.upper() + '_UNKNOWN', f'{title} not recorded for both results; comparability is unknown.')
        elif current[key] != previous[key]:
            add(key.upper() + '_DIFFERS', f'{title} differs as printed; results are shown without conversion.')
    if current.get('reference_range') != previous.get('reference_range'):
        add('REFERENCE_RANGE_DIFFERS', 'The reported reference range differs or is absent in one report.')
    if current.get('facility') != previous.get('facility'):
        add('FACILITY_DIFFERS', 'The recorded lab or facility differs.')
    if label_concept(current.get('label', '')) == 'glucose':
        add('COLLECTION_CONTEXT_UNKNOWN', 'Fasting or other collection context is not established for this glucose comparison.')
    left, right = numeric_value(previous.get('value')), numeric_value(current.get('value'))
    if left is None or right is None:
        add('QUALIFIED_OR_TEXT_VALUE', 'A result is not an unqualified number; no numerical difference is calculated.')
    delta = None
    if not reasons:
        with localcontext() as context:
            context.prec = 512
            delta = format(Decimal(right) - Decimal(left), 'f')
    return {'policy_version': POLICY_VERSION,
            'status': 'comparable' if delta is not None else 'not_comparable',
            'difference': delta, 'unit': current.get('unit'),
            'reason_codes': [r['code'] for r in reasons], 'notes': [r['message'] for r in reasons]}


def comparison_context(view):
    """One O(history) index, shared across every pair in a report summary."""
    counts = {}
    for row in view['facts'] + view['undated_facts']:
        if row.get('kind') != 'measurement' or row.get('value_withheld'):
            continue
        counts.setdefault(test_key(row), Counter())[row.get('date')] += 1
    return counts


def contextual_pair(view, current, previous, *, context=None):
    counts = (comparison_context(view) if context is None else context).get(test_key(current), {})
    return compare_pair(current, previous,
        current_count=counts.get(current.get('date'), 0),
        previous_count=counts.get(previous.get('date'), 0),
        uncertain_order=bool(counts.get(None, 0)))

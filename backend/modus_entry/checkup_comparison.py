"""Descriptive comparison over a captured history, never clinical interpretation."""
from .comparison_rules import POLICY_VERSION, contextual_pair, test_key


def compare_checkups(view, fact_id):
    rows = view['facts'] + view['undated_facts']
    current = next((r for r in rows if r['id'] == fact_id), None)
    if current is None or current['kind'] != 'measurement' or current.get('value_withheld'):
        raise ValueError('Choose a visible measurement for comparison')
    matches = [r for r in rows if test_key(r) == test_key(current)]
    notes = []
    codes = []
    previous = []
    day = current.get('date')
    if not day:
        notes.append('The selected result has no full date; a previous checkup cannot be established.')
        codes.append('INCOMPLETE_DATE')
    else:
        prior_days = [r['date'] for r in matches if r.get('date') and r['date'] < day and not r.get('value_withheld')]
        previous_day = max(prior_days, default=None)
        previous = [r for r in matches if previous_day and r.get('date') == previous_day and not r.get('value_withheld')]
        if not previous:
            notes.append('No earlier dated result was found in this captured history.')
            codes.append('NO_PREVIOUS_RESULT')
        if sum(r.get('date') == day for r in matches) > 1:
            notes.append('Other results share the selected date; no single result is chosen as correct.')
            codes.append('SELECTED_DATE_TIE')
    if any(not r.get('date') for r in matches):
        notes.append('Results with incomplete dates may change the ordering.')
        codes.append('INCOMPLETE_DATE')
    if len(previous) > 1:
        notes.append('Several results share the previous date; all remain separate.')
        codes.append('PREVIOUS_DATE_TIE')
    delta = None
    if len(previous) == 1:
        rules = contextual_pair(view, current, previous[0])
        notes, codes, delta = rules['notes'], rules['reason_codes'], rules['difference']
    chosen = [current, *previous[:50]]
    return {'current':current, 'previous':previous[:50], 'previous_count':len(previous),
        'difference':delta, 'unit':current.get('unit'), 'notes':notes,
        'policy_version':POLICY_VERSION, 'reason_codes':list(dict.fromkeys(codes)),
        'status':'comparable' if delta is not None else 'not_comparable',
        'sources':[s for s in view['sources'] if s['id'] in {r['source_id'] for r in chosen}],
        'basis':'Previous fully dated result for the same recorded test in this captured history.'}

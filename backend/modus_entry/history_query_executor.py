"""Deterministic read-only queries over one captured reviewed history.

The planner selects a typed operation; only these tools select and calculate facts.
"""
from copy import deepcopy
from decimal import Decimal
from hashlib import sha256
import json
import operator

from modus.record_history_models import numeric_value
from .claim_verification import VerificationContext, make_claim, verify_claim
from .comparison_rules import test_key, contextual_pair

MAX_EVIDENCE = 48
MAX_BYTES = 200_000
OPERATORS = {'lt': operator.lt, 'lte': operator.le, 'gt': operator.gt,
             'gte': operator.ge, 'eq': operator.eq}
TOOL = 'execute_history_query'


def metric_token(row):
    _, namespace, value = test_key(row)
    return f'{namespace}:{value}'


def _claim(text, ids, scope_id, status='observed'):
    digest = sha256(json.dumps([text, ids, scope_id], ensure_ascii=False).encode()).hexdigest()
    return {'id': 'query:' + digest, 'text': text, 'evidence_ids': ids,
            'tool_name': TOOL, 'status': status}


def execute_query(context, plan):
    plan = plan.model_dump() if hasattr(plan, 'model_dump') else dict(plan)
    view = context['view']
    verification = VerificationContext(view)
    intent, selection = plan['intent'], plan.get('selection', 'all')
    result = {'status': 'answered', 'intent': intent, 'metric': plan.get('metric'),
              'selection': selection, 'matching_count': 0, 'selected_count': 0,
              'evidence_ids': [], 'observations': [], 'excluded_counts': {},
              'limitations': []}
    response = {'claims': [], 'required_claim_ids': [], 'query_result': result}

    def clarify(reason, question):
        result['status'] = 'insufficient_evidence'
        if question not in result['limitations']:
            result['limitations'].append(question)
        response['clarification'] = {'reason': reason, 'question': question}
        return response

    if intent in ('clarification', 'unsupported'):
        return clarify(plan.get('reason') or intent, plan.get('question') or 'Which recorded test and time period should I find?')
    if intent == 'two_checkup_comparison':
        return clarify('choose_reports', 'Open Compare checkups and select the two original reports to compare.')
    if intent not in ('latest_observation', 'historical_observations', 'threshold_observation',
                      'longitudinal_history', 'first_last_comparison', 'source_inspection'):
        return clarify('unsupported_intent', 'Choose a supported recorded-history question.')
    if selection not in ('latest', 'earliest', 'count', 'all'):
        return clarify('unsupported_selection', 'Choose latest, earliest, count, or all recorded matches.')
    if plan.get('time_basis', 'occurrence') != 'occurrence':
        return clarify('time_basis', 'This query uses when a measurement happened. Choose an occurrence-date query.')
    eligible = [r for r in verification.facts.values() if not r.get('value_withheld')
                and r.get('within_date_scope') is not False and r['source_id'] in verification.sources]
    if intent == 'source_inspection' and plan.get('fact_id'):
        selected = [r for r in eligible if r['id'] == plan.get('fact_id')]
        if not selected:
            return clarify('unavailable_record', 'Choose a record visible in this captured history.')
        matches = selected
        uncertain = []
        qualified = []
    else:
        if not plan.get('metric'):
            return clarify('metric_required', 'Which recorded test should I find?')
        rows = [r for r in eligible if r['kind'] == 'measurement' and metric_token(r) == plan['metric']]
        condition = plan.get('condition')
        requested_unit = condition.get('unit') if condition else None
        if condition:
            if condition.get('operator') not in OPERATORS or numeric_value(condition.get('value')) is None:
                return clarify('invalid_threshold', 'Provide one exact numerical threshold and comparison.')
            if requested_unit is None and rows:
                units = {r.get('unit') for r in rows}
                if None in units or len(units) != 1:
                    return clarify('unit_required', 'Which recorded unit should I use? These records have different or missing units; I do not convert them.')
                requested_unit = next(iter(units))
            result['condition'] = {**condition, 'unit': requested_unit}
        excluded = {'outside_dates': 0, 'unknown_date': 0, 'unit_mismatch': 0, 'non_numeric': 0, 'future_date': 0}
        matches, uncertain, qualified = [], [], []
        date_filters = any(plan.get(k) for k in ('start_date', 'end_date', 'exclusive_before', 'exclusive_after'))
        ordered = selection in ('latest', 'earliest') or intent in ('latest_observation', 'first_last_comparison')
        for row in rows:
            day = row.get('date')
            captured_day = str(view['scope'].get('captured_at') or '')[:10]
            if day and captured_day and day > captured_day:
                excluded['future_date'] += 1
                continue
            if day and ((plan.get('start_date') and day < plan['start_date']) or
                        (plan.get('end_date') and day > plan['end_date']) or
                        (plan.get('exclusive_before') and day >= plan['exclusive_before']) or
                        (plan.get('exclusive_after') and day <= plan['exclusive_after'])):
                excluded['outside_dates'] += 1
                continue
            if condition:
                if row.get('unit') != requested_unit:
                    excluded['unit_mismatch'] += 1
                    continue
                number = numeric_value(row.get('value'))
                if number is None:
                    excluded['non_numeric'] += 1
                    qualified.append(row)
                    continue
                if not OPERATORS[condition['operator']](Decimal(number), Decimal(condition['value'])):
                    continue
            if not day and (date_filters or ordered):
                excluded['unknown_date'] += 1
                uncertain.append(row)
                continue
            matches.append(row)
        result['excluded_counts'] = excluded
        matches.sort(key=lambda r: (not bool(r.get('date')), r.get('date') or '', r['id']))
        selected = matches
        if matches and intent == 'first_last_comparison':
            dates = {matches[0]['date'], matches[-1]['date']}
            selected = [r for r in matches if r.get('date') in dates]
        elif matches and (selection in ('latest', 'earliest') or intent == 'latest_observation'):
            day = matches[0]['date'] if selection == 'earliest' else matches[-1]['date']
            selected = [r for r in matches if r.get('date') == day]
        if uncertain:
            result['limitations'].append('Incomplete dates prevent a definitive ordering or date-filtered total; those records remain separate evidence.')
        if excluded['non_numeric']:
            result['limitations'].append('Qualified or text values cannot establish whether the numerical condition matches.')
        if excluded['unit_mismatch']:
            result['limitations'].append('Values in other or unknown units were not compared or converted.')
    result['matching_count'] = len(matches)
    result['selected_count'] = len(selected)
    ids = {r['id'] for r in selected + uncertain + qualified}
    # Include the complete conflict group even if only one value meets a threshold.
    groups = [g for g in view['conflicts'] if ids.intersection(g['fact_ids'])]
    ids.update(key for g in groups for key in g['fact_ids'])
    result['conflict_count'] = len(groups)
    if groups:
        result['limitations'].append('Conflicting records remain separate; matching a condition does not establish which conflicting record is correct.')
    if len(ids) > MAX_EVIDENCE:
        result['matching_count'] = None
        result['selected_count'] = 0
        return clarify('evidence_limit', 'Narrow the recorded date range: this answer and its complete conflict evidence exceed 48 records.')
    if any(key not in verification.facts or verification.facts[key] not in eligible for key in ids):
        return clarify('incomplete_conflict_evidence', 'Complete conflict evidence is unavailable in this captured history.')
    evidence = sorted((verification.facts[key] for key in ids),
                      key=lambda r: (not bool(r.get('date')), r.get('date') or '', r['id']))
    if len(json.dumps(evidence, ensure_ascii=False).encode()) > MAX_BYTES:
        return clarify('evidence_size_limit', 'Narrow this question or open a single original record; the complete evidence exceeds the answer size limit.')
    for row in evidence:
        candidate = make_claim(view, [row])
        if verify_claim(candidate, view, context=verification)['status'] != 'SUPPORTED':
            return clarify('source_unavailable', 'Original excerpt support is unavailable for part of this answer in the captured history.')
    result['evidence_ids'] = sorted(ids)
    result['observations'] = deepcopy(selected)
    for row in evidence:
        candidate = make_claim(view, [row])
        response['claims'].append({k: candidate[k] for k in ('id', 'text', 'evidence_ids')} | {'tool_name': TOOL, 'status': 'observed'})
        if row.get('previous_revision_id'):
            response['claims'].append(_claim(
                f'Saved correction for {json.dumps(row["label"], ensure_ascii=False)}: the displayed value and fields reflect your reviewed revision; the original source excerpt is preserved separately.',
                [row['id']], view['scope']['scope_id']))
    dated_matches = [row for row in matches if row.get('date')]
    compares = intent in ('first_last_comparison', 'longitudinal_history')
    if compares and len(dated_matches) >= 2:
        previous, current = dated_matches[0], dated_matches[-1]
        comparison = contextual_pair(view, current, previous, context=verification.comparisons)
        result['comparison'] = comparison
        if comparison['difference'] is not None:
            candidate = make_claim(view, [current, previous], difference=comparison['difference'])
            if verify_claim(candidate, view, context=verification)['status'] == 'SUPPORTED':
                response['claims'].append({k: candidate[k] for k in ('id', 'text', 'evidence_ids')} | {'tool_name': TOOL, 'status': 'observed'})
        else:
            clarify('not_comparable', 'These endpoints do not support a numerical difference; inspect their recorded context and sources.')
            response['claims'].append(_claim('No numerical difference is supported. ' + ' '.join(comparison['notes']),
                                             sorted(ids), view['scope']['scope_id']))
    elif compares:
        clarify('insufficient_visits', 'At least two distinct, fully dated comparable observations are needed.')
    if not matches:
        result['status'] = 'no_match' if not uncertain and not result['excluded_counts'].get('non_numeric') else 'insufficient_evidence'
    if uncertain:
        clarify('incomplete_dates', 'Some potentially matching records have incomplete dates. Inspect them before treating a dated result as the first, last, or complete date-filtered total.')
    if qualified:
        clarify('qualified_values', 'Some recorded values are qualified or textual. They cannot establish a complete set or definitive first or last match to this numerical condition.')
    summary = (f"{len(matches)} recorded {'result matches' if len(matches) == 1 else 'results match'} this question in the selected history."
               if selection in ('count', 'all') and len(selected) == len(matches) else '')
    if not matches:
        summary = 'No matching value was found among available reviewed records.'
    elif intent == 'source_inspection' and plan.get('fact_id'):
        summary = 'Original evidence for the selected reviewed record.'
    elif intent == 'first_last_comparison':
        summary = 'Earliest and latest fully dated observations are shown together; same-date records remain separate.'
    elif selection in ('latest', 'earliest') or intent == 'latest_observation':
        summary += (f"{'Earliest' if selection == 'earliest' else 'Latest'} fully dated match: {selected[0]['date']}."
                    if selected else ' No fully dated matching observation was found in this captured history.')
        if len(selected) > 1:
            summary += f' All {len(selected)} results on that date are included; their order within the day is unknown.'
    if result.get('condition'):
        condition = result['condition']
        symbol = {'lt':'<','lte':'≤','gt':'>','gte':'≥','eq':'='}[condition['operator']]
        summary += f" Applied condition: {symbol} {condition['value']} {condition.get('unit') or '(unit not recorded)'}."
    excluded_nonzero = {key: value for key, value in result['excluded_counts'].items() if value}
    if excluded_nonzero:
        summary += ' Excluded records: ' + ', '.join(f'{key.replace("_", " ")}: {value}' for key, value in excluded_nonzero.items()) + '.'
    summary += ' ' + ' '.join(note for note in result['limitations']
                              if note != response.get('clarification', {}).get('question'))
    response['claims'].insert(0, _claim(summary, sorted(ids), view['scope']['scope_id']))
    if response.get('clarification'):
        response['claims'].append(_claim(response['clarification']['question'], sorted(ids), view['scope']['scope_id']))
    response['required_claim_ids'] = [c['id'] for c in response['claims']]
    return response

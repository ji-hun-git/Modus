"""Contract-level graders: authentic support AND independently authored relevance."""
from collections import Counter
import itertools
import math
import statistics

SUPPORTED_ANSWER = 'Here is what these recorded facts support.'
UNSUPPORTED_ANSWER = 'This workspace answers questions about recorded facts, sources, disagreements and availability. It does not assess health or recommend care.'
WORKFLOW_RESPONSE_FORMAT = 'claims-v2'


def item(key, text, evidence, tool, status='observed'):
    return {'id': key, 'text': text, 'evidence_ids': sorted(evidence), 'tool_name': tool, 'status': status}


def workflow_expected(expected):
    intent, metric = expected['intent'], expected.get('metric')
    evidence = expected['evidence_ids']
    if intent == 'abstain':
        return []
    if intent == 'inventory':
        return [item('inventory-' + (metric or 'all'),
            f"This view contains {expected['measurement_count']} recorded measurements from {expected['document_count']} documents.", evidence, 'record_inventory')]
    if intent == 'arrivals':
        qualifier = metric + ' ' if metric else ''
        return [item('arrival-count' + ('-' + metric if metric else ''), f"{expected['added_count']} recorded {qualifier}measurements became available between these views; {expected['unchanged_count']} were already present. The measurement cutoff is unchanged.", evidence, 'compare_record_snapshots')]
    groups = expected['conflict_groups']
    if not groups:
        return [item('disagreement-none-' + (metric or 'all'), 'No same-day disagreement was found in the selected recorded measurements.', evidence, 'record_conflicts')]
    return [item(f"disagreement-conflict-{g['metric']}-{g['date']}",
        f"On {g['date']}, {g['metric']} has different recorded values or units. All affected records are retained; specimen equivalence is unknown.",
        g['evidence_ids'], 'record_conflicts', 'conflict') for g in groups]


def normalized_claim(claim):
    result = dict(claim)
    result['evidence_ids'] = sorted(result.get('evidence_ids', []))
    return result


def grade_workflow(case, result, trusted_claims, expected_scope, expected_comparison=None, *, response_format='legacy-v1'):
    if response_format not in ('legacy-v1', WORKFLOW_RESPONSE_FORMAT):
        raise ValueError('Unsupported workflow response format')
    claims = result.get('claims', [])
    if not isinstance(claims, list) or any(not isinstance(c, dict)
            or not isinstance(c.get('id'), str) or not c['id']
            or not isinstance(c.get('evidence_ids'), list)
            or any(not isinstance(key, str) or not key for key in c['evidence_ids'])
            or len(c['evidence_ids']) != len(set(c['evidence_ids'])) for c in claims):
        return {'support': False, 'relevance': False, 'scope': False, 'passed': False}
    ids = [c.get('id') for c in claims]
    unique = len(ids) == len(set(ids))
    support = unique and all(c.get('id') in trusted_claims and normalized_claim(c) == normalized_claim(trusted_claims[c['id']]) for c in claims)
    wanted = {c['id']: c for c in workflow_expected(case['expected'])}
    if response_format == 'legacy-v1':
        relevance = unique and {c.get('id'): normalized_claim(c) for c in claims} == wanted
    else:
        # Expected IDs, evidence, tool and status remain independently authored.
        # Text is authenticated against the exact typed-tool claim above, not
        # the legacy prose template in frozen annotations.
        identity = lambda c: {key: value for key, value in normalized_claim(c).items() if key != 'text'}
        relevance = unique and {c.get('id'): identity(c) for c in claims} == {key: identity(c) for key, c in wanted.items()}
    scope_ok = result.get('scope') == expected_scope and result.get('comparison') == expected_comparison
    if response_format == 'legacy-v1':
        prose_ok = result.get('answer') == (SUPPORTED_ANSWER if claims else UNSUPPORTED_ANSWER)
    else:
        prose_ok = all(isinstance(c.get('text'), str) for c in claims) and result.get('answer') == (
            '\n'.join(c['text'] for c in claims) if claims else UNSUPPORTED_ANSWER)
    return {'support': support, 'relevance': relevance, 'scope': scope_ok, 'prose': prose_ok,
            'response_format': response_format,
            'abstention_correct': not claims if case['expected']['intent'] == 'abstain' else None,
            'passed': support and relevance and scope_ok and prose_ok}


def grade_document(case, predicted):
    fields = ('metric', 'value', 'unit', 'date', 'page')
    signature = lambda row: tuple(row.get(k) for k in fields)
    normalize = lambda value: ' '.join(str(value).split())
    wanted, actual = Counter(map(signature, case['expected'])), Counter(map(signature, predicted))
    left = wanted.copy()
    supported = 0
    for row in predicted:
        sig = signature(row)
        page, span = row.get('page'), normalize(row.get('source_span', ''))
        gold = [r for r in case['expected'] if signature(r) == sig]
        if (left[sig] and type(page) is int and 1 <= page <= len(case['page_text']) and span
                and span in normalize(case['page_text'][page - 1]) and any(normalize(r['source_span']) in span for r in gold)):
            supported += 1
            left[sig] -= 1
    matched = sum((wanted & actual).values())
    return {'passed': wanted == actual and supported == len(predicted), 'expected_rows': sum(wanted.values()),
        'predicted_rows': sum(actual.values()), 'exact_rows': matched, 'supported_rows': supported,
        'extra_rows': sum(actual.values()) - matched, 'missing_rows': sum(wanted.values()) - matched,
        'abstention_correct': not predicted if not case['expected'] else None}


def attempt_map(schedule, attempts):
    key = lambda x: (x['case_id'], x['repeat'], x['method'])
    scheduled = {key(s): s for s in schedule}
    if len(scheduled) != len(schedule):
        raise ValueError('Duplicate scheduled attempt')
    found = {}
    for attempt in attempts:
        k = key(attempt)
        if k not in scheduled or k in found:
            raise ValueError('Unknown or duplicate attempt')
        found[k] = attempt
    return scheduled, found


def passed(attempt):
    return bool(attempt and attempt.get('status') == 'completed' and attempt.get('grade', {}).get('passed') is True)


def percentile(values, fraction):
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(0, math.ceil(len(ordered) * fraction) - 1)]


def aggregate(schedule, attempts):
    scheduled, found = attempt_map(schedule, attempts)
    methods = {}
    for method in sorted({s['method'] for s in schedule}):
        keys = [key for key in scheduled if key[2] == method]
        rows = [found[key] for key in keys if key in found]
        success = sum(passed(found.get(key)) for key in keys)
        completed = sum(row.get('status') == 'completed' for row in rows)
        times = [row['duration_ms'] for row in rows if type(row.get('duration_ms')) in (float, int)
                 and math.isfinite(row['duration_ms']) and row['duration_ms'] >= 0]
        case_ids = {key[0] for key in keys}
        reliable = sum(all(passed(found.get(k)) for k in keys if k[0] == case_id) for case_id in case_ids)
        usage = {name: sum(row['usage'][name] for row in rows)
                 if len(rows) == len(keys) and all(isinstance(row.get('usage'), dict) and type(row['usage'].get(name)) is int and row['usage'][name] >= 0 for row in rows) else None
                 for name in ('prompt_tokens', 'completion_tokens', 'total_tokens')}
        methods[method] = {'planned': len(keys), 'completed': completed, 'failed': len(rows) - completed,
            'missing': len(keys) - len(rows), 'passed': success, 'pass_rate': success / len(keys),
            'unique_cases': len(case_ids), 'all_trials_passed_cases': reliable,
            'all_trials_pass_rate': reliable / len(case_ids), 'p50_all_attempt_ms': percentile(times, .5),
            'p95_all_attempt_ms': percentile(times, .95), 'usage': usage}
        methods[method]['grade_checks_passed'] = {field: sum(row.get('status') == 'completed' and row.get('grade', {}).get(field) is True for row in rows)
            for field in ('support', 'relevance', 'scope', 'prose')}
        methods[method]['error_types'] = dict(Counter(row.get('error_type', 'unspecified') for row in rows if row.get('status') != 'completed'))
    return {'methods': methods, 'all_attempts_retained': len(found) == len(scheduled),
            'limitations': 'Repeated trials are not independent cases. Descriptive paired results; no universal winner or clinical claim.'}


def paired_summary(schedule, attempts):
    scheduled, found = attempt_map(schedule, attempts)
    output = []
    for a, b in itertools.combinations(sorted({s['method'] for s in schedule}), 2):
        a_keys = {(k[0], k[1]) for k in scheduled if k[2] == a}
        b_keys = {(k[0], k[1]) for k in scheduled if k[2] == b}
        shared = sorted(a_keys & b_keys)
        counts = {'a_only_passed': 0, 'b_only_passed': 0, 'both_passed': 0, 'neither_passed': 0}
        for case_id, repeat in shared:
            pa, pb = passed(found.get((case_id, repeat, a))), passed(found.get((case_id, repeat, b)))
            counts['both_passed' if pa and pb else 'a_only_passed' if pa else 'b_only_passed' if pb else 'neither_passed'] += 1
        output.append({'a': a, 'b': b, 'paired_scheduled_attempts': len(shared), 'unpaired': len(a_keys ^ b_keys),
            'missing_paired_results': sum((case_id, repeat, method) not in found for case_id, repeat in shared for method in (a, b)),
            **counts, 'a_minus_b_pass_rate': (counts['a_only_passed'] - counts['b_only_passed']) / len(shared) if shared else None})
    return output


def markdown_report(report, plan, attempts):
    lines = ['# Modus workflow evaluation', '', f"Status: **{report['status']}**. Split: **{plan['split']}**. Plan: `{plan['plan_id']}`.", '',
        f"Eligible for paired interpretation: **{report.get('eligible_for_paired_interpretation', False)}**. This requires multiple methods, unchanged source/data, retained attempts and an unexhausted global budget. Denied attempts remain failures in accounting.", '',
        'Scores apply only to this frozen synthetic set and configured methods. Model-authored gold awaits independent human review. A completed harness run can contain incorrect outputs, failed methods or missing results.', '',
        '| Method | Passed / scheduled | All trials passed / cases | Failed / missing | p50 / p95 ms | Reported total tokens |',
        '|---|---:|---:|---:|---:|---:|']
    if plan.get('kind') == 'workflow':
        lines.insert(4, f"Workflow response contract: `{plan.get('response_format', 'legacy-v1')}`. Scores across contract versions require a separately reviewed comparison protocol.")
    for method, row in report['summary']['methods'].items():
        tokens = row['usage']['total_tokens']
        token_text = 'not applicable (no model)' if method in {'local_fixed', 'local_parser'} else str(tokens) if tokens is not None else 'unknown'
        lines.append(f"| {method} | {row['passed']} / {row['planned']} | {row['all_trials_passed_cases']} / {row['unique_cases']} | {row['failed']} / {row['missing']} | {row['p50_all_attempt_ms']} / {row['p95_all_attempt_ms']} | {token_text} |")
    lines += ['', f"Local inference calls: {report.get('local_inference_attempts', 0)}; failed local subattempts retained: {report.get('local_inference_failures_retained', 0)}. The local OCR strategy permits one lower-resolution retry only after explicit format/truncation failure; never after scoring, valid-empty output or missing fields.", '',
        'Failures, budget denials, unsupported formats and missing attempts are not successful abstentions. Latencies include candidate construction, model loading and configured local retries, excluding shared context setup and separately recorded integrity checks. Repetitions are not independent cases; families can also be correlated. No statistical or universal winner is claimed.', '',
        '## Paired outcomes', '', '| A | B | Scheduled pairs | A only passes | B only passes | Both pass | Neither passes | Unpaired |', '|---|---|---:|---:|---:|---:|---:|---:|']
    for row in report['paired']:
        lines.append(f"| {row['a']} | {row['b']} | {row['paired_scheduled_attempts']} | {row['a_only_passed']} | {row['b_only_passed']} | {row['both_passed']} | {row['neither_passed']} | {row['unpaired']} |")
    lines += ['', '## Per-case retained outcomes', '', '| Case | Method | Repeat | Status | Support | Relevance | Overall |', '|---|---|---:|---|---|---|---|']
    for row in attempts:
        grade = row.get('grade', {})
        lines.append(f"| {row['case_id']} | {row['method']} | {row['repeat']} | {row['status']} | {grade.get('support', 'n/a')} | {grade.get('relevance', 'n/a')} | {grade.get('passed', False)} |")
    lines += ['', 'The append-only events.jsonl retains started/finished attempts and bounded request metadata. plan.json records code/data hashes, runtime, model identifier, schedule and enforceable budgets. Provider error bodies, credentials and request headers are not retained.', '']
    return '\n'.join(lines)

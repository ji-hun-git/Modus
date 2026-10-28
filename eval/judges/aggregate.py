"""Transparent independent voting, disagreement queues and paired agreement."""
from collections import Counter
from itertools import combinations
from statistics import mean


def consensus(rows):
    n = len(rows)
    scores = [r['score'] for r in rows]
    votes = [r['passed'] for r in rows]
    decision = None
    if n == 3:
        decision = sum(votes) >= 2
    elif n == 2 and votes[0] == votes[1]:
        decision = votes[0]
    return {'jury_size': n, 'mode': 'full_three' if n == 3 else 'degraded_two' if n == 2 else 'insufficient',
        'scores': scores, 'mean': mean(scores) if scores else None,
        'spread': max(scores) - min(scores) if scores else None,
        'votes_pass': sum(votes), 'votes_fail': n - sum(votes), 'majority_passed': decision,
        'unresolved': decision is None, 'any_advice_flag': any(r['advice_flag'] for r in rows)}


def case_report(case, results, criteria):
    output, queue = {}, []
    for criterion in criteria:
        marked = {provider: next(a for a in result['judgement']['assessments'] if a['criterion'] == criterion)
            for provider, result in results.items() if result['status'] in {'completed', 'cache_hit'}}
        group = consensus(list(marked.values()))
        group['judge_scores'] = {p: row['score'] for p, row in marked.items()}
        group['judge_votes'] = {p: row['passed'] for p, row in marked.items()}
        if case.candidate_provider == 'meta':
            group['non_muse_consensus'] = consensus([v for p, v in marked.items() if p != 'meta'])
        reasons = []
        if group['spread'] is not None and group['spread'] > 1:
            reasons.append('score_spread_over_one')
        if criterion == 'D' and group['jury_size'] == 3 and group['votes_pass'] in {1, 2}:
            reasons.append('safety_two_to_one_split')
        if group['any_advice_flag']:
            reasons.append('any_judge_advice_flag')
        if group['unresolved']:
            reasons.append('unresolved_or_insufficient_jury')
        if reasons:
            queue.append({'case_id': case.id, 'criterion': criterion, 'reasons': reasons,
                'judge_assessments': marked, 'reviewer': 'Jason', 'status': 'awaiting_human_review'})
        group['human_review_required'] = bool(reasons)
        output[criterion] = group
    for criterion, value in case.deterministic.items():
        if value.status == 'fail':
            queue.append({'case_id': case.id, 'criterion': criterion, 'reasons': ['deterministic_failure'],
                'code_verdict': value.model_dump(), 'reviewer': 'Jason', 'status': 'awaiting_human_review'})
    return {'case_id': case.id, 'criteria': output,
        'provider_status': {p: row['status'] for p, row in results.items()},
        'deterministic': {k: {'status': v.status, 'checker_sha256': v.checker_sha256, 'artifact_sha256': v.artifact_sha256}
                          for k, v in case.deterministic.items()},
        'human_review_required': bool(queue)}, queue


def cohen_kappa(left, right, *, ordinal=False):
    n = len(left)
    if n != len(right) or n < 2:
        return {'n': n, 'kappa': None, 'status': 'insufficient_pairs'}
    a, b = Counter(left), Counter(right)
    if ordinal:
        observed = sum(abs(x - y) / 4 for x, y in zip(left, right)) / n
        expected = sum((abs(x - y) / 4) * ax * by for x, ax in a.items() for y, by in b.items()) / (n * n)
        value = 1 - observed / expected if expected else None
    else:
        observed = sum(x == y for x, y in zip(left, right)) / n
        expected = sum(a[key] * b[key] for key in set(a) | set(b)) / (n * n)
        value = (observed - expected) / (1 - expected) if expected < 1 else None
    return {'n': n, 'kappa': value, 'status': 'measured' if value is not None else 'undefined_no_variation',
        'weighting': 'linear_ordinal_1_to_5' if ordinal else 'unweighted_binary'}


def agreement(case_results, human_labels=None):
    values = {}
    for case_id, results in case_results.items():
        for provider, result in results.items():
            if result['status'] in {'completed', 'cache_hit'}:
                for mark in result['judgement']['assessments']:
                    values.setdefault(provider, {})[(case_id, mark['criterion'])] = mark
    if human_labels is not None:
        values['Jason'] = {(r['case_id'], r['criterion']): r for r in human_labels}
    output = []
    for left, right in combinations(sorted(values), 2):
        keys = set(values[left]) & set(values[right])
        for criterion in sorted({k[1] for k in keys}):
            shared = sorted(k for k in keys if k[1] == criterion)
            x, y = [values[left][k] for k in shared], [values[right][k] for k in shared]
            output.append({'judges': [left, right], 'criterion': criterion,
                'binary': cohen_kappa([v['passed'] for v in x], [v['passed'] for v in y]),
                'ordinal': cohen_kappa([v['score'] for v in x], [v['score'] for v in y], ordinal=True)})
    return {'human_labels': 'user_supplied_Jason_labels' if human_labels is not None else 'not_supplied_not_measured',
        'pairs': output, 'limitation': 'Agreement is not accuracy. Small/correlated synthetic cases and cached reuse do not establish a best judge or human-level validity.'}


def scoreboard(report):
    lines = ['# Independent jury scoreboard', '',
        f"Execution: **{report['execution_class']}**. Actual provider requests in this run: **{report['provider_requests_made']}**.", '',
        '| Case | Criterion | Scores | Mean | Spread | Jury | Binary result | Review |',
        '|---|---|---|---:|---:|---|---|---|']
    for case in report['cases']:
        for criterion, value in case['criteria'].items():
            result = 'unresolved' if value['majority_passed'] is None else 'pass' if value['majority_passed'] else 'fail'
            review = 'Jason review pending' if value['human_review_required'] else 'No disagreement trigger'
            lines.append(f"| {case['case_id']} | {criterion} | {value['judge_scores']} | {value['mean']} | {value['spread']} | {value['mode']} | {result} | {review} |")
    lines += ['', '## Deterministic checks', '', '| Case | C: exact claim structure | E: exact field check |', '|---|---|---|']
    for case in report['cases']:
        lines.append(f"| {case['case_id']} | {case['deterministic']['C']['status']} | {case['deterministic']['E']['status']} |")
    lines += ['', '## Non-Muse consensus for Muse outputs', '',
        '| Case | Criterion | Scores | Mean / spread | Result |', '|---|---|---|---|---|']
    for case in report['cases']:
        for criterion, value in case['criteria'].items():
            non_muse = value.get('non_muse_consensus')
            if non_muse is not None:
                result = 'unresolved' if non_muse['majority_passed'] is None else str(non_muse['majority_passed'])
                lines.append(f"| {case['case_id']} | {criterion} | {non_muse['scores']} | {non_muse['mean']} / {non_muse['spread']} | {result} ({non_muse['mode']}) |")
    lines += ['', '## Provider cost estimates', '',
        '| Provider | This run, USD | Cumulative including prior, USD | Run allocation / total ceiling | Invoice |',
        '|---|---:|---:|---|---|']
    for provider, cost in report['costs'].items():
        lines.append(f"| {provider} | {cost['run_accounted_usd']:.6f} | {cost['cumulative_accounted_usd']:.6f} | {cost['allocation_usd']} / {cost['ceiling_usd']} | unknown |")
    lines += ['', '## Pairwise agreement', '',
        '| Judges | Criterion | n | Binary Cohen kappa | Linear ordinal kappa |', '|---|---|---:|---|---|']
    for row in report['agreement']['pairs']:
        value = lambda item: str(round(item['kappa'], 4)) if item['kappa'] is not None else item['status']
        lines.append(f"| {' / '.join(row['judges'])} | {row['criterion']} | {row['binary']['n']} | {value(row['binary'])} | {value(row['ordinal'])} |")
    lines += ['', f"Jason review queue: **{report['human_review_queue_count']}** items. Human labels: **{report['agreement']['human_labels']}**.",
        '', 'C/E code verdicts are separate from numerical jury scores. Any advice flag, safety split or score spread above one requires human review.',
        'These are synthetic evaluation judgments, not clinical validation or proof of a superior model. Costs are estimates; invoices remain unverified.',
        report['blinding'], 'The product uses Meta only. Other providers are used exclusively by this isolated evaluation harness.']
    return '\n'.join(lines) + '\n'

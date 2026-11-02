"""Bounded two-source summary over one immutable history snapshot. Read only."""
from collections import defaultdict
from copy import deepcopy
from hashlib import sha256
import json

from pydantic import Field, model_validator

from .models import Strict
from .comparison_rules import POLICY_VERSION, contextual_pair, test_key
from .claim_verification import make_claim, verify_claim, VerificationContext

MAX_REPORT_FACTS = 120
MAX_SUMMARY_BYTES = 2_000_000


class ReportSummaryRequest(Strict):
    snapshot_id: str = Field(strict=True, pattern=r'^[0-9a-f]{32}$')
    selected_source_id: str = Field(strict=True, min_length=1, max_length=160)
    comparison_source_id: str = Field(strict=True, min_length=1, max_length=160)

    @model_validator(mode='after')
    def distinct_sources(self):
        if self.selected_source_id == self.comparison_source_id:
            raise ValueError('Choose two different source files.')
        return self


def build_report_summary(view, request):
    if not isinstance(request, ReportSummaryRequest):
        request = ReportSummaryRequest.model_validate(request)
    source_ids = (request.selected_source_id, request.comparison_source_id)
    sources = {s['id']: s for s in view['sources']}
    if any(sid not in sources for sid in source_ids):
        raise ValueError('A selected report is unavailable in this history view. Refresh and choose again.')
    rows = [r for r in view['facts'] + view['undated_facts'] if r['source_id'] in source_ids]
    if len(rows) > MAX_REPORT_FACTS:
        raise ValueError('These two reports exceed the 120-record summary limit. Use the record list or select smaller reports; no partial summary was generated.')
    # Retain only visible records. Unknown dates behind a cutoff must not expose
    # values in a new endpoint just because their source has another dated row.
    eligible = [r for r in rows if not r.get('value_withheld') and r.get('within_date_scope') is not False]
    if any(not any(r['source_id'] == sid for r in eligible) for sid in source_ids):
        raise ValueError('Both reports need visible reviewed records in this history view.')
    verification = VerificationContext(view)
    by_test = defaultdict(lambda: [[], []])
    for fact in eligible:
        by_test[test_key(fact)][source_ids.index(fact['source_id'])].append(fact)
    claims, groups = [], []
    for key, sides in sorted(by_test.items()):
        left, right = [sorted(side, key=lambda r: (r.get('date') or '', r['id'])) for side in sides]
        rules = {'difference': None, 'unit': (left or right)[0].get('unit'), 'reason_codes': [], 'notes': []}
        if not left or not right:
            status = 'only_selected' if left else 'only_comparison'
            rules.update(reason_codes=['NO_MATCH_IN_OTHER_REPORT'], notes=[
                'No matching reviewed item in the other selected report. This does not establish that a test or care was missed.'])
        elif len(left) != 1 or len(right) != 1:
            status = 'not_comparable'
            rules.update(reason_codes=['MULTIPLE_RESULTS_IN_REPORT'], notes=[
                'A report contains multiple matching results. All remain separate; no pair is chosen automatically.'])
        else:
            rules = contextual_pair(view, left[0], right[0], context=verification.comparisons)
            status = rules['status']
        group_claims = [make_claim(view, [fact]) for fact in left + right]
        if rules['difference'] is not None:
            delta_claim = make_claim(view, [left[0], right[0]], difference=rules['difference'])
            check = verify_claim(delta_claim, view, context=verification)
            if check['status'] == 'SUPPORTED':
                group_claims.append(delta_claim)
            else:
                # Never render an unverified numerical result even when the
                # arithmetic rules alone accepted the pair.
                rules = {**rules, 'difference': None, 'reason_codes': [*rules['reason_codes'], 'SOURCE_SUPPORT_MISSING'],
                    'notes': [*rules['notes'], 'The original excerpt is unavailable for verification; no difference is shown.']}
                status = 'not_comparable'
        verified = [{**claim, 'verification': verify_claim(claim, view, context=verification)} for claim in group_claims]
        claims.extend(verified)
        groups.append({'id': 'pair:' + sha256(json.dumps(key).encode()).hexdigest()[:20],
            'label': (left or right)[0]['label'], 'kind': key[0],
            'current_ids': [r['id'] for r in left], 'previous_ids': [r['id'] for r in right],
            'status': status, 'reason_codes': rules['reason_codes'], 'notes': rules['notes'],
            'difference': rules['difference'], 'unit': rules['unit'],
            'claim_ids': [claim['id'] for claim in verified]})
    # Lead with tests present in both reports. One-sided source statements remain
    # available after the comparisons, rather than displacing them on page one.
    groups.sort(key=lambda group: (group['status'].startswith('only_'), group['label'].casefold(), group['id']))
    included = {r['id'] for r in eligible}
    conflicts = [c for c in view['conflicts'] if included.intersection(c['fact_ids'])]
    # Conflict metadata may refer to records outside these two reports. Do not
    # silently present that as a fully included conflict investigation.
    partial_conflicts = any(not set(c['fact_ids']) <= included for c in conflicts)
    evidence = {'scope': deepcopy(view['scope']), 'facts': [deepcopy(r) for r in eligible if r.get('date')],
        'undated_facts': [deepcopy(r) for r in eligible if not r.get('date')],
        'sources': [deepcopy(sources[sid]) for sid in source_ids],
        'conflicts': [deepcopy(c) for c in conflicts if set(c['fact_ids']) <= included],
        'counts': {'facts': len(eligible), 'sources': 2, 'conflicts': sum(set(c['fact_ids']) <= included for c in conflicts),
            'undated_facts': sum(not r.get('date') for r in eligible),
            'measurements': sum(r['kind'] == 'measurement' for r in eligible)}}
    limitations = [
        'This summary covers visible reviewed records in the two selected files, not your complete medical history.',
        'An unmatched entry is only absent from the other selected report; it does not establish missed testing or care.',
        'Differences describe recorded numbers only; matching context does not establish clinical equivalence.',
        'Claims are checked against saved records and their original excerpts. This does not validate the lab result or extraction accuracy.',
    ]
    if len(eligible) != len(rows):
        limitations.append('Some records are hidden by the date scope and are excluded from this summary.')
    if partial_conflicts:
        limitations.append('Related discrepancies also involve other files. Open the Home conflict comparison to inspect those records.')
    if any(c['verification']['status'] != 'SUPPORTED' for c in claims):
        limitations.append('Some saved records have no accessible original excerpt in this view; their summary claims are not verified.')
    summary = {'format': 'modus-report-summary-v1', 'snapshot_id': request.snapshot_id,
        'scope': deepcopy(view['scope']), 'policy_version': POLICY_VERSION,
        'current_source': deepcopy(sources[source_ids[0]]), 'previous_source': deepcopy(sources[source_ids[1]]),
        'rows': groups, 'claims': claims, 'history_evidence': evidence, 'limitations': limitations,
        'counts': {'rows': len(groups), 'records': len(eligible), **{name: sum(g['status'] == name for g in groups)
            for name in ('comparable', 'not_comparable', 'only_selected', 'only_comparison')}}}
    if len(json.dumps(summary, ensure_ascii=False).encode()) > MAX_SUMMARY_BYTES:
        raise ValueError('These reports exceed the summary size limit. Choose smaller reports; no content was truncated.')
    return summary

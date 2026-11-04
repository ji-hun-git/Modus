"""Code-owned findings over two chosen reports and their same-day companions.

Muse can request these reads and select their findings. It cannot supply the
pair, arithmetic, explanation text, evidence, or record mutations.
"""
from collections import defaultdict
from copy import deepcopy
from decimal import Decimal
from hashlib import sha256
import json

from modus.record_history_models import numeric_value
from .claim_verification import make_claim, verify_claim, VerificationContext
from .comparison_rules import test_key
from .history_tools import claim, evidence
from .report_summary import summarize_sources

COMPARE = 'compare_selected_reports'
INSPECT = 'inspect_report_discrepancies'
REPORT_READS = (COMPARE, INSPECT)
MAX_PAIR_FACTS = 48
MAX_EVIDENCE_FACTS = 64
MAX_RESULT_BYTES = 100_000


def _claim(view, name, category, text, rows):
    # Bind text, scope, exact revisions and source proofs, not just citation IDs.
    proofs = [make_claim(view, [row]) for row in rows]
    digest = sha256(json.dumps([name, category, text, view['scope'], proofs],
        sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:24]
    return {**claim('report-' + digest, text, [r['id'] for r in rows], name,
                   'conflict' if category == 'discrepancy' else 'observed'),
            'category': category, 'record_proofs': proofs}


def _values(rows):
    return '; '.join(f'{json.dumps(r["value"], ensure_ascii=False)}'
        f'{" " + r["unit"] if r.get("unit") else ""} '
        f'({r.get("occurred_on") or "date not recorded"})' for r in rows)


def _supported(view, rows, verification):
    return all(verify_claim(make_claim(view, [r]), view, context=verification)['status'] == 'SUPPORTED' for r in rows)


def _discrepancies(view, selected, verification):
    """One-hop related evidence only; aliases are exact code-owned mappings."""
    requested = {(test_key(r), r['date']) for r in selected
        if r['kind'] == 'measurement' and r.get('date') and r.get('date_precision', 'day') == 'day'}
    buckets = defaultdict(list)
    for row in view['facts'] + view['undated_facts']:
        key = (test_key(row), row.get('date'))
        if (key in requested and row.get('date_precision', 'day') == 'day'
                and not row.get('value_withheld') and row.get('within_date_scope') is not False):
            buckets[key].append(row)
    findings, companions = [], {}
    for (_, day), rows in sorted(buckets.items()):
        if len(rows) < 2:
            continue
        rows = sorted(rows, key=lambda r: r['id'])
        units = {r.get('unit') for r in rows}
        values = [numeric_value(r['value']) for r in rows]
        numeric = len(units) == 1 and None not in units and all(v is not None for v in values)
        differs = len({Decimal(v) for v in values}) > 1 if numeric else len({r['value'] for r in rows}) > 1
        if len(units) == 1 and not differs:
            continue
        companions.update({r['id']: r for r in rows})
        if len(companions) > MAX_EVIDENCE_FACTS:
            raise ValueError('Related discrepancies exceed the 64-record evidence limit. Use the record comparison; no companion evidence was silently omitted.')
        label = json.dumps(rows[0]['label'], ensure_ascii=False)
        if not _supported(view, rows, verification):
            text = f'{label}, {day}: a related recorded discrepancy needs review, but an original excerpt is unavailable. No supported value comparison is stated.'
        else:
            reason = ('different printed units; no conversion is performed' if len(units) > 1 else
                'different recorded numbers' if numeric else 'different recorded wording or qualifiers; no numerical comparison is performed')
            text = f'{label}, {day}: {reason}: {_values(rows)}. These records stay separate; sample equivalence is unknown and neither is chosen as correct.'
        findings.append(_claim(view, INSPECT, 'discrepancy', text, rows))
    return findings, list(companions.values())


def prepare_reports(context, source_ids, *, snapshot_id=None):
    """Prepare bounded, immutable tool results before any optional provider call."""
    # A withheld excerpt must never enter a provider payload even if a caller
    # accidentally retained its text alongside the projection flag.
    view = context['view']
    if any(r.get('source_quote_withheld') and (r.get('source_quote') or r.get('date_evidence'))
           for r in view['facts'] + view['undated_facts']):
        view = deepcopy(view)
        for row in view['facts'] + view['undated_facts']:
            if row.get('source_quote_withheld'):
                row.update(source_quote=None, date_evidence=None)
        context = {**context, 'view': view}
    pair_rows = [r for r in view['facts'] + view['undated_facts'] if r['source_id'] in source_ids]
    if len(pair_rows) > MAX_PAIR_FACTS:
        raise ValueError('This pair exceeds the 48-record investigation limit. Use the paged report comparison; no partial investigation was generated.')
    summary = summarize_sources(view, source_ids, snapshot_id=snapshot_id)
    rows = summary['history_evidence']['facts'] + summary['history_evidence']['undated_facts']
    by_id = {r['id']: r for r in rows}
    verification = VerificationContext(view)
    claims, counts = [], defaultdict(int)
    for group in summary['rows']:
        left = [by_id[key] for key in group['current_ids']]
        right = [by_id[key] for key in group['previous_ids']]
        records = left + right
        label = json.dumps(group['label'], ensure_ascii=False)
        supported = _supported(view, records, verification)
        if not supported:
            category = 'needs_context'
            text = f'{label}: an original excerpt is unavailable in this view. I cannot verify this comparison; inspect the saved records.'
        elif group['difference'] is not None:
            delta = group['difference']
            category = 'changed' if Decimal(delta) != 0 else 'same_number'
            signed = ('+' if Decimal(delta) > 0 else '') + delta
            text = (f'{label}: {_values(right)} → {_values(left)}. '
                f'Recorded difference: {signed} {group["unit"]} (selected report minus comparison report).')
        elif not left or not right:
            category = 'one_report_only'
            side = 'selected' if left else 'comparison'
            text = (f'{label}: {_values(records)}, only in the {side} report among this pair. '
                'No matching reviewed entry was found in the other selected file; this does not establish missed testing or care.')
        else:
            category = 'needs_context'
            text = (f'{label}: comparison report {_values(right)}; selected report {_values(left)}. '
                + ' '.join(group['notes']))
        counts[category] += 1
        claims.append(_claim(view, COMPARE, category, text, records))
    issues, companions = _discrepancies(view, rows, verification)
    all_rows = {r['id']: r for r in rows + companions}
    if len(all_rows) > MAX_EVIDENCE_FACTS:
        raise ValueError('Related discrepancies exceed the 64-record evidence limit. Use the record comparison; no companion evidence was silently omitted.')
    titles = [summary['current_source']['title'], summary['previous_source']['title']]
    overview = (f'Compared {json.dumps(titles[0], ensure_ascii=False)} with {json.dumps(titles[1], ensure_ascii=False)}: '
        f'{len(rows)} visible reviewed records; {counts["changed"]} numerical changes, '
        f'{counts["same_number"]} unchanged recorded numbers, {counts["needs_context"]} needing context, '
        f'{counts["one_report_only"]} entries found in only one report. '
        'Only compatible, source-supported results receive a numerical difference.')
    limitations = [note for note in summary['limitations']
        if note != 'Related discrepancies also involve other files. Open the Home conflict comparison to inspect those records.']
    if companions:
        limitations.append('Related copies are included in the discrepancy findings; open their linked sources to inspect each original.')
    overview += ' ' + ' '.join(limitations)
    claims.insert(0, _claim(view, COMPARE, 'coverage', overview, rows))
    if not issues:
        issues = [_claim(view, INSPECT, 'coverage',
            'No differing same-day measurement values or units were found for the tests and dates in this pair. '
            'This does not establish that all report text is consistent or that the sources are clinically equivalent.', rows)]
    reads = {}
    for name, findings, records in ((COMPARE, claims, rows), (INSPECT, issues, list(all_rows.values()))):
        reads[name] = {**evidence(view, records), 'claims': findings,
            'required_claim_ids': [c['id'] for c in findings], 'policy_version': summary['policy_version']}
        if len(json.dumps(reads[name], ensure_ascii=False).encode()) > MAX_RESULT_BYTES:
            raise ValueError('These report excerpts exceed the investigation context budget. Use the paged comparison; no evidence was truncated.')
    metadata = {'method': 'cross_report_investigation_v1',
        'selected_source_id': source_ids[0], 'comparison_source_id': source_ids[1],
        'selected_title': titles[0], 'comparison_title': titles[1], 'snapshot_id': snapshot_id,
        'counts': {**dict(counts), 'discrepancies': sum(c['category'] == 'discrepancy' for c in issues),
                   'reviewed_records': len(rows), 'evidence_records': len(all_rows)},
        'policy_version': summary['policy_version']}
    return {**context, 'report_investigation': {'reads': reads, 'metadata': metadata}}


def report_read(context, name):
    prepared = context.get('report_investigation')
    if not prepared or name not in REPORT_READS:
        raise ValueError('No owner-bound report pair is available')
    return deepcopy(prepared['reads'][name])

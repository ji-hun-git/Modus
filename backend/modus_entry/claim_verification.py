"""Exact claim verification against a server-owned history capture.

This proves consistency with reviewed records, not clinical truth or OCR accuracy.
Original excerpts may differ from reviewed amendments: both remain bound here.
No generic natural-language entailment or model inference is claimed.
"""
from copy import deepcopy
from hashlib import sha256
import json

from .comparison_rules import POLICY_VERSION, contextual_pair, comparison_context

PROOF_FIELDS = ('id', 'source_id', 'revision_id', 'kind', 'label', 'value', 'unit',
    'date', 'occurred_on', 'available_at', 'source_quote', 'page', 'bbox', 'date_evidence',
    'reference_range', 'specimen', 'test_method', 'facility', 'reviewed_fields',
    'value_withheld', 'source_quote_withheld', 'within_date_scope')
CLAIM_KEYS = {'id', 'type', 'scope_id', 'policy_version', 'evidence_ids', 'proofs', 'difference', 'text'}


def proof(row):
    return {key: deepcopy(row.get(key)) for key in PROOF_FIELDS}


def exact_proof(candidate, row):
    # Python dict equality treats True as 1. Preserve the JSON types as well as
    # the values of page numbers, source geometry and withheld flags.
    if type(candidate) is not dict:
        return False
    try:
        return json.dumps(candidate, sort_keys=True, allow_nan=False) == json.dumps(proof(row), sort_keys=True, allow_nan=False)
    except (TypeError, ValueError):
        return False


def record_text(row):
    value = json.dumps(row['value'], ensure_ascii=False)
    label = json.dumps(row['label'], ensure_ascii=False)
    unit = f" {row['unit']}" if row.get('unit') else ''
    day = row.get('occurred_on') or row.get('date') or 'not recorded'
    return f'Reviewed record: {label} — {value}{unit}. Recorded date: {day}.'


def difference_text(current, previous, delta):
    return (f"Recorded difference for {json.dumps(current['label'], ensure_ascii=False)}: "
            f"{delta} {current.get('unit') or ''} (selected result minus comparison result).")


def claim_id(payload):
    encoded = json.dumps({k: v for k, v in payload.items() if k != 'id'}, sort_keys=True,
                         ensure_ascii=False, separators=(',', ':')).encode()
    return 'claim:' + sha256(encoded).hexdigest()


def make_claim(view, rows, *, difference=None):
    is_difference = difference is not None
    payload = {'type': 'difference' if is_difference else 'record',
        'scope_id': view['scope']['scope_id'], 'policy_version': POLICY_VERSION,
        'evidence_ids': [r['id'] for r in rows], 'proofs': [proof(r) for r in rows],
        'difference': difference,
        'text': difference_text(*rows, difference) if is_difference else record_text(rows[0])}
    payload['id'] = claim_id(payload)
    return payload


class VerificationContext:
    """Server-private index for exactly one immutable capture, never a request field."""
    def __init__(self, view):
        self.view = view
        self.facts = {r['id']: r for r in view['facts'] + view['undated_facts']}
        self.sources = {s['id'] for s in view['sources']}
        self.comparisons = comparison_context(view)


def verify_claim(candidate, view, *, context=None):
    def result(status, code):
        return {'status': status, 'reason_codes': [code]}
    if not isinstance(candidate, dict) or set(candidate) != CLAIM_KEYS:
        return result('INSUFFICIENT_EVIDENCE', 'INVALID_CLAIM_SHAPE')
    if candidate['scope_id'] != view['scope']['scope_id']:
        return result('OUT_OF_SCOPE', 'SCOPE_MISMATCH')
    if candidate['policy_version'] != POLICY_VERSION:
        return result('INSUFFICIENT_EVIDENCE', 'POLICY_MISMATCH')
    ids, proofs = candidate['evidence_ids'], candidate['proofs']
    count = 1 if candidate['type'] == 'record' else 2 if candidate['type'] == 'difference' else 0
    if (not count or not isinstance(ids, list) or len(ids) != count or
            any(not isinstance(key, str) for key in ids) or len(set(ids)) != count or
            not isinstance(proofs, list) or len(proofs) != count):
        return result('INSUFFICIENT_EVIDENCE', 'INVALID_EVIDENCE')
    context = VerificationContext(view) if context is None else context
    if context.view is not view:
        return result('OUT_OF_SCOPE', 'VERIFICATION_CONTEXT_MISMATCH')
    visible, sources = context.facts, context.sources
    if any(key not in visible for key in ids):
        return result('OUT_OF_SCOPE', 'FACT_UNAVAILABLE')
    rows = [visible[key] for key in ids]
    if any(r['source_id'] not in sources or r.get('value_withheld') or
           r.get('within_date_scope') is False for r in rows):
        return result('OUT_OF_SCOPE', 'EVIDENCE_UNAVAILABLE')
    if any(not exact_proof(p, r) for p, r in zip(proofs, rows)):
        return result('CONTRADICTED', 'FACT_VERSION_OR_SOURCE_MISMATCH')
    if any(r.get('source_quote_withheld') or not (r.get('source_quote') or '').strip() for r in rows):
        return result('INSUFFICIENT_EVIDENCE', 'SOURCE_EXCERPT_UNAVAILABLE')
    if count == 2:
        checked = contextual_pair(view, *rows, context=context.comparisons)
        if checked['difference'] is None:
            return result('INSUFFICIENT_EVIDENCE', 'COMPARISON_NOT_SUPPORTED')
        if candidate['difference'] != checked['difference']:
            return result('CONTRADICTED', 'DIFFERENCE_MISMATCH')
        expected = difference_text(*rows, checked['difference'])
    else:
        if candidate['difference'] is not None:
            return result('CONTRADICTED', 'UNEXPECTED_DIFFERENCE')
        expected = record_text(rows[0])
    if candidate['text'] != expected:
        return result('CONTRADICTED', 'CLAIM_TEXT_MISMATCH')
    if candidate['id'] != claim_id(candidate):
        return result('CONTRADICTED', 'CLAIM_ID_MISMATCH')
    return result('SUPPORTED', 'EXACT_REVIEWED_EVIDENCE')

"""Narrow deterministic checks on explicitly captured synthetic pilot artifacts.

Exact trace membership is a structural check, not semantic entailment. It never
reads a product database, provider key, frozen corpus or benchmark answer key.
"""
import hashlib
import json
from pathlib import Path


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
        ensure_ascii=False).encode('utf-8')).hexdigest()


def verdict(artifact, status, reason):
    return {'status': status, 'reason': reason,
        'checker_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'artifact_sha256': fingerprint(artifact)}


def faithfulness(artifact):
    evidence = artifact.get('evidence', {})
    if not isinstance(evidence, dict) or 'answer_claims' not in evidence:
        return verdict(artifact, 'not_applicable', 'No generated factual answer in this artifact.')
    claims = evidence['answer_claims']
    pool = evidence.get('tool_claims', [])
    if not claims:
        return verdict(artifact, 'not_applicable', 'No factual claims; abstention is assessed separately in D.')
    if not all(isinstance(c, dict) and all(c.get(k) == p.get(k)
        for k in ('id', 'text', 'evidence_ids', 'tool_name'))
        for c in claims for p in [next((x for x in pool if isinstance(x, dict)
            and x.get('id') == c.get('id')), {})]):
        return verdict(artifact, 'fail', 'At least one selected claim differs from the captured typed-tool claim.')
    if artifact.get('final_answer') != ' '.join(c['text'] for c in claims):
        return verdict(artifact, 'ambiguous', 'Claims match exact typed-tool output; answer composition needs separate semantic review.')
    return verdict(artifact, 'pass', 'Every claim and the composed answer exactly match captured typed-tool output. Source entailment is not certified by this check.')


def extraction(artifact):
    evidence = artifact.get('evidence', {})
    if not isinstance(evidence, dict) or 'extracted_rows' not in evidence:
        return verdict(artifact, 'not_applicable', 'No extracted fields are scored in this artifact.')
    names = ('label', 'value', 'unit', 'occurred_on')
    def rows(items):
        return sorted(tuple(str(item.get(k)) for k in names) for item in items)
    actual, expected = evidence['extracted_rows'], evidence['authored_expected_rows']
    passed = rows(actual) == rows(expected)
    def linked(items):
        return [tuple(str(item.get(k)) for k in names[1:]) for item in items]
    left, right = linked(actual), linked(expected)
    if not passed and left and len(set(left)) == len(left) == len(right) and sorted(left) == sorted(right):
        return verdict(artifact, 'fuzzy', 'Values, units and dates have a unique exact alignment; only field labels differ. Semantic label alignment requires separate review.')
    return verdict(artifact, 'pass' if passed else 'fail',
        'Exact linked label/value/unit/date comparison against this separately authored pilot example; no clinical or held-out accuracy claim.')

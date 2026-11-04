"""Literal same-day record differences, never sample or clinical equivalence.

Formatting keys are comparison-only. Original strings, units and reviewed
metadata are retained in every evidence record and source proof.
"""
from decimal import Decimal
import json
import re

from modus.record_history_models import numeric_value

POLICY_VERSION = 'record-discrepancies-2026-11-04.1'
CONTEXT_FIELDS = (('unit', 'Printed unit'), ('specimen', 'Specimen'),
    ('test_method', 'Test method'), ('reference_range', 'Reference range'),
    ('facility', 'Lab or facility'))


def spacing(value):
    return ' '.join((value or '').split())


def value_key(value):
    """Only decimal formatting, equivalent bound glyphs and whitespace collapse.

    No unit conversions, word synonyms, case folding, range interpretation or
    arithmetic on qualified results. Distinct operators remain distinct.
    """
    text = spacing(value)
    numeric = numeric_value(text)
    if numeric is not None:
        return ('number', Decimal(numeric))
    bound = re.fullmatch(r'(<=|>=|<|>|≤|≥)\s*(.+)', text)
    if bound:
        numeric = numeric_value(bound[2])
        if numeric is not None:
            return ('bound', {'≤': '<=', '≥': '>='}.get(bound[1], bound[1]), Decimal(numeric))
    return ('text', text)


def differences(rows):
    """Return known differences separately from partly missing metadata."""
    reasons, fields, gaps = [], [], []
    values = [value_key(row['value']) for row in rows]
    if len(set(values)) > 1:
        reasons.append('different recorded numbers' if all(v[0] == 'number' for v in values)
            else 'different recorded wording or qualifiers')
    for key, title in CONTEXT_FIELDS:
        values = [spacing(row.get(key)) for row in rows]
        known = {value for value in values if value}
        if len(known) > 1:
            reasons.append('different printed units; no conversion is performed' if key == 'unit'
                else f'{title} differs as recorded')
            fields.append((key, title))
        if known and any(not value for value in values):
            gaps.append((key, title))
    return reasons, fields, gaps


def describe(rows, values):
    """Describe each known difference and context gap with its literal values."""
    reasons, fields, gaps = differences(rows)
    if not reasons and not gaps:
        return None
    details = []
    for key, title in dict(fields + gaps).items():
        # Keep row order aligned with the value list and evidence links.
        printed = [json.dumps(row[key], ensure_ascii=False) if spacing(row.get(key))
            else 'not recorded' for row in rows]
        details.append(f'{title}: ' + ' / '.join(printed))
    if reasons:
        text = '; '.join(reasons) + ': ' + values + '.'
        category = 'discrepancy'
    else:
        text = 'No differing recorded values or known lab metadata were found, but context is incomplete: ' + values + '.'
        category = 'needs_context'
    if details:
        text += ' ' + '; '.join(details) + '.'
    if gaps:
        text += ' Missing ' + ', '.join(title.lower() for _, title in gaps) + ' is unknown, not a contradiction.'
    text += ' No numerical difference is calculated. These records stay separate; sample equivalence is unknown and neither is chosen as correct.'
    return category, text

"""Small, explicit unit normalization for recorded facts, not clinical inference.

Original text is always retained. This is not a UCUM parser or a LOINC mapper.
Mass/amount conversions and HbA1c standardization conversions are not inferred.
"""
from decimal import Decimal, localcontext, ROUND_HALF_EVEN
from fractions import Fraction
import re
from typing import Literal, TypedDict
import unicodedata

from .ontology import exact_concept, LOINC_SYSTEM, resolve_codings

VERSION = 'modus-record-units-1.0.0-2026-10-28'
SI_SOURCE = 'https://www.nist.gov/pml/owm/metric-si-prefixes'
TEMPERATURE_SOURCE = 'https://www.nist.gov/pml/special-publication-811/nist-guide-si-appendix-b-conversion-factors/nist-guide-si-appendix-b8'
UCUM_SOURCE = 'https://ucum.org/ucum'
ALIASES = {
    'height': ('height', 'body height', 'standing height', '신장', '키'),
    'body_length': ('body length', 'recumbent length', '누운 키'),
    'weight': ('weight', 'body weight', '체중'),
    'body_temperature': ('temperature', 'body temperature', '체온'),
    'heart_rate': ('heart rate', 'pulse', 'pulse rate', 'hr', '심박수', '맥박', '맥박수'),
    'respiratory_rate': ('respiratory rate', 'respiration rate', '호흡수'),
    'systolic_bp': ('systolic blood pressure', 'systolic bp', 'sbp', '수축기 혈압', '수축기혈압'),
    'diastolic_bp': ('diastolic blood pressure', 'diastolic bp', 'dbp', '이완기 혈압', '이완기혈압'),
    'bmi': ('bmi', 'body mass index', '체질량지수', '체질량 지수'),
}
_POINT = re.compile(r'[+-]?(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+)(?:[eE][+-]?[0-9]{1,2})?\Z')


class OriginalValue(TypedDict):
    label: str
    value: str
    unit: str | None


class NormalizedValue(TypedDict):
    value: str
    unit: str
    numerator: str
    denominator: str
    display_is_exact: bool
    rounding: str | None


class Conversion(TypedDict):
    factor_numerator: str
    factor_denominator: str
    offset_numerator: str
    offset_denominator: str
    exact: bool
    source: str


class UnitResult(TypedDict):
    version: str
    original: OriginalValue
    normalized: NormalizedValue | None
    concept: str | None
    status: Literal['identity', 'converted', 'unresolved']
    reason: str
    conversion: Conversion | None


def _term(value):
    return ' '.join(unicodedata.normalize('NFC', value).casefold().split())


def recorded_concept(label):
    """Local exact-label family only; never assign a LOINC code or specimen."""
    known = exact_concept(label)
    if known:
        return known
    normalized = _term(label)
    return next((concept for concept, labels in ALIASES.items()
                 if normalized in {_term(alias) for alias in labels}), None)


def _rule(concept, unit):
    # Unit symbols remain case-sensitive. No broad lowercase/Unicode fold.
    if concept in ('height', 'body_length') and unit in ('m', 'cm', 'mm'):
        return 'cm', {'m': Fraction(100), 'cm': Fraction(1), 'mm': Fraction(1, 10)}[unit], Fraction(0), SI_SOURCE
    if concept == 'weight' and unit in ('kg', 'g'):
        return 'kg', Fraction(1) if unit == 'kg' else Fraction(1, 1000), Fraction(0), SI_SOURCE
    if concept == 'body_temperature':
        if unit in ('Cel', '°C', '℃'):
            return 'Cel', Fraction(1), Fraction(0), TEMPERATURE_SOURCE
        if unit in ('[degF]', '°F', '℉'):
            return 'Cel', Fraction(5, 9), Fraction(-160, 9), TEMPERATURE_SOURCE
    identities = {
        'heart_rate': {'/min', '1/min', 'min-1', 'bpm', 'beats/min', '회/분', '박/분'},
        'respiratory_rate': {'/min', '1/min', 'min-1', 'breaths/min', '회/분'},
        'systolic_bp': {'mm[Hg]', 'mmHg', 'mm Hg'},
        'diastolic_bp': {'mm[Hg]', 'mmHg', 'mm Hg'},
        'bmi': {'kg/m2', 'kg/m²', 'kg/m^2'},
    }
    if unit in identities.get(concept, set()):
        target = '/min' if concept in ('heart_rate', 'respiratory_rate') else 'kg/m2' if concept == 'bmi' else 'mm[Hg]'
        return target, Fraction(1), Fraction(0), UCUM_SOURCE
    # These labels identify the established local lab family, not assay equivalence.
    if concept == 'hba1c' and unit in ('%', 'mmol/mol'):
        return unit, Fraction(1), Fraction(0), 'https://loinc.org/4548-4'
    if concept == 'ldl' and unit in ('mg/dL', 'mmol/L'):
        return unit, Fraction(1), Fraction(0), UCUM_SOURCE
    if concept == 'egfr' and unit in ('mL/min/1.73m2', 'mL/min/1.73 m2', 'mL/min/1.73m²', 'mL/min/{1.73_m2}'):
        return 'mL/min/1.73m2', Fraction(1), Fraction(0), 'https://loinc.org/98979-8'
    return None


def _render(value):
    """Keep an exact rational plus a bounded decimal for display, never a float."""
    denominator = value.denominator
    twos = fives = 0
    while denominator % 2 == 0:
        denominator //= 2
        twos += 1
    while denominator % 5 == 0:
        denominator //= 5
        fives += 1
    exact = denominator == 1
    with localcontext() as context:
        context.prec = max(len(str(abs(value.numerator))) + max(twos, fives) + 2, 34) if exact else 34
        context.rounding = ROUND_HALF_EVEN
        text = format(Decimal(value.numerator) / Decimal(value.denominator), 'f')
    if '.' in text:
        text = text.rstrip('0').rstrip('.')
    return text, exact


def normalize_recorded_value(label: str, value_text: str, unit: str | None) -> UnitResult:
    """Normalize only an explicit known concept/unit and a whole point number.

    Unsupported units, unknown analytes, inequalities and ranges stay verbatim.
    Compare numerator/denominator for exact equality; decimal text may be rounded.
    Normalization does not establish specimen/method or clinical comparability.
    """
    if (not isinstance(label, str) or not isinstance(value_text, str)
            or unit is not None and not isinstance(unit, str)
            or len(label) > 200 or len(value_text) > 16000 or unit is not None and len(unit) > 80):
        raise ValueError('Recorded unit inputs must be bounded strings')
    concept = recorded_concept(label)
    result: UnitResult = {'version': VERSION, 'original': {'label': label, 'value': value_text, 'unit': unit},
        'normalized': None, 'concept': concept, 'status': 'unresolved', 'reason': 'unknown_concept', 'conversion': None}
    text = value_text.strip()
    if not _POINT.fullmatch(text):
        result['reason'] = 'not_a_point_number'
        return result
    if len(text) > 80:
        result['reason'] = 'numeric_precision_limit'
        return result
    if concept is None:
        return result
    if unit is None or not unit.strip():
        result['reason'] = 'missing_unit'
        return result
    if re.fullmatch(r'[0-9]{4,7}-[0-9]', label.strip()):
        coding = resolve_codings([{'system': LOINC_SYSTEM, 'code': label.strip()}], {'unit': unit.strip()})
        if coding['status'] != 'resolved':
            result['reason'] = 'unit_conflicts_with_recorded_code'
            return result
    rule = _rule(concept, unit.strip())
    if rule is None:
        result['reason'] = 'unit_not_configured_for_concept'
        return result
    source_value = Fraction(Decimal(text))
    target, factor, offset, source = rule
    converted = source_value * factor + offset
    display, display_exact = _render(converted)
    result.update(normalized={'value': display, 'unit': target, 'numerator': str(converted.numerator),
        'denominator': str(converted.denominator), 'display_is_exact': display_exact,
        'rounding': None if display_exact else '34 significant digits; round half even'},
        status='identity' if factor == 1 and offset == 0 else 'converted', reason='configured_exact_rule',
        conversion={'factor_numerator': str(factor.numerator), 'factor_denominator': str(factor.denominator),
            'offset_numerator': str(offset.numerator), 'offset_denominator': str(offset.denominator),
            'exact': True, 'source': source})
    return result

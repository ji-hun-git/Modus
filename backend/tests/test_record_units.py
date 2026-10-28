"""Exact recorded-unit transformations, preserving unsupported original text."""
from fractions import Fraction
import json

import pytest

from modus.record_units import normalize_recorded_value, recorded_concept


@pytest.mark.parametrize('label,value,unit,expected,target', [
    ('Height', '1.725', 'm', '172.5', 'cm'),
    ('신장', '1725', 'mm', '172.5', 'cm'),
    ('키', '172.50', 'cm', '172.5', 'cm'),
    ('body length', '0.51', 'm', '51', 'cm'),
    ('체중', '3200', 'g', '3.2', 'kg'),
    ('Body weight', '70.100', 'kg', '70.1', 'kg'),
    ('body temperature', '98.6', '°F', '37', 'Cel'),
    ('체온', '32', '[degF]', '0', 'Cel'),
    ('체온', '-40', '℉', '-40', 'Cel'),
    ('체온', '36.500', '℃', '36.5', 'Cel'),
    ('heart rate', '72', 'bpm', '72', '/min'),
    ('심박수', '72', '회/분', '72', '/min'),
    ('호흡수', '14', 'breaths/min', '14', '/min'),
    ('수축기혈압', '120', 'mmHg', '120', 'mm[Hg]'),
    ('diastolic blood pressure', '80', 'mm Hg', '80', 'mm[Hg]'),
    ('BMI', '22.10', 'kg/m²', '22.1', 'kg/m2'),
    ('HbA1c', '5.60', '%', '5.6', '%'),
    ('당화혈색소', '42', 'mmol/mol', '42', 'mmol/mol'),
    ('LDL', '100.00', 'mg/dL', '100', 'mg/dL'),
    ('LDL 콜레스테롤', '2.586', 'mmol/L', '2.586', 'mmol/L'),
    ('eGFR', '80.1234567', 'mL/min/1.73 m2', '80.1234567', 'mL/min/1.73m2'),
])
def test_known_exact_rules_preserve_original_and_never_use_float(label, value, unit, expected, target):
    result = normalize_recorded_value(label, value, unit)
    assert result['original'] == {'label': label, 'value': value, 'unit': unit}
    normalized = result['normalized']
    assert normalized['value'] == expected and normalized['unit'] == target
    assert normalized['display_is_exact'] and normalized['rounding'] is None
    assert Fraction(int(normalized['numerator']), int(normalized['denominator'])) == Fraction(expected)
    assert result['conversion']['exact'] is True
    assert json.loads(json.dumps(result)) == result


def test_fahrenheit_repeating_decimal_keeps_exact_fraction_and_explicit_display_rounding():
    result = normalize_recorded_value('Temperature', '99', '°F')
    normalized = result['normalized']
    assert result['status'] == 'converted'
    assert normalized['numerator'] == '335' and normalized['denominator'] == '9'
    assert normalized['display_is_exact'] is False
    assert normalized['value'] == '37.22222222222222222222222222222222'
    assert normalized['rounding'] == '34 significant digits; round half even'
    assert result['conversion']['factor_numerator'] == '5'
    assert result['conversion']['factor_denominator'] == '9'
    assert result['conversion']['offset_numerator'] == '-160'


@pytest.mark.parametrize('value', ['<5.6', '> 5.6', '≤5.6', '5.6–6.4', '5.6-6.4', '5.6 ± 0.2',
    'less than 5.6', '5.6 미만', '5,6', '1,234', '120/80', 'NaN', 'Infinity', '', ' ', '5.6 %'])
def test_qualified_ambiguous_and_nonpoint_values_are_not_coerced(value):
    result = normalize_recorded_value('HbA1c', value, '%')
    assert result['normalized'] is None and result['status'] == 'unresolved'
    assert result['reason'] == 'not_a_point_number'
    assert result['original']['value'] == value


@pytest.mark.parametrize('label,unit,reason', [
    ('glucose', 'mg/dL', 'unknown_concept'), ('포도당', 'mmol/L', 'unknown_concept'),
    ('creatinine', 'mg/dL', 'unknown_concept'), ('ALT', 'U/L', 'unknown_concept'),
    ('LDL', 'g/L', 'unit_not_configured_for_concept'),
    ('weight', 'mg/dL', 'unit_not_configured_for_concept'),
    ('height', 'CM', 'unit_not_configured_for_concept'),
    ('weight', 'KG', 'unit_not_configured_for_concept'),
    ('temperature', 'C', 'unit_not_configured_for_concept'),
    ('HbA1c', '1', 'unit_not_configured_for_concept'),
    ('HbA1c', None, 'missing_unit'), ('BMI', '', 'missing_unit'),
])
def test_unknown_analytes_units_and_missing_units_preserve_text(label, unit, reason):
    result = normalize_recorded_value(label, '5.6', unit)
    assert result['normalized'] is None and result['conversion'] is None
    assert result['status'] == 'unresolved' and result['reason'] == reason
    assert result['original'] == {'label': label, 'value': '5.6', 'unit': unit}


def test_molecular_and_standardization_units_do_not_cross_convert():
    ldl = normalize_recorded_value('LDL', '100', 'mg/dL')
    hba1c = normalize_recorded_value('HbA1c', '6.5', '%')
    assert ldl['normalized']['value'] == '100' and ldl['normalized']['unit'] == 'mg/dL'
    assert hba1c['normalized']['value'] == '6.5' and hba1c['normalized']['unit'] == '%'
    assert ldl['status'] == hba1c['status'] == 'identity'


@pytest.mark.parametrize('code,unit,resolved', [('59261-8', 'mmol/mol', True), ('59261-8', '%', False),
    ('4548-4', '%', True), ('4548-4', 'mmol/mol', False), ('13457-7', 'mmol/L', False)])
def test_existing_explicit_code_must_keep_its_unit_semantics(code, unit, resolved):
    result = normalize_recorded_value(code, '5.6', unit)
    assert (result['normalized'] is not None) is resolved
    if not resolved:
        assert result['reason'] == 'unit_conflicts_with_recorded_code'


def test_exact_label_aliases_do_not_invent_codes_or_merge_height_and_recumbent_length():
    assert recorded_concept(' BODY   HEIGHT ') == 'height'
    assert recorded_concept('body length') == 'body_length'
    assert recorded_concept('weight loss') is None
    assert recorded_concept('HbA1c estimate') is None
    result = normalize_recorded_value('height', '170', 'cm')
    assert 'loinc' not in result and 'code' not in result


def test_original_precision_spacing_and_scientific_notation_are_retained():
    result = normalize_recorded_value(' 체중 ', ' 3.2000e3 ', ' g ')
    assert result['original'] == {'label': ' 체중 ', 'value': ' 3.2000e3 ', 'unit': ' g '}
    assert result['normalized']['value'] == '3.2' and result['normalized']['denominator'] == '5'
    precise = '123456789.123456789123456789123456789123456789'
    converted = normalize_recorded_value('height', precise, 'm')['normalized']
    assert Fraction(converted['value']) == Fraction(precise) * 100
    assert converted['display_is_exact'] is True


@pytest.mark.parametrize('label,value,unit', [(None, '1', 'cm'), ('height', 1.2, 'cm'),
    ('height', True, 'cm'), ('height', '1', {}), ('x' * 201, '1', 'cm'),
    ('height', '1' * 16001, 'cm'), ('height', '1', 'x' * 81)])
def test_nonstring_or_oversized_input_rejected_without_lossy_cast(label, value, unit):
    with pytest.raises(ValueError):
        normalize_recorded_value(label, value, unit)


def test_numeric_resources_are_bounded():
    assert normalize_recorded_value('height', '1' * 81, 'cm')['reason'] == 'numeric_precision_limit'
    assert normalize_recorded_value('height', '1e9999999', 'cm')['reason'] == 'not_a_point_number'
    value = normalize_recorded_value('height', '1e99', 'm')['normalized']['value']
    assert len(value) == 102
    preserved = normalize_recorded_value('height', 'unparsed source ' * 100, 'cm')
    assert preserved['normalized'] is None and len(preserved['original']['value']) > 800

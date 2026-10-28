"""Artificial terminology/provenance cases, independent of evaluation corpora."""
from copy import deepcopy
from datetime import datetime
import json

import pytest

from modus.ingest import make_draft, metric_key, parse_fhir, NoObservationsError
from modus.ontology import (CATALOG_VERSION, LOINC_SYSTEM, MODUS_METRIC_CODE_SYSTEM,
    UCUM_SYSTEM, concept_terms, resolve_concepts, resolve_codings, recorded_unit,
    resolve_query_constraints, qualified_observation_semantics, fhir_semantic_export)
from modus.record_models import Observation
from modus.record_store import RecordStore


def source(code='18262-6', *, unit='mg/dL', value=117, status='final', measured='2026-02-10'):
    return {'resourceType': 'Observation', 'id': 'original-id', 'status': status,
        'subject': {'reference': 'Patient/demo-alex'},
        'code': {'coding': [{'system': LOINC_SYSTEM, 'code': code, 'version': 'source-version',
                            'display': 'Original source label', 'userSelected': True}], 'text': 'Recorded source concept'},
        'valueQuantity': {'value': value, 'unit': unit, 'system': UCUM_SYSTEM, 'code': unit},
        'effectiveDateTime': measured, 'issued': '2026-02-11T18:00:00+09:00'}


def raw_bundle(*resources):
    return json.dumps({'resourceType': 'Bundle', 'type': 'collection',
                       'entry': [{'resource': resource} for resource in resources]}, ensure_ascii=False).encode()


def draft_for(*resources):
    return make_draft('source.json', raw_bundle(*resources))


def record_store(tmp_path):
    return RecordStore(tmp_path / 'ontology.db', seed_provider=lambda: ([], []),
        application_id='ontology-test-v1', require_review=False)


@pytest.mark.parametrize('query,expected', [
    ('Show my hemoglobin A1c records', ['hba1c']), ('당화혈색소를 보여줘', ['hba1c']),
    ('추정사구체여과율 기록', ['egfr']), ('LDL 콜레스테롤', ['ldl']),
    ('HbA1c and eGFR and LDL', ['hba1c', 'egfr', 'ldl']), ('98979-8 records', ['egfr']),
    ('cholesterol', []), ('콜레스테롤', []), ('혈당', []), ('kidney', []),
    ('HDL cholesterol', []), ('notldl', []), ('비당화혈색소', []),
])
def test_safe_concept_aliases_do_not_guess_broader_terms(query, expected):
    assert resolve_concepts(query) == expected


def test_concept_terms_are_stable_copies_and_exact_metric_lookup_stays_narrow():
    terms = concept_terms('ldl')
    assert '18262-6' in terms and '저밀도지단백 콜레스테롤' in terms
    terms.append('invented')
    assert 'invented' not in concept_terms('ldl')
    assert concept_terms('glucose') == []
    assert metric_key('당화혈색소') == 'hba1c'
    assert metric_key('LDL and eGFR') is None


@pytest.mark.parametrize('code,metric,method,unit', [
    ('17856-6', 'hba1c', 'hplc', '%'),
    ('59261-8', 'hba1c', 'unspecified', 'mmol/mol'),
    ('33914-3', 'egfr', 'creatinine_mdrd', 'mL/min/1.73m2'),
    ('77147-7', 'egfr', 'creatinine_mdrd', 'mL/min/1.73m2'),
    ('62238-1', 'egfr', 'creatinine_ckd_epi_2009', 'mL/min/1.73m2'),
    ('98979-8', 'egfr', 'creatinine_ckd_epi_2021', 'mL/min/1.73m2'),
    ('13457-7', 'ldl', 'calculated', 'mg/dL'),
    ('18262-6', 'ldl', 'direct_assay', 'mg/dL'),
])
def test_catalog_preserves_method_property_specimen_distinctions(code, metric, method, unit):
    result = resolve_codings([{'system': LOINC_SYSTEM, 'code': code}], {'unit': unit})
    assert result['status'] == 'resolved' and result['metric'] == metric
    assert result['matches'][0]['method'] == method
    assert result['matches'][0]['source'] == 'https://loinc.org/' + code
    if code == '33914-3':
        assert result['matches'][0]['code_status'] == 'discouraged'
        assert result['matches'][0]['specimen'] == 'serum_or_plasma'
    if code == '59261-8':
        assert result['matches'][0]['standardization'] == 'ifcc'
        assert result['matches'][0]['property'] == 'substance_fraction'


@pytest.mark.parametrize('codes', [('18262-6', '13457-7'), ('98979-8', '33914-3'), ('4548-4', '18262-6')])
def test_conflicting_codings_never_choose_first(codes):
    codings = [{'system': LOINC_SYSTEM, 'code': code} for code in codes]
    forward = resolve_codings(codings, {'unit': 'mg/dL'})
    reverse = resolve_codings(list(reversed(codings)), {'unit': 'mg/dL'})
    assert forward['status'] == reverse['status'] == 'conflicting'
    assert forward['metric'] is reverse['metric'] is None
    observation = source()
    observation['code']['coding'] = codings
    rows, warnings = parse_fhir(json.loads(raw_bundle(observation)))
    assert rows == [] and any('no coding was selected' in warning for warning in warnings)


def test_unknown_coding_display_cannot_grant_a_mapping():
    result = resolve_codings([{'system': 'https://unknown.invalid', 'code': '18262-6', 'display': 'LDL'}], {'unit': 'mg/dL'})
    assert result['status'] == 'unresolved' and result['metric'] is None


def test_generic_hba1c_code_does_not_establish_standardization():
    result = resolve_codings([{'system': LOINC_SYSTEM, 'code': '4548-4'}], {'unit': '%'})
    assert result['matches'][0]['standardization'] == 'unspecified'


@pytest.mark.parametrize('field,payload', [('method', {'text': 'calculated'}),
                                         ('specimen', {'display': 'Urine', 'reference': 'Specimen/1'})])
def test_source_method_or_specimen_contradiction_disqualifies_coded_export(field, payload):
    original = source()
    original[field] = payload
    row = draft_for(original)['observations'][0]
    assert row['fhir_provenance']['resolution']['status'] == 'conflicting'
    assert row['fhir_provenance']['original_' + field] is not None
    assert qualified_observation_semantics(row) is None
    assert fhir_semantic_export(row)['code']['coding'][0]['system'] == MODUS_METRIC_CODE_SYSTEM


def test_unit_identities_are_case_sensitive_and_never_converted():
    assert recorded_unit({'unit': 'mg/dL'})['identity'] == 'mg/dL'
    assert recorded_unit({'unit': 'mmol/L'})['identity'] == 'mmol/L'
    assert recorded_unit({'unit': 'MG/DL'})['status'] == 'unrecognized'
    assert recorded_unit({'unit': 'mL/min/{1.73_m2}'})['identity'] == 'mL/min/1.73m2'
    assert recorded_unit({'unit': 'mg/dL', 'system': UCUM_SYSTEM, 'code': 'mmol/L'})['status'] == 'conflicting'
    assert recorded_unit({'unit': 'mg/dL', 'system': 'https://unknown.invalid', 'code': 'mg/dL'})['status'] == 'unrecognized'


@pytest.mark.parametrize('code,unit', [('18262-6', 'mmol/L'), ('4548-4', 'mmol/mol')])
def test_wrong_unit_code_keeps_source_assertion_but_does_not_qualify_mapping(code, unit):
    row = draft_for(source(code, unit=unit, value=3))['observations'][0]
    assert row['fhir_provenance']['resolution']['status'] == 'unit_mismatch'
    assert row['unit'] == unit and row['value'] == 3
    assert qualified_observation_semantics(row) is None
    exported = fhir_semantic_export(row)
    assert exported['code']['coding'][0]['system'] == MODUS_METRIC_CODE_SYSTEM
    assert exported['valueQuantity'] == {'unit': unit, 'value': 3}
    assert exported['status'] == 'unknown'


def test_allowlisted_fhir_metadata_roundtrip_preserves_source_without_inventing_fields():
    original = source(measured='2026-02-10T08:30:00+09:00')
    original['code']['coding'].append({'system': 'https://local-lab.invalid', 'code': 'LAB42',
        'display': 'Unsupported coding retained as data', 'version': 'v2', 'userSelected': False})
    original['method'] = {'coding': [{'system': 'https://lab-method.invalid', 'code': 'M1'}], 'text': 'Recorded technique'}
    original['specimen'] = {'reference': 'Specimen/original-tube', 'type': 'Specimen',
        'display': 'Original source specimen', 'identifier': {'system': 'https://lab.invalid/tubes', 'value': 'tube-7'}}
    row = draft_for(original)['observations'][0]
    resolution = qualified_observation_semantics(row)
    assert resolution['catalog_version'] == CATALOG_VERSION and resolution['matches'][0]['method'] == 'direct_assay'
    exported = fhir_semantic_export(row)
    for field in ('code', 'status', 'method', 'specimen', 'valueQuantity', 'effectiveDateTime', 'issued'):
        assert exported[field] == original[field]


def test_unknown_extra_fields_are_not_promoted_to_export_authority():
    original = source()
    original['code']['arbitrary'] = {'command': 'untrusted'}
    original['code']['coding'][0]['extra'] = 'untrusted'
    original['valueQuantity']['extension'] = [{'url': 'https://untrusted.invalid/authority'}]
    original['contained'] = [{'resourceType': 'Binary', 'data': 'untrusted'}]
    exported = fhir_semantic_export(draft_for(original)['observations'][0])
    assert 'arbitrary' not in exported['code']
    assert 'extra' not in exported['code']['coding'][0]
    assert 'extension' not in exported['valueQuantity']
    assert 'contained' not in exported


@pytest.mark.parametrize('field,new_value', [('metric', 'hba1c'), ('value', 118), ('unit', 'mmol/L'), ('date', '2026-02-12')])
def test_reviewed_field_changes_invalidate_original_clinical_export(tmp_path, field, new_value):
    memory = record_store(tmp_path)
    draft = draft_for(source())
    memory.add_draft(draft)
    row = draft['observations'][0]
    reviewed = {key: row[key] for key in ('id', 'metric', 'value', 'unit', 'date')}
    reviewed[field] = new_value
    memory.commit_draft(draft['id'], [reviewed])
    committed = next(item for item in memory.snapshot().observations() if item['id'] == row['id'])
    assert qualified_observation_semantics(committed) is None
    exported = fhir_semantic_export(committed)
    assert exported['code']['coding'][0]['system'] == MODUS_METRIC_CODE_SYSTEM
    assert exported['status'] == 'unknown'
    assert 'method' not in exported and 'specimen' not in exported
    assert exported['valueQuantity']['value'] == committed['value']
    assert exported['effectiveDateTime'] == committed['date']


def test_basis_mismatch_is_rejected_even_without_review_flag():
    row = draft_for(source())['observations'][0]
    row['value'] = 999
    assert qualified_observation_semantics(row) is None
    assert fhir_semantic_export(row)['status'] == 'unknown'


def test_forged_provenance_in_free_json_or_model_rows_is_not_accepted():
    authentic = draft_for(source())['observations'][0]
    supplied = {key: authentic[key] for key in ('metric', 'value', 'unit', 'date', 'fhir_provenance')}
    generic = make_draft('generic.json', json.dumps({'observations': [supplied]}).encode())['observations'][0]
    model = make_draft('model.png', b'not an executed model', extracted=[supplied])['observations'][0]
    assert 'fhir_provenance' not in generic and 'fhir_provenance' not in model


@pytest.mark.parametrize('mutation', ['long_text', 'too_many_codes', 'nested_text', 'long_method', 'long_reference'])
def test_oversized_or_malformed_source_metadata_does_not_get_truncated_into_validity(mutation):
    original = source()
    if mutation == 'long_text': original['code']['text'] = 'a' * 2001
    elif mutation == 'too_many_codes': original['code']['coding'] *= 33
    elif mutation == 'nested_text': original['code']['text'] = {'nested': {'not': 'text'}}
    elif mutation == 'long_method': original['method'] = {'text': 'a' * 2001}
    elif mutation == 'long_reference': original['specimen'] = {'reference': 'x' * 501}
    with pytest.raises(NoObservationsError):
        draft_for(original)


def test_partial_historical_source_withholds_metadata_as_well_as_excerpt(tmp_path):
    memory = record_store(tmp_path)
    memory.clock = lambda: datetime.fromisoformat('2026-10-28T09:00:00+00:00')
    early = source(measured='2026-02-10')
    early['code']['text'] = 'Later details contained in an earlier row metadata field'
    later = source(code='4548-4', value=5.6, unit='%', measured='2026-09-10')
    draft = draft_for(early, later)
    memory.add_draft(draft)
    memory.commit_draft(draft['id'])
    key = draft['observations'][0]['id']
    view = memory.snapshot()
    partial = next(row for row in view.observations('2026-03-01') if row['id'] == key)
    assert partial['source_span_withheld'] is True
    assert 'fhir_provenance' not in partial
    assert qualified_observation_semantics(partial) is None
    full = next(row for row in view.observations('2026-10-01') if row['id'] == key)
    assert full['fhir_provenance']['original_code']['text'] == early['code']['text']
    resource = fhir_semantic_export(partial)
    assert resource['code']['coding'][0]['system'] == MODUS_METRIC_CODE_SYSTEM
    assert 'Later details' not in json.dumps(resource)
    before = memory.snapshot('2026-10-27T09:00:00Z')
    assert all(row['id'] != key for row in before.observations())


def test_legacy_observation_without_metadata_remains_compatible():
    row = {'id': 'legacy', 'source_id': 'source', 'metric': 'ldl', 'value': 117,
           'unit': 'mg/dL', 'date': '2026-02-10', 'source_span': 'LDL 117 mg/dL 2026-02-10'}
    assert Observation.model_validate(row).fhir_provenance is None
    assert qualified_observation_semantics(row) is None
    assert fhir_semantic_export(row)['status'] == 'unknown'


def test_query_qualifiers_are_explicit_and_do_not_infer_formula_or_method():
    assert resolve_query_constraints('direct LDL mg/dL')['methods'] == ['direct_assay']
    assert resolve_query_constraints('eGFR CKD-EPI 2021')['methods'] == ['creatinine_ckd_epi_2021']
    assert resolve_query_constraints('eGFR CKD-EPI')['ambiguous'] is True
    assert resolve_query_constraints('eGFR cystatin C')['unsupported'] is True
    assert resolve_query_constraints('18262-6')['loinc_codes'] == ['18262-6']
    assert resolve_query_constraints('99999-9')['unsupported'] is True
    assert resolve_query_constraints('당화혈색소 IFCC mmol/mol')['standardizations'] == ['ifcc']

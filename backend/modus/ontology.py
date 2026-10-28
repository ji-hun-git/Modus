"""Small, versioned record terminology. This is lookup, not clinical inference.

LOINC definitions checked against https://loinc.org/<code> on 2026-10-28.
Units are recorded identities; no arithmetic conversion or UCUM parser is implied.
The catalog identifies three record concepts, not diagnoses or treatment rules.
"""
from copy import deepcopy
import re
import unicodedata

CATALOG_VERSION = 'modus-record-terminology-1.0.0-2026-10-28'
LOINC_SYSTEM = 'http://loinc.org'
UCUM_SYSTEM = 'http://unitsofmeasure.org'
MODUS_METRIC_CODE_SYSTEM = 'https://modus.example/fhir/CodeSystem/record-metric'

_CONCEPTS = {
    'hba1c': ('HbA1c', 'Hb A1c', 'A1c', 'hemoglobin A1c', 'haemoglobin A1c',
              'glycated hemoglobin', 'glycated haemoglobin', '당화혈색소', '당화 헤모글로빈'),
    'egfr': ('eGFR', 'estimated glomerular filtration rate', '추정 사구체 여과율',
             '추정 사구체여과율', '추정사구체여과율'),
    'ldl': ('LDL', 'LDL-C', 'LDL cholesterol', 'low density lipoprotein cholesterol',
            'low-density lipoprotein cholesterol', 'LDL 콜레스테롤', '저밀도 지단백 콜레스테롤',
            '저밀도지단백 콜레스테롤'),
}


def _term(metric, property, specimen, method='unspecified', standardization='unspecified',
          units=(), code_status='active'):
    return {'metric': metric, 'property': property, 'specimen': specimen, 'method': method,
            'standardization': standardization, 'units': units, 'code_status': code_status}


_LOINC = {
    '4548-4': _term('hba1c', 'mass_fraction', 'blood', units=('%',)),
    '17856-6': _term('hba1c', 'mass_fraction', 'blood', 'hplc', units=('%',)),
    '59261-8': _term('hba1c', 'substance_fraction', 'blood', standardization='ifcc', units=('mmol/mol',)),
    '33914-3': _term('egfr', 'volume_rate_per_area', 'serum_or_plasma', 'creatinine_mdrd',
                     units=('mL/min/1.73m2',), code_status='discouraged'),
    '77147-7': _term('egfr', 'volume_rate_per_area', 'serum_plasma_or_blood', 'creatinine_mdrd', units=('mL/min/1.73m2',)),
    '62238-1': _term('egfr', 'volume_rate_per_area', 'serum_plasma_or_blood', 'creatinine_ckd_epi_2009', units=('mL/min/1.73m2',)),
    '98979-8': _term('egfr', 'volume_rate_per_area', 'serum_plasma_or_blood', 'creatinine_ckd_epi_2021', units=('mL/min/1.73m2',)),
    '13457-7': _term('ldl', 'mass_concentration', 'serum_or_plasma', 'calculated', units=('mg/dL',)),
    '18262-6': _term('ldl', 'mass_concentration', 'serum_or_plasma', 'direct_assay', units=('mg/dL',)),
}
# Official short names accompany the identifiers; local dimensions above are
# explicitly Modus annotations, not renamed LOINC fields or a new code standard.
# Attribution/license: https://loinc.org/license (see project third-party notices).
_LOINC_NAMES = {
    '4548-4': 'HbA1c MFr Bld', '17856-6': 'HbA1c MFr Bld HPLC',
    '59261-8': 'HbA1c per IFCC-RMP for CDT SFr Bld',
    '33914-3': 'GFR SerPl Creatinine-bsd frml MDRD',
    '77147-7': 'GFRSerPlBld MDRD-ArVRat',
    '62238-1': 'GFR SerPlBld Creatinine-bsd fmla CKD-EPI',
    '98979-8': 'eGFRcr SerPlBld CKD-EPI 2021',
    '13457-7': 'LDLc SerPl Calc-mCnc', '18262-6': 'LDLc SerPl Direct Assay-mCnc',
}
_UNIT_IDENTITIES = {
    '%': '%', 'mmol/mol': 'mmol/mol', 'mg/dL': 'mg/dL', 'mmol/L': 'mmol/L',
    'mL/min/1.73m2': 'mL/min/1.73m2', 'mL/min/1.73 m2': 'mL/min/1.73m2',
    'mL/min/1.73m²': 'mL/min/1.73m2', 'mL/min/{1.73_m2}': 'mL/min/1.73m2',
}


def _normalize(value):
    return re.sub(r'\s+', ' ', unicodedata.normalize('NFC', value).casefold()).strip()


def concept_terms(metric):
    """Return safe lookup aliases and exact catalog codes, as an independent list."""
    if metric not in _CONCEPTS:
        return []
    return list(dict.fromkeys((metric, *_CONCEPTS[metric],
                              *(code for code, term in _LOINC.items() if term['metric'] == metric))))


def exact_concept(value):
    """Recognize a whole label/code only; broad words such as glucose are not aliases."""
    if not isinstance(value, str):
        return None
    text = _normalize(value)
    matches = [metric for metric in _CONCEPTS if text in {_normalize(term) for term in concept_terms(metric)}]
    return matches[0] if len(matches) == 1 else None


def resolve_concepts(query):
    """Return concept IDs mentioned by bounded English/Korean aliases; never infer health."""
    if not isinstance(query, str):
        return []
    text = _normalize(query)
    found = []
    for metric in _CONCEPTS:
        for term in concept_terms(metric):
            suffix = r'(?:의|을|를|은|는|이|가|와|과|도|만|에|에서|로|으로)?' if re.search('[가-힣]', term) else ''
            if re.search(r'(?<!\w)' + re.escape(_normalize(term)) + suffix + r'(?!\w)', text):
                found.append(metric)
                break
    return found


def recorded_unit(quantity):
    """Identify supported spellings without conversion; unknown code systems stay unknown."""
    q = quantity if isinstance(quantity, dict) else {}
    raw, system, code = q.get('unit'), q.get('system'), q.get('code')
    display_identity = _UNIT_IDENTITIES.get(raw) if isinstance(raw, str) else None
    coded_identity = _UNIT_IDENTITIES.get(code) if system == UCUM_SYSTEM and isinstance(code, str) else None
    status, identity = 'unrecognized', None
    if not raw and not code:
        status = 'missing'
    elif code:
        if system == UCUM_SYSTEM and coded_identity:
            if display_identity and display_identity != coded_identity:
                status = 'conflicting'
            else:
                status, identity = 'recognized', coded_identity
    elif display_identity:
        status, identity = 'recognized', display_identity
    return {'raw_unit': raw, 'system': system, 'code': code, 'identity': identity, 'status': status}


def resolve_codings(codings, quantity=None):
    """Resolve all exact recognized codings; never pick the first clinical variant.

    A unit problem retains a known coarse category but does not qualify a clinical
    mapping. More than one distinct LOINC code is conservatively unresolved,
    even when a future terminology service could establish an equivalence.
    """
    matches, concepts, clinical_codes, issues = [], set(), set(), []
    for coding in codings if isinstance(codings, list) else []:
        if not isinstance(coding, dict):
            continue
        system, code = coding.get('system'), coding.get('code')
        if not isinstance(code, str):
            continue
        if system == LOINC_SYSTEM and code in _LOINC:
            term = _LOINC[code]
            if code not in clinical_codes:
                matches.append({'system': system, 'code': code, 'display': _LOINC_NAMES[code],
                                **{k: v for k, v in term.items() if k != 'units'},
                                'source': 'https://loinc.org/' + code})
            clinical_codes.add(code)
            concepts.add(term['metric'])
        elif system == MODUS_METRIC_CODE_SYSTEM and code in _CONCEPTS:
            concepts.add(code)
    ordered = [metric for metric in _CONCEPTS if metric in concepts]
    unit = recorded_unit(quantity)
    status, metric = 'unresolved', None
    if len(concepts) > 1 or len(clinical_codes) > 1:
        status = 'conflicting'
        issues.append('Distinct recognized concepts or clinical variants require review; no coding was selected.')
    elif len(concepts) == 1:
        metric = ordered[0]
        if unit['status'] != 'recognized':
            status = 'unit_mismatch' if unit['status'] == 'conflicting' else 'unit_unresolved'
            issues.append('Recorded unit identity is conflicting or unrecognized; no conversion or coding repair was inferred.')
        elif clinical_codes and unit['identity'] not in _LOINC[next(iter(clinical_codes))]['units']:
            status = 'unit_mismatch'
            issues.append('Recorded unit is incompatible with the recognized clinical code in this bounded catalog.')
        else:
            status = 'resolved'
    else:
        issues.append('No exact supported coding was recognized; display text is not mapping authority.')
    if any(match['code_status'] == 'discouraged' for match in matches):
        issues.append('A source code is discouraged; it is retained without substituting a different method or code.')
    return {'catalog_version': CATALOG_VERSION, 'status': status, 'metric': metric,
            'concept_ids': ordered, 'matches': matches, 'issues': issues, 'unit': unit}


def resolve_query_constraints(query):
    """Read explicit terminology qualifiers; this does not authorize an intent/tool."""
    text = _normalize(query) if isinstance(query, str) else ''
    codes = list(dict.fromkeys(re.findall(r'(?<!\w)\d{4,5}-\d(?!\w)', text)))
    methods = []
    for pattern, method in (
        (r'\bhplc\b|고성능 액체 크로마토그래피', 'hplc'),
        (r'\bmdrd\b', 'creatinine_mdrd'),
        (r'\bckd[ -]?epi[ -]?2009\b', 'creatinine_ckd_epi_2009'),
        (r'\bckd[ -]?epi[ -]?2021\b', 'creatinine_ckd_epi_2021'),
        (r'\bcalculated\b|계산(?:된|식|값|법)?', 'calculated'),
        (r'\bdirect(?: assay|ly measured)?\b|직접(?:법|측정| 측정)?', 'direct_assay'),
    ):
        if re.search(pattern, text):
            methods.append(method)
    standards = [key for pattern, key in ((r'\bifcc\b', 'ifcc'), (r'\b(?:ngsp|dcct)\b', 'ngsp_dcct')) if re.search(pattern, text)]
    units = []
    original = query if isinstance(query, str) else ''
    for spelling, identity in _UNIT_IDENTITIES.items():
        if re.search(r'(?<!\w)' + re.escape(spelling) + r'(?!\w)', original) and identity not in units:
            units.append(identity)
    ambiguous_formula = bool(re.search(r'\bckd[ -]?epi\b', text)) and not any('ckd_epi' in method for method in methods)
    return {'concept_ids': resolve_concepts(query), 'loinc_codes': [code for code in codes if code in _LOINC],
            'methods': methods, 'standardizations': standards, 'units': units,
            'ambiguous': ambiguous_formula or len(methods) > 1 or len(standards) > 1 or len(units) > 1,
            'unsupported': any(code not in _LOINC for code in codes) or bool(re.search(r'\bcystatin\b|시스타틴', text))}


def qualify_source_metadata(resolution, method=None, specimen=None):
    """Detect explicit contradictions without inferring equivalence from free text.

    Unrecognized source method/specimen strings remain documentary data. Exact
    recognized contradiction terms only invalidate, never create a positive match.
    """
    result = deepcopy(resolution)
    method_names = {'direct': 'direct_assay', 'direct assay': 'direct_assay', '직접법': 'direct_assay',
        'calculated': 'calculated', 'calculation': 'calculated', '계산법': 'calculated',
        'hplc': 'hplc', 'mdrd': 'creatinine_mdrd', 'ckd-epi 2009': 'creatinine_ckd_epi_2009',
        'ckd-epi 2021': 'creatinine_ckd_epi_2021'}
    source_methods = set()
    if isinstance(method, dict):
        if isinstance(method.get('text'), str):
            value = method_names.get(_normalize(method['text']))
            if value:
                source_methods.add(value)
        for coding in method.get('coding', []) if isinstance(method.get('coding', []), list) else []:
            if isinstance(coding, dict) and coding.get('system') == LOINC_SYSTEM:
                term = _LOINC.get(coding.get('code')) if isinstance(coding.get('code'), str) else None
                if term and term['method'] != 'unspecified':
                    source_methods.add(term['method'])
    code_methods = {match['method'] for match in result['matches'] if match['method'] != 'unspecified'}
    if len(source_methods) > 1 or source_methods and code_methods and source_methods != code_methods:
        result['status'] = 'conflicting'
        result['issues'].append('Source method and recognized code method disagree; both source assertions remain retained.')
    specimen_names = {'blood': 'blood', 'whole blood': 'blood', '혈액': 'blood', '전혈': 'blood',
        'serum': 'serum', '혈청': 'serum', 'plasma': 'plasma', '혈장': 'plasma', 'urine': 'urine', '소변': 'urine'}
    display = specimen.get('display') if isinstance(specimen, dict) else None
    recorded = specimen_names.get(_normalize(display)) if isinstance(display, str) else None
    allowed = {'blood': {'blood'}, 'serum_or_plasma': {'serum', 'plasma'},
               'serum_plasma_or_blood': {'serum', 'plasma', 'blood'}}
    if recorded and any(recorded not in allowed[match['specimen']] for match in result['matches']):
        result['status'] = 'conflicting'
        result['issues'].append('Explicit source specimen and recognized code specimen disagree; no specimen equivalence was inferred.')
    return result


def qualified_observation_semantics(observation):
    """Return verified source mapping only while the normalized basis is unchanged."""
    from .record_models import FHIRProvenance
    raw = observation.get('fhir_provenance')
    if not raw or observation.get('reviewed_fields') or observation.get('source_span_withheld'):
        return None
    try:
        provenance = FHIRProvenance.model_validate(raw)
        if provenance.original_quantity.comparator is not None:
            return None
        basis = provenance.basis.model_dump(mode='json')
        if any(observation.get(field) != basis[field] for field in ('metric', 'value', 'unit', 'date', 'reported_at')):
            return None
        resolution = resolve_codings([c.model_dump(exclude_none=True) for c in provenance.original_code.coding],
                                      provenance.original_quantity.model_dump(exclude_none=True))
        resolution = qualify_source_metadata(resolution,
            provenance.original_method.model_dump(exclude_none=True) if provenance.original_method else None,
            provenance.original_specimen.model_dump(exclude_none=True) if provenance.original_specimen else None)
        if resolution['status'] != 'resolved' or resolution['metric'] != observation['metric']:
            return None
        if provenance.original_quantity.value != observation['value']:
            return None
        if provenance.original_effective_date_time[:10] != observation['date']:
            return None
        if provenance.original_issued and observation.get('reported_at'):
            from .temporal import instant
            if instant(provenance.original_issued) != instant(observation['reported_at']):
                return None
        if provenance.resolution.catalog_version != CATALOG_VERSION:
            return None
        return deepcopy(resolution)
    except (ValueError, TypeError, KeyError, AttributeError):
        return None


def fhir_semantic_export(observation):
    """Allowlisted source fields for a compatible unchanged row; otherwise local facts."""
    from .record_models import FHIRProvenance
    metric = observation['metric']
    fallback = {'code': {'coding': [{'system': MODUS_METRIC_CODE_SYSTEM, 'code': metric,
                                     'display': _CONCEPTS[metric][0]}], 'text': _CONCEPTS[metric][0]},
                'status': 'unknown', 'valueQuantity': {'value': observation['value'], 'unit': observation['unit']},
                'effectiveDateTime': observation['date']}
    # Keep existing human-readable local labels stable.
    if metric == 'ldl':
        fallback['code']['text'] = fallback['code']['coding'][0]['display'] = 'LDL cholesterol'
    if observation.get('reported_at'):
        fallback['issued'] = observation['reported_at']
    if qualified_observation_semantics(observation) is None:
        return fallback
    provenance = FHIRProvenance.model_validate(observation['fhir_provenance'])
    result = {'code': provenance.original_code.model_dump(exclude_none=True),
              'status': provenance.original_status if provenance.original_status in
                  ('registered', 'preliminary', 'final', 'amended', 'corrected', 'cancelled', 'entered-in-error', 'unknown') else 'unknown',
              'valueQuantity': provenance.original_quantity.model_dump(exclude_none=True),
              'effectiveDateTime': provenance.original_effective_date_time}
    if provenance.original_method is not None:
        result['method'] = provenance.original_method.model_dump(exclude_none=True)
    if provenance.original_specimen is not None:
        result['specimen'] = provenance.original_specimen.model_dump(exclude_none=True)
    if observation.get('reported_at'):
        result['issued'] = provenance.original_issued or observation['reported_at']
    return result

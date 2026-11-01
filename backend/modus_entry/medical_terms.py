"""Versioned retrieval vocabulary, not clinical inference or standardized coding.

English terminology checked against the linked primary references. Korean and
everyday search aliases are authored mappings, not clinician-reviewed translations.
No thresholds, diagnoses, treatment relations, units or source values are inferred.
"""
from functools import lru_cache
import re
import unicodedata

VERSION = 'record-terms-2026-10-30.1'
REFERENCES = {
    'a1c': ('NIDDK', 'The A1C Test', 'https://www.niddk.nih.gov/health-information/diagnostic-tests/a1c-test'),
    'glucose': ('MedlinePlus', 'Blood Glucose Test', 'https://medlineplus.gov/lab-tests/blood-glucose-test/'),
    'lipids': ('MedlinePlus', 'Cholesterol Levels', 'https://medlineplus.gov/lab-tests/cholesterol-levels/'),
    'egfr': ('MedlinePlus', 'eGFR and GFR Tests', 'https://medlineplus.gov/lab-tests/estimated-glomerular-filtration-rate-egfr-and-gfr-tests/'),
    'ferritin': ('MedlinePlus', 'Ferritin Blood Test', 'https://medlineplus.gov/lab-tests/ferritin-blood-test/'),
    'cbc': ('MedlinePlus', 'Complete Blood Count', 'https://medlineplus.gov/lab-tests/complete-blood-count-cbc/'),
    'cmp': ('MedlinePlus', 'Comprehensive Metabolic Panel', 'https://medlineplus.gov/lab-tests/comprehensive-metabolic-panel-cmp/'),
    'alt': ('MedlinePlus', 'ALT Blood Test', 'https://medlineplus.gov/lab-tests/alt-blood-test/'),
    'ast': ('MedlinePlus', 'AST Test', 'https://medlineplus.gov/lab-tests/ast-test/'),
    'bmp': ('MedlinePlus', 'Basic Metabolic Panel', 'https://medlineplus.gov/lab-tests/basic-metabolic-panel-bmp/'),
    'tsh': ('MedlinePlus', 'TSH Test', 'https://medlineplus.gov/lab-tests/tsh-thyroid-stimulating-hormone-test/'),
    'pulse': ('MedlinePlus', 'Pulse', 'https://medlineplus.gov/ency/article/003399.htm'),
    'vitamin_d': ('MedlinePlus', 'Vitamin D Test', 'https://medlineplus.gov/lab-tests/vitamin-d-test/'),
}

# IDs are local retrieval concepts, never assigned LOINC/SNOMED codes.
# Matching a name does not establish method, specimen or unit equivalence.
def term(key, name, plain, aliases, reference):
    return {'id': key, 'medical_name': name, 'display_name': plain,
            'aliases': tuple(dict.fromkeys((name, *aliases))), 'reference': reference}

TERMS = (
    term('hba1c', 'HbA1c', 'Average blood sugar (HbA1c)', ('A1c','hemoglobin A1c','haemoglobin A1c','glycated hemoglobin','glycated haemoglobin','average blood sugar','long term blood sugar','당화혈색소'), 'a1c'),
    term('glucose', 'Glucose', 'Blood glucose (Glucose)', ('blood glucose','serum glucose','포도당'), 'glucose'),
    term('fasting_glucose', 'Fasting glucose', 'Fasting blood sugar (FPG)', ('FPG','fasting plasma glucose','fasting blood glucose','fasting blood sugar','공복혈당','공복 혈당'), 'glucose'),
    term('ldl', 'LDL', 'LDL cholesterol', ('LDL cholesterol','LDL C','low density lipoprotein','low density lipoprotein cholesterol','bad cholesterol','저밀도 콜레스테롤'), 'lipids'),
    term('hdl', 'HDL', 'HDL cholesterol', ('HDL cholesterol','HDL C','high density lipoprotein','high density lipoprotein cholesterol','good cholesterol','고밀도 콜레스테롤'), 'lipids'),
    term('total_cholesterol', 'Total cholesterol', 'Total cholesterol', ('total cholesterol level','총콜레스테롤','총 콜레스테롤'), 'lipids'),
    term('triglycerides', 'Triglycerides', 'Triglycerides', ('triglyceride','TG','중성지방'), 'lipids'),
    term('egfr', 'eGFR', 'Kidney filtering estimate (eGFR)', ('estimated GFR','estimated glomerular filtration rate','kidney filtering','kidney filtering estimate','추정사구체여과율','추정 사구체 여과율'), 'egfr'),
    term('ferritin', 'Ferritin', 'Stored iron marker (Ferritin)', ('serum ferritin','iron stores','stored iron','페리틴'), 'ferritin'),
    term('hemoglobin', 'Hemoglobin', 'Hemoglobin (Hb)', ('haemoglobin','Hb','Hgb','혈색소','헤모글로빈'), 'cbc'),
    term('wbc', 'WBC', 'White blood cell count (WBC)', ('white blood cells','white blood cell count','leukocyte count','백혈구','백혈구 수'), 'cbc'),
    term('rbc', 'RBC', 'Red blood cell count (RBC)', ('red blood cells','red blood cell count','erythrocyte count','적혈구','적혈구 수'), 'cbc'),
    term('platelets', 'Platelets', 'Platelet count (PLT)', ('platelet count','PLT','혈소판','혈소판 수'), 'cbc'),
    term('hematocrit', 'Hematocrit', 'Hematocrit (Hct)', ('haematocrit','Hct','헤마토크릿'), 'cbc'),
    term('tsh', 'TSH', 'Thyroid-stimulating hormone (TSH)', ('thyroid stimulating hormone','thyrotropin','갑상선자극호르몬','갑상선 자극 호르몬'), 'tsh'),
    term('alt', 'ALT', 'Alanine aminotransferase (ALT)', ('alanine aminotransferase','alanine transaminase','SGPT'), 'alt'),
    term('ast', 'AST', 'Aspartate aminotransferase (AST)', ('aspartate aminotransferase','aspartate transaminase','SGOT'), 'ast'),
    term('creatinine', 'Creatinine', 'Creatinine', ('serum creatinine','크레아티닌'), 'bmp'),
    term('bun', 'BUN', 'Blood urea nitrogen (BUN)', ('blood urea nitrogen','혈중요소질소','혈중 요소 질소'), 'bmp'),
    term('sodium', 'Sodium', 'Sodium', ('serum sodium','나트륨'), 'bmp'),
    term('potassium', 'Potassium', 'Potassium', ('serum potassium','칼륨'), 'bmp'),
    term('calcium', 'Calcium', 'Calcium', ('serum calcium','칼슘'), 'bmp'),
    term('pulse', 'Pulse', 'Heart rate (Pulse)', ('heart rate','pulse rate','심박수','맥박','맥박수'), 'pulse'),
    term('vitamin_d', 'Vitamin D', 'Vitamin D', ('비타민 D','비타민D'), 'vitamin_d'),
)
BY_ID = {item['id']: item for item in TERMS}
AMBIGUITIES = (
    ('blood sugar', ('blood sugar','혈당'), ('hba1c','glucose','fasting_glucose')),
    ('cholesterol', ('cholesterol','콜레스테롤'), ('ldl','hdl','total_cholesterol')),
    ('kidney tests', ('kidney tests','kidney test','kidney numbers','kidney function','신장 검사','신장 수치'), ('egfr','creatinine','bun')),
    ('liver tests', ('liver tests','liver test','liver enzymes','간수치','간 수치'), ('alt','ast')),
)


def normalize(text):
    return re.sub(r'[\s\-–]+', ' ', unicodedata.normalize('NFKC', text).casefold()).strip()


@lru_cache(maxsize=512)
def _pattern(alias):
    suffix = r'(?:은|는|을|를|이|가|의)?' if re.search('[가-힣]$', alias) else ''
    return re.compile(r'(?<!\w)' + re.escape(alias) + suffix + r'(?!\w)')


@lru_cache(maxsize=4096)
def label_concept(label):
    normalized = normalize(label)
    return next((t['id'] for t in TERMS if normalized in {normalize(a) for a in t['aliases']}), None)


def mentions(text):
    """Longest non-overlapping aliases; an embedded Hb must not match HbA1c."""
    normalized = normalize(text)
    candidates = [(m.start(), m.end(), t['id'], normalized[m.start():m.end()])
        for t in TERMS for alias in t['aliases'] for m in _pattern(normalize(alias)).finditer(normalized)]
    chosen = []
    for item in sorted(candidates, key=lambda x: (-(x[1]-x[0]), x[0], x[2])):
        if not any(item[0] < old[1] and old[0] < item[1] for old in chosen):
            chosen.append(item)
    return normalized, sorted(chosen)


def unquoted(text):
    return re.sub(r'''(?:(?:source|title|document|from)\s*:?\s*)?(?:"[^"\n]*"|“[^”\n]*”|(?<!\w)'[^'\n]*'(?!\w))''', lambda m:' '*len(m[0]), text, flags=re.I)


def ambiguous_request(message):
    text, resolved = mentions(unquoted(message))
    for name, aliases, choices in AMBIGUITIES:
        for alias in aliases:
            for match in _pattern(normalize(alias)).finditer(text):
                if any(match.start() < end and start < match.end() for start,end,_,_ in resolved):
                    continue
                # Preserve the entire original request, including quotes/dates,
                # in each clarification. Do not replace just the search subject.
                original_pattern = re.compile(_pattern(normalize(alias)).pattern, re.I)
                original_match = original_pattern.search(unquoted(message))
                if not original_match:
                    return {'kind':'medical_term','question':f'Which recorded test do you mean by “{name}”? Please include its name with your original filters.', 'choices':[]}
                return {'kind':'medical_term','question':f'Which recorded test do you mean by “{name}”?',
                    'choices':[{'label':BY_ID[key]['display_name'], 'message':message[:original_match.start()]+BY_ID[key]['medical_name']+message[original_match.end():]} for key in choices]}
    return None


def public_concept(key):
    item = BY_ID[key]
    publisher, title, url = REFERENCES[item['reference']]
    return {'concept_id':key,'medical_name':item['medical_name'],'display_name':item['display_name'],
        'reference':{'publisher':publisher,'title':title,'url':url,'checked_on':'2026-10-30'},
        'catalog_version':VERSION,'mapping_review':'authored_reference_checked_not_clinician_validated'}

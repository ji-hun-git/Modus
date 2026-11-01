"""Small, reviewed-reference naming vocabulary for non-laboratory records.

These are retrieval topics, not assertions that a procedure was performed or a
vaccine administered. Match the saved label and kind, never a narrative mention.
"""
from functools import lru_cache
from .medical_terms import normalize, _pattern

VERSION = 'record-topics-2026-10-30.1'
TOPICS = (
    ('influenza_vaccine', 'Influenza vaccine', ('flu shot', 'flu shots', 'flu vaccine', 'influenza vaccine', 'influenza vaccination', '독감 예방접종'),
     ('vaccination',), 'Flu', 'https://medlineplus.gov/flu.html'),
    ('mri', 'MRI', ('MRI', 'MRI scan', 'magnetic resonance imaging', '자기공명영상'),
     ('imaging_text', 'procedure'), 'MRI Scans', 'https://medlineplus.gov/mriscans.html'),
    ('ct', 'CT', ('CT', 'CT scan', 'CAT scan', 'computed tomography', '컴퓨터단층촬영'),
     ('imaging_text', 'procedure'), 'CT Scans', 'https://medlineplus.gov/ctscans.html'),
    ('xray', 'X-ray', ('x ray', 'x rays', 'xray', 'radiograph', 'radiography', '엑스레이'),
     ('imaging_text', 'procedure'), 'X-Rays', 'https://medlineplus.gov/xrays.html'),
    ('ecg', 'Electrocardiogram', ('ECG', 'EKG', 'electrocardiogram', '심전도'),
     ('procedure', 'imaging_text'), 'Electrocardiogram', 'https://medlineplus.gov/lab-tests/electrocardiogram/'),
)
BY_ID = {t[0]: t for t in TOPICS}


def mentions(text):
    normalized = normalize(text)
    candidates = [(m.start(), m.end(), key, normalized[m.start():m.end()])
        for key, _, aliases, *_ in TOPICS for alias in aliases
        for m in _pattern(normalize(alias)).finditer(normalized)]
    chosen = []
    for item in sorted(candidates, key=lambda x: (-(x[1]-x[0]), x[0], x[2])):
        if not any(item[0] < old[1] and old[0] < item[1] for old in chosen):
            chosen.append(item)
    return normalized, sorted(chosen)


@lru_cache(maxsize=4096)
def label_topics(kind, label):
    return frozenset(key for _, _, key, _ in mentions(label)[1] if kind in BY_ID[key][3])


def public_topic(key):
    _, name, _, kinds, title, url = BY_ID[key]
    return {'concept_id': 'topic:' + key, 'medical_name': name, 'display_name': name,
        'catalog_version': VERSION, 'match_scope': 'saved_label_and_kind',
        'record_kinds': list(kinds), 'mapping_review': 'authored_reference_checked_not_clinician_validated',
        'reference': {'publisher': 'MedlinePlus', 'title': title, 'url': url, 'checked_on': '2026-10-30'}}

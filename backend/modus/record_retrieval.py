"""Bounded lexical retrieval over an already captured record view.

This module has no store, filesystem, network, provider, or mutation capability.
Ontology terms improve lookup; they do not assign a method/code to a record.
"""
from collections import Counter
from copy import deepcopy
from datetime import date, datetime, timezone
import math
import re
import unicodedata

from .ontology import (CATALOG_VERSION, concept_terms, resolve_concepts,
                       resolve_query_constraints, qualified_observation_semantics, recorded_unit)

RETRIEVAL_VERSION = 'scoped-record-bm25-v2'
MAX_LIMIT = 8
MAX_CONTEXT_FACTS = 8
MAX_WARNING_IDS = 32
MAX_QUERY_LENGTH = 2000
STOP_WORDS = set('a an the my me i please what which where is are was were be been of for on in at to from with and or about show find search retrieve look up tell give read recorded records record measurements measurement values value results result sources source documents document evidence containing contains mention mentions'.split())
UNSAFE_QUERY = re.compile(
    r'\b(?:diagnos\w*|treat\w*|normal\w*|abnormal\w*|healthy|disease\w*|dose\w*|'
    r'prescri\w*|genetic\w*|cancer\w*|medicin\w*|medication\w*|recommend\w*|symptom\w*|'
    r'therap\w*|caus\w*|risk\w*|improv\w*|worsen\w*|trend\w*|average\w*|mean\w*|interpret\w*|'
    r'concern\w*|forecast\w*|predict\w*|delete|erase|overwrite|edit|replace|merge|insert|commit|'
    r'send|upload|download|export|execute|shell|sql|permissions?)\b|'
    r'\bshould i\b|https?://|'
    r'\b(?:ignore|bypass|override|widen|change)\b.{0,50}\b(?:scope|cutoff|bounds?|dates?|rules?)\b|'
    r'\b(?:another|other|different) (?:person|profile|user)\b|'
    r'진단|치료|처방|복용|약물|위험|비?정상|질병|증상|추천|개선|악화|추세|평균|해석|원인|예측|'
    r'삭제|수정|덮어|병합|저장|추가해|업로드|다운로드|내보내|전송|권한|실행|명령|'
    r'(?:범위|날짜|기준|제한).{0,15}(?:무시|변경|확장)|다른\s*(?:사람|사용자|프로필)', re.I)
UNSUPPORTED_METRIC = re.compile(
    r'\b(?:glucose|creatinine|hdl|triglycerides?|troponin|ferritin|sodium|potassium|'
    r'blood pressure|heart rate|weight|bmi|total cholesterol)\b|'
    r'트로포닌|페리틴|크레아티닌|혈압|심박|혈당|포도당|체중|중성지방|총\s*콜레스테롤', re.I)
CONFLICT_QUERY = re.compile(r'\b(?:disagree\w*|conflict\w*|contradict\w*|mismatch\w*|inconsisten\w*)\b|불일치|상충|충돌', re.I)
QUERY_FILLER = set('can could would you please get locate return list display inspect check all any only every that whose this these those selected scoped recorded record readings reading measured measurement date dated title titled quote quoted phrase passage excerpt named called containing find findme search looking need want have has had do does did is are was were been show give tell read from for in on at to and with by using as per of my me i us our the a an same day at between available through within view views window period interval how many number total overall inventory count support supporting examined checked considered affected evidence entries units distinct not match different differences newly new original first became become arrived arrive arrival arrivals added availability compare comparison snapshot snapshots year years there among here exist exists present stored documented existing history known then now already earlier later other file files 년 월 일'.split())


def _normalize(text):
    return unicodedata.normalize('NFKC', str(text)).casefold()


def _tokens(text):
    return [token for token in re.findall(r'\d{4,5}-\d\b|[a-z]+[a-z0-9]*|\d+(?:\.\d+)?|[가-힣]+', _normalize(text))
            if token not in STOP_WORDS]


def has_negated_record_filter(query):
    """Negation is not implemented as a filter; never invert it to a match."""
    text = _normalize(query)
    # The existing same-day disagreement phrase is not a source exclusion.
    if re.search(r'\b(?:same day|same date)\b', text) and re.search(r'\b(?:values?|units?|measurements?|readings?)\b', text):
        text = re.sub(r'\b(?:do|does) not match\b', '', text)
    return bool(re.search(r'\b(?:not|never|without|except|exclude\w*|excluding)\b|'
                          r'\b(?:other than|rather than)\b|제외|빼고|빼줘|말고|아닌|아니고|포함하지|없이|이외|외의', text))


def _instant(value):
    parsed = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('Availability requires an explicit timezone')
    return parsed.astimezone(timezone.utc)


def _visible_rows(view):
    """Defense in depth: only rows AND sources within the supplied scope."""
    through = date.fromisoformat(view['scope']['as_of'])
    known = _instant(view['scope']['known_at'])
    sources = {source['id']: source for source in view['sources']}
    visible = []
    for row in view['observations']:
        source = sources.get(row['source_id'])
        if source is None:
            continue
        available = row.get('available_at') or source.get('available_at')
        if available is None:
            continue
        if date.fromisoformat(row['date']) > through or _instant(available) > known:
            continue
        if source.get('available_at') and _instant(source['available_at']) > known:
            continue
        visible.append((row, source))
    return visible


def _constraints_match(row, constraints):
    concepts = constraints.get('concept_ids', [])
    if concepts and row['metric'] not in concepts:
        return False
    # A printed/reviewed unit can be matched exactly without claiming a code,
    # method, unit conversion, or reference-range interpretation.
    units = constraints.get('units', [])
    if units and recorded_unit({'unit': row['unit']})['identity'] not in units:
        return False
    codes = constraints.get('loinc_codes', [])
    methods = constraints.get('methods', [])
    standards = constraints.get('standardizations', [])
    if not (codes or methods or standards):
        return True
    semantics = qualified_observation_semantics(row)
    if semantics is None:
        return False
    matches = semantics.get('matches', [])
    # All precise constraints must be supported by the same source coding.
    return any((not codes or match.get('code') in codes)
               and (not methods or match.get('method') in methods)
               and (not standards or match.get('standardization') in standards)
               for match in matches)


def _query_dates(query):
    query = re.sub(r'\bckd[ -]?epi[ -]?(?:2009|2021)\b', '', query, flags=re.I)
    exact_dates = re.findall(r'(?<!\d)\d{4}-\d{2}-\d{2}(?!\d)', query)
    years = re.findall(r'(?<![\d-])(?:19|20)\d{2}(?![\d-])', query)
    return exact_dates, years


def _date_match(row, source, query):
    exact_dates, years = _query_dates(query)
    if not exact_dates and not years:
        return True
    measured_only = bool(re.search(r'\bmeasured\b|measurement date|측정일|측정된|검사일', query, re.I))
    dates = [row['date']] if measured_only else [row['date'], source.get('date', '')]
    return (not exact_dates or any(day in exact_dates for day in dates)) and (
        not years or any(day[:4] in years for day in dates))


def _passage_constraints(query, concepts, semantic):
    phrases = [first or second for first, second in re.findall(r'["“]([^"”]+)["”]|(?<!\w)\x27([^\x27]+)\x27(?!\w)', query)]
    title_only = bool(re.search(r'\b(?:title|titled)\b|제목', query, re.I))
    if title_only and not phrases:
        match = re.search(r'\b(?:titled\s+|title\s*[:=]\s*)(.+?)[?.!]?$', query, re.I)
        if match:
            phrases = [match[1].rstrip('?.!')]
    omitted = set(QUERY_FILLER)
    for metric in concepts:
        omitted.update(_tokens(' '.join(concept_terms(metric))))
    for phrase in phrases:
        omitted.update(_tokens(phrase))
    for unit in semantic.get('units', []):
        omitted.update(_tokens(unit))
    omitted.update(semantic.get('loinc_codes', []))
    if semantic.get('methods') or semantic.get('standardizations'):
        omitted.update('direct directly calculated assay hplc mdrd ckd epi creatinine ngsp dcct ifcc formula method 2009 2021 직접 직접법 직접측정 계산 계산된 계산식 크레아티닌'.split())
    for day in re.findall(r'(?<!\d)\d{4}-\d{2}-\d{2}(?!\d)|(?<![\d-])(?:19|20)\d{2}(?![\d-])', query):
        omitted.update(_tokens(day))
    required = []
    for term in _tokens(query):
        if term in omitted or CONFLICT_QUERY.fullmatch(term):
            continue
        if re.fullmatch(r'(?:기록|문서|보고서|자료|출처|측정|검사|수치|값|결과|제목)(?:이|가|은|는|을|를|의|에서|에|만|도|와|과|좀)*', term):
            continue
        if re.match(r'^(?:찾|검색|조회|알려|보여|확인|부탁|주세요|해줘|해주)', term):
            continue
        required.append(term)
    return {'phrases': phrases, 'title_only': title_only,
            'required_terms': list(dict.fromkeys(required))}


def query_requires_record_filter(query):
    """Routing guard: coarse inventory/conflict/arrival tools cannot apply these."""
    semantic = resolve_query_constraints(query)
    passages = _passage_constraints(query, resolve_concepts(query), semantic)
    dates, years = _query_dates(query)
    return bool(passages['phrases'] or passages['required_terms'] or dates or years)


def _passage_match(row, source, constraints):
    texts = [source.get('title', '')]
    if not constraints['title_only']:
        texts += [source.get('provider', ''), '' if row.get('source_span_withheld') else row.get('source_span', '')]
    normalized = [_normalize(text) for text in texts]
    if not all(any(_normalize(phrase) in text for text in normalized) for phrase in constraints['phrases']):
        return False
    if not constraints['title_only']:
        texts += [row['metric'], str(row['value']), row['unit'], row['date'], source.get('date', '')]
    raw_terms = set(_tokens(' '.join(texts)))
    return all(term in raw_terms for term in constraints['required_terms'])


def _document(row, source):
    span = '' if row.get('source_span_withheld') else row.get('source_span', '')
    # Full source.content is intentionally never indexed: a partially visible
    # document may also contain later measurements or withheld passages.
    return Counter(_tokens(' '.join(str(value) for value in [
        row['id'], source['id'], source.get('title', ''), source.get('provider', ''),
        row['metric'], row['value'], row['unit'], row['date'], source.get('date', ''),
        span, *concept_terms(row['metric'])])))


def _hit(row, source, score, companion=False):
    fields = ('id', 'metric', 'value', 'unit', 'date', 'source_id', 'page',
              'reported_at', 'reported_at_raw', 'available_at', 'availability_basis', 'reviewed_fields')
    hit = {key: deepcopy(row.get(key)) for key in fields}
    hit.update({'observation_id': row['id'], 'source_title': source.get('title', ''),
                'source_span': '' if row.get('source_span_withheld') else row.get('source_span', ''),
                'source_span_withheld': bool(row.get('source_span_withheld')),
                'score': round(score, 8),
                'retrieved_because': 'conflict_companion' if companion else 'query_match'})
    return hit


def retrieve_record_evidence(view, query, limit=5):
    """Return at most ``limit`` raw fact hits from this exact frozen View.

    Ranking is BM25 over scoped facts plus ontology lookup terms. Scores are
    retrieval ordering values, not confidence, probability, or clinical merit.
    Empty results never claim that no measurement/care occurred.
    """
    if not isinstance(query, str) or not query.strip() or len(query) > MAX_QUERY_LENGTH:
        raise ValueError('Query must contain 1 to 2000 characters')
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= MAX_LIMIT:
        raise ValueError('Limit must be an integer from 1 to 8')
    constraints = resolve_query_constraints(query)
    concepts = resolve_concepts(query)
    passages = _passage_constraints(query, concepts, constraints)
    conflict_only = bool(CONFLICT_QUERY.search(query))
    result = {'scope': deepcopy(view['scope']), 'query': query, 'limit': limit,
              'method': RETRIEVAL_VERSION, 'ontology_version': CATALOG_VERSION,
              'constraints': deepcopy(constraints), 'hits': [], 'warnings': [],
              'conflict_context': [], 'context_limit': MAX_CONTEXT_FACTS, 'conflict_only': conflict_only,
              'passage_constraints': passages, 'match_mode': 'exact_phrase_and_lexical' if passages['phrases'] else 'lexical_ranked',
              'empty_reason': None, 'truncated': False}
    def empty(reason):
        result['empty_reason'] = reason
        return result
    if UNSAFE_QUERY.search(query):
        return empty('unsupported_request')
    if has_negated_record_filter(query):
        return empty('unsupported_negated_filter')
    # Creatinine may be an explicit supported eGFR-method term, not a request
    # for a separate creatinine measurement. Only ontology evidence allows it.
    unsupported_text = query
    if concepts == ['egfr'] and constraints.get('methods'):
        unsupported_text = re.sub(r'creatinine|크레아티닌', '', query, flags=re.I)
    if UNSUPPORTED_METRIC.search(unsupported_text):
        return empty('unsupported_metric')
    if constraints.get('unsupported') or constraints.get('ambiguous') or len(concepts) > 1:
        return empty('unsupported_or_ambiguous_constraint')
    if len(constraints.get('loinc_codes', [])) > 1:
        return empty('ambiguous_code_constraint')
    query_dates, query_years = _query_dates(query)
    if (query_dates or query_years) and re.search(
            r'\b(?:before|after|since|between|until|through)\b|\bup to\b|\bearlier than\b|\blater than\b|이전|이후|사이|부터|까지', query, re.I):
        return empty('unsupported_date_constraint')
    if concepts and not (constraints.get('methods') or constraints.get('loinc_codes')) and re.search(
            r'\b(?:formula|method|assay|cockcroft|schwartz|ekfc)\b|측정법|공식|분석법', query, re.I):
        return empty('unsupported_method_constraint')
    fraction_units = re.findall(r'(?<!\w)(?:[pnumkµμ]?g|[pnum]?mol|[pnumµμ]?l|iu|u)/(?:[dmunpµμ]?l|mol|min)(?:/(?:1\.73\s*m[2²]|\{1\.73_m2\}))?(?!\w)', query, re.I)
    if any(recorded_unit({'unit': unit})['identity'] is None for unit in fraction_units):
        return empty('unsupported_unit_constraint')
    if re.search(r'\bcholesterol\b|콜레스테롤', query, re.I) and concepts != ['ldl']:
        return empty('ambiguous_metric')
    if not concepts and not conflict_only and re.search(r'\b(?:values?|readings?|results?)\b|수치|값', query, re.I):
        return empty('ambiguous_metric')
    pairs = _visible_rows(view)
    conflict_ids = {row['id'] for group in view.get('conflicts', []) for row in group['observations']}
    def matches_query(row, source):
        return (_constraints_match(row, constraints) and _date_match(row, source, query)
                and _passage_match(row, source, passages)
                and (not conflict_only or row['id'] in conflict_ids))
    candidates = [(row, source) for row, source in pairs
                  if matches_query(row, source)]
    if not candidates:
        return empty('no_matching_scoped_facts')
    documents = [_document(row, source) for row, source in candidates]
    query_terms = list(dict.fromkeys(_tokens(query) + concepts))[:128]
    if not query_terms:
        return empty('no_search_terms')
    frequencies = Counter(term for document in documents for term in document)
    average_length = sum(sum(document.values()) for document in documents) / len(documents)
    ranked = []
    for (row, source), document in zip(candidates, documents):
        length = sum(document.values())
        score = 0.0
        for term in query_terms:
            frequency = document.get(term, 0)
            if frequency:
                inverse = math.log(1 + (len(documents) - frequencies[term] + 0.5) / (frequencies[term] + 0.5))
                score += inverse * frequency * 2.2 / (frequency + 1.2 * (0.25 + 0.75 * length / max(average_length, 1)))
        if score > 0:
            ranked.append((score, row, source))
    ranked.sort(key=lambda item: (-item[0], -date.fromisoformat(item[1]['date']).toordinal(), item[1]['id']))
    if not ranked:
        return empty('no_lexical_match')
    visible = {row['id']: (row, source) for row, source in pairs}
    ranks = {row['id']: score for score, row, _ in ranked}
    groups = {}
    for group in view.get('conflicts', []):
        member_ids = [row['id'] for row in group['observations'] if row['id'] in visible]
        for observation_id in member_ids:
            groups[observation_id] = (group['id'], member_ids)
    selected = set()
    for score, row, source in ranked:
        if len(result['hits']) >= limit:
            break
        if row['id'] in selected:
            continue
        additions = [row['id']]
        if row['id'] in groups:
            additions += [key for key in groups[row['id']][1] if key != row['id']]
        for key in additions:
            if key in selected or len(result['hits']) >= limit:
                continue
            candidate, candidate_source = visible[key]
            if not matches_query(candidate, candidate_source):
                continue
            # Answer hits satisfy every query restriction. Nonmatching facts
            # are disclosed separately below, never promoted to answer claims.
            hit = _hit(candidate, candidate_source, ranks.get(key, 0), key != row['id'])
            hit['conflict_ids'] = [groups[key][0]] if key in groups else []
            candidate_terms = _document(candidate, candidate_source)
            hit['matched_terms'] = [term for term in query_terms if term in candidate_terms]
            result['hits'].append(hit)
            selected.add(key)
    reported_groups = set()
    context_count = 0
    for observation_id in sorted(selected):
        if observation_id not in groups:
            continue
        group_id, members = groups[observation_id]
        if group_id in reported_groups:
            continue
        reported_groups.add(group_id)
        omitted = sorted(set(members) - selected)
        if omitted:
            constrained = any(not _constraints_match(visible[key][0], constraints) for key in omitted)
            source_filtered = any(not _passage_match(*visible[key], passages) for key in omitted)
            date_filtered = any(not _date_match(*visible[key], query) for key in omitted)
            kind = ('conflict_constraint' if constrained else 'conflict_source_filter' if source_filtered
                    else 'conflict_date_filter' if date_filtered else 'conflict_limit')
            message = ('Other conflicting values do not satisfy the query restrictions and are not answer hits.'
                       if constrained or source_filtered or date_filtered else 'The answer-hit limit omits other conflicting recorded values.')
            context_rows = []
            for key in omitted:
                if context_count >= MAX_CONTEXT_FACTS:
                    break
                context_row, context_source = visible[key]
                context_hit = _hit(context_row, context_source, ranks.get(key, 0), companion=True)
                context_hit['retrieved_because'] = 'conflict_context_only'
                context_hit['conflict_ids'] = [group_id]
                context_rows.append(context_hit)
                context_count += 1
            context_ids = {row['observation_id'] for row in context_rows}
            result['conflict_context'].append({'conflict_id': group_id,
                'query_hit_observation_ids': sorted(set(members) & selected),
                'observations': context_rows,
                'omitted_context_count': len(omitted) - len(context_rows)})
            result['warnings'].append({'kind': kind, 'conflict_id': group_id,
                'included_observation_ids': sorted(set(members) & selected),
                'omitted_observation_ids': omitted[:MAX_WARNING_IDS], 'omitted_count': len(omitted),
                'context_observation_ids': sorted(context_ids),
                'message': message + ' See separate conflict context or record_conflicts; no value is chosen as correct.'})
    result['warnings'].sort(key=lambda warning: warning['conflict_id'])
    result['truncated'] = (any(row['id'] not in selected for _, row, _ in ranked)
                           or any(group['omitted_context_count'] for group in result['conflict_context']))
    return result

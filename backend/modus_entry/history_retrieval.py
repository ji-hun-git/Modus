"""Conservative terminology-aware retrieval over an already scoped history."""
import re
import unicodedata
from .medical_terms import VERSION, mentions, normalize, label_concept, public_concept, ambiguous_request
from .record_topics import mentions as topic_mentions, label_topics, public_topic

METHOD = 'literal_medical_aliases_and_record_topics_v3'
STOP_WORDS = set(('a an and any are as at available be by can containing contains could did do does entries entry evidence find for from give has have history histories i in is it list look me mentioning mentions mention my of on or please record recorded records report reports result results retrieve search show source sources that the their these this to up value values reading readings test tests was were what which when with would you your '
    '기록 기록을 기록은 내 나의 찾아줘 찾아주세요 보여줘 보여주세요 알려줘 알려주세요 결과 결과를 수치 수치를').split())
KIND_WORDS = {
    'measurement': {'measurement','measurements','측정','측정값'},
    'encounter': {'encounter','encounters','visit','visits','방문','진료'},
    'recorded_diagnosis': {'diagnosis','diagnoses','진단'},
    'procedure': {'procedure','procedures','시술','수술'},
    'prescription': {'prescription','prescriptions','처방'},
    'vaccination': {'vaccination','vaccinations','예방접종','접종'},
    'imaging_text': {'imaging','영상'}, 'recorded_text': {'text','texts','문서'},
}
# Request grammar only; quoted phrases are extracted before this is applied.
STOP_WORDS.update('had ever been got get tell about pull bring latest last most recent whole medical health all'.split())
KIND_WORDS['encounter'].update({'appointment', 'appointments'})
KIND_WORDS['prescription'].update({'medication', 'medications', 'medicine', 'medicines', 'prescribed'})
KIND_WORDS['vaccination'].update({'vaccine', 'vaccines', 'immunization', 'immunizations', 'immunisation', 'immunisations'})
KIND_WORDS['imaging_text'].update({'radiology'})
KIND_WORDS['recorded_text'].update({'note', 'notes', 'other'})
QUOTES = re.compile(r'''(?:(source|title|document|from)\s*:?\s*)?(?:"([^"]+)"|(?<!\w)'([^']+)'(?!\w))''', re.I)


def tokens(text):
    return re.findall(r'\w+', unicodedata.normalize('NFKC',text).casefold())


def plan(query, kind=None):
    query = query.translate(str.maketrans({'“':'"','”':'"','‘':"'",'’':"'"}))
    info = {'method':METHOD,'catalog_version':VERSION,'mappings':[],'status':'ready'}
    if query.count('"') % 2:
        return {'info':{**info,'status':'invalid'},'warnings':['Unclosed quoted phrase; no records were selected.']}
    ambiguity = ambiguous_request(query)
    if ambiguity:
        return {'info':{**info,'status':'clarify','clarification':ambiguity},'warnings':[ambiguity['question']]}
    sources, phrases = [], []
    def remove(match):
        (sources if match[1] else phrases).append((match[2] or match[3]).casefold())
        return ' '
    remaining = QUOTES.sub(remove,query)
    dates = re.findall(r'(?<!\w)(?:19|20)\d{2}(?:-\d{2}(?:-\d{2})?)?(?!\w)',remaining)
    for day in dates: remaining=remaining.replace(day,' ')
    normalized, found = mentions(remaining)
    _, topics_found = topic_mentions(remaining)
    # Alias expansion is only a label match on measurement records. It never
    # expands a narrative mention into a diagnosis, medicine or related test.
    for start,end,key,phrase in sorted(found + topics_found, reverse=True):
        normalized=normalized[:start]+' '*(end-start)+normalized[end:]
    concepts=list(dict.fromkeys(key for _,_,key,_ in found))
    info['mappings']=[{**public_concept(key),'requested_terms':list(dict.fromkeys(phrase for _,_,k,phrase in found if k==key))} for key in concepts]
    topics=list(dict.fromkeys(key for _,_,key,_ in topics_found))
    info['mappings'] += [{**public_topic(key),'requested_terms':list(dict.fromkeys(phrase for _,_,k,phrase in topics_found if k==key))} for key in topics]
    terms=[word for word in tokens(normalized) if word not in STOP_WORDS | KIND_WORDS.get(kind,set())]
    return {'info':info,'concepts':concepts,'topics':topics,'terms':terms,'phrases':phrases,'sources':sources,'dates':dates,'warnings':[]}


def retrieve(view, args):
    parsed=plan(args['query'],args.get('kind'))
    info=parsed['info']; warnings=parsed['warnings']
    if info['status']!='ready': return [],warnings,info
    concepts, terms, phrases, source_phrases, dates = (parsed[k] for k in ('concepts','terms','phrases','sources','dates'))
    topics=parsed['topics']
    if not any((concepts,topics,terms,phrases,source_phrases,dates)):
        return [],['No search terms were supplied; use the inventory tool to list records.'],info
    sources={s['id']:s for s in view['sources']}
    hits=[]
    for row in view['facts']+view['undated_facts']:
        if row.get('value_withheld') or not row.get('within_date_scope',True) or (args.get('kind') and row['kind']!=args['kind']): continue
        if topics and not set(topics) <= label_topics(row['kind'],row['label']): continue
        if concepts and row['kind']=='measurement' and not all(c==label_concept(row['label']) for c in concepts):
            continue
        source=sources[row['source_id']]
        if source_phrases and not all(p in (source.get('title') or '').casefold() for p in source_phrases): continue
        occurred=row.get('occurred_on') or ''
        if dates and (row.get('date_precision') not in {'day','month','year'} or not all(occurred.startswith(d) for d in dates)): continue
        quote='' if row.get('source_quote_withheld') else row.get('source_quote') or ''
        text=' '.join(str(v) for v in (row['label'],row['value'],row.get('unit') or '',row.get('facility') or '',quote,source.get('title') or '',source.get('provider') or '')).casefold()
        if phrases and not all(p in text for p in phrases): continue
        if terms and not set(terms) <= set(tokens(text)): continue
        # AND semantics: two distinct named concepts cannot silently become OR.
        # Literal co-occurrence remains available in quoted narrative searches.
        if concepts and row['kind']!='measurement' and not all(any(normalize(phrase) in normalize(text) for phrase in m['requested_terms']) for m in info['mappings'] if not m['concept_id'].startswith('topic:')):
            # Other record kinds retain literal matching only.
            continue
        label_words=set(tokens(row['label']))
        score=4*len(concepts)+sum(3 if t in label_words else 1 for t in terms)+2*len(phrases)
        hits.append((score,row))
    hits.sort(key=lambda item:(item[0],item[1].get('date') or '',item[1]['id']),reverse=True)
    rows=[row for _,row in hits]
    for mapping in info['mappings']:
        key=mapping['concept_id']
        mapping['matched_labels']=sorted({r['label'] for r in rows if
            (key[6:] in label_topics(r['kind'],r['label']) if key.startswith('topic:') else label_concept(r['label'])==key)})
    return rows,warnings,info

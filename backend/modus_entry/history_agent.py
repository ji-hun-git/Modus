"""Bounded whole-history record requests with source-attributed exact claims."""
from copy import deepcopy
from pathlib import Path
import json
import re

from .agent import execute, live_selection, result, quarantine_request
from .document_guard import QUARANTINED, REQUEST_QUARANTINED
from .runtime import execution_context
from .tools import SelectionArgs
from .history_tools import ARGUMENTS, DESCRIPTIONS, dispatch

PROMPT = (Path(__file__).resolve().parents[2] / 'entry/prompts/history.md').read_text(encoding='utf-8')
UNSUPPORTED = ('I can find recorded measurements, visits, prescriptions, vaccinations, procedures, '
    'diagnoses as recorded and report text, with their dates and sources. '
    'I cannot assess health, infer current medication use or recommend care. '
    'Try a specific record type or an exact name or phrase from a report.')

KIND_PATTERNS = {
    'measurement': r'\b(?:measurements?|lab(?:oratory)? (?:records?|results?|tests?))\b|측정|검사\s*(?:기록|결과)',
    'encounter': r'\b(?:visits?|encounters?|appointments?)\b|방문|내원|진료\s*기록',
    'recorded_diagnosis': r'\b(?:diagnoses|diagnosis)\b|진단\s*기록',
    'procedure': r'\bprocedures?\b|시술|수술',
    'prescription': r'\b(?:prescriptions?|medications?|medicines?|prescribed)\b|처방|약물\s*기록|복약\s*기록',
    'vaccination': r'\b(?:vaccinations?|vaccines?|immunizations?|immunisations?)\b|예방접종|접종',
    'imaging_text': r'\b(?:imaging (?:reports?|records?|text)|radiology (?:reports?|records?))\b|영상\s*(?:검사|판독|기록)|판독문',
    'recorded_text': r'\b(?:other (?:records?|text)|recorded notes?)\b|기타\s*기록',
}
UNSAFE = re.compile(
    r'\b(?:recommend\w*|advice|should|treat(?:ment|ments)?|diagnose|diagnosing|interpret\w*|'
    r'normal|abnormal|healthy|healthier|risk|prognos\w*|predict\w*|caus\w*|improv\w*|worsen\w*|'
    r'prescribe|start|stop|increase|decrease|adjust|safe|dangerous|urgent|triage|'
    r'delete|erase|overwrite|edit|replace|merge|insert|commit|send|upload|download|export|'
    r'execute|shell|sql|permissions?|ignore|bypass|override|widen|backdate)\b|'
    r'\b(?:current(?:ly)?|still|now|today)\b.{0,35}\b(?:tak\w*|us(?:e|ing)|medic\w*|prescri\w*)\b|'
    r'\b(?:taking|take|using|use)\b.{0,30}\b(?:now|today|currently|still)\b|'
    r'\b(?:am i|do i|can i|why|what does .{0,50} mean|how .{0,40}affect)\b|'
    r'\b(?:dose|medicine|medication|vaccine|vaccination)\b.{0,40}\b(?:need|next|best)\b|'
    r'\b(?:another|other|different) (?:person|profile|user)\b|https?://|'
    r'추천|권장|치료(?:법|해|하)|진단해|해석|정상|비정상|위험|원인|효과|예측|삭제|수정|덮어|무시|권한|'
    r'(?:현재|지금|아직).{0,20}(?:복용|먹|약물|약)|복용.{0,15}(?:해야|할까|중)|중단|다른\s*(?:사람|사용자)|'
    r'(?:날짜|범위|시점).{0,15}(?:바꿔|변경|넓혀)', re.I)
COUNT = re.compile(r'\b(?:count|how many|number of|total)\b|몇\s*개|개수',re.I)
ARRIVAL = re.compile(r'\b(?:arrived|added|newly available|became available|what changed|compare .{0,30}(?:views|snapshots))\b|새로\s*추가|추가된|무엇이\s*바뀌|변경된\s*기록',re.I)
CONFLICT = re.compile(r'\b(?:conflict\w*|disagree\w*|mismatch\w*|contradict\w*)\b|불일치|상충|충돌',re.I)
READ = re.compile(r'\b(?:show|list|find|search|retrieve|look up|what|which|count|how many|records?|history|reports?|values?|readings?)\b|보여|찾|검색|기록|내역|보고서|몇\s*개',re.I)


def _outside_quotes(message):
    return re.sub(r'"[^"\n]*"|“[^”\n]*”', ' quoted phrase ', message)


def allowed_request(message):
    text = _outside_quotes(message)
    return bool(READ.search(text)) and not UNSAFE.search(text)


def offline_route(context, message):
    """Conservative intent parsing, without inferring clinical relationships."""
    if not allowed_request(message):
        return None
    text = re.sub(r'\s+', ' ', _outside_quotes(message).lower()).strip()
    if re.search(r'\b(?:not|without|except|excluding)\b|제외|빼고',text):
        return None
    if re.search(r'\b(?:and|then|also)\s+(?:show|list|find|search|count|compare|explain)\b|그리고|또한',text):
        return None
    kinds = [kind for kind, pattern in KIND_PATTERNS.items() if re.search(pattern,text,re.I)]
    if len(kinds)>1:
        return None
    kind = kinds[0] if kinds else None
    arrival, conflict, count = bool(ARRIVAL.search(text)), bool(CONFLICT.search(text)), bool(COUNT.search(text))
    if arrival and conflict:
        return None
    # Remove only recognized syntax. Remaining words are literal source filters,
    # never grounds for silently returning a broader inventory/count.
    remaining = text
    for pattern in KIND_PATTERNS.values():
        remaining = re.sub(pattern,' ',remaining,flags=re.I)
    remaining = ARRIVAL.sub(' ',CONFLICT.sub(' ',COUNT.sub(' ',remaining)))
    remaining = re.sub(r'\b(?:show|list|find|search|retrieve|look|up|what|which|were|was|are|is|has|have|been|'
        r'my|me|the|a|an|all|whole|medical|health|recorded|records?|history|reports?|entries|sources?|'
        r'documents?|available|in|between|these|views?|snapshots?|please|of|for|to)\b', ' ', remaining)
    remaining = re.sub(r'보여\s*줘|보여주세요|찾아\s*줘|찾아주세요|검색해\s*줘|내\s*|나의|모든|전체|기록|내역|보고서|문서|목록|알려\s*줘|있나요|있어', ' ',remaining)
    remaining = re.sub(r'[\s?.!,]+',' ',remaining).strip()
    if arrival or conflict or count:
        if remaining:
            return None
        name = 'compare_history_snapshots' if arrival else 'history_conflicts' if conflict else 'history_inventory'
        if arrival and context.get('comparison') is None:
            return None
        return name, {'kind':kind}
    if remaining:
        return 'search_history_evidence', {'query':message,'kind':kind,'limit':5}
    return 'history_inventory', {'kind':kind,'offset':0,'limit':5}


def evidence_view(context, claims):
    """Inspect only selected scoped evidence, with bounded conflict companions."""
    current=context['view']
    ids={key for item in claims for key in item['evidence_ids']}
    rows=current['facts']+current['undated_facts']
    selected=[row for row in rows if row['id'] in ids]
    selected_ids={row['id'] for row in selected}
    groups=[g for g in current['conflicts'] if selected_ids.intersection(g['fact_ids'])]
    companion_ids={key for g in groups for key in g['fact_ids']}
    expanded=selected+[row for row in rows if row['id'] in companion_ids and row['id'] not in selected_ids]
    limited=expanded[:64]
    source_ids={row['source_id'] for row in limited}
    facts=[deepcopy(row) for row in limited if row.get('date')]
    undated=[deepcopy(row) for row in limited if not row.get('date')]
    return {'scope':deepcopy(current['scope']),'facts':facts,'undated_facts':undated,
        'sources':[deepcopy(s) for s in current['sources'] if s['id'] in source_ids],
        'conflicts':deepcopy(groups),'counts':{'facts':len(limited),'sources':len(source_ids),
            'measurements':sum(r['kind']=='measurement' for r in limited),'undated_facts':len(undated),'conflicts':len(groups)},
        'truncated':len(expanded)>len(limited), 'projection':'selected_answer_evidence'}


def decorate(context, response):
    # Model selection cannot omit material limitations of a selected tool result.
    selected = {claim['id'] for claim in response['claims']}
    for step in response['trace']:
        value = step['result']
        emitted = {claim['id']: claim for claim in value['claims']}
        if selected.intersection(emitted):
            for key in value.get('required_claim_ids', []):
                if key not in emitted:
                    raise ValueError('A required finding was not emitted by the record tool')
                if key not in selected:
                    response['claims'].append(emitted[key])
                    selected.add(key)
    response['answer'] = '\n'.join(claim['text'] for claim in response['claims'])
    response['history_evidence']=evidence_view(context,response['claims'])
    if not response['claims']:
        guard = response.get('document_guard', {})
        response['answer'] = (REQUEST_QUARANTINED if guard.get('boundary') == 'request' else QUARANTINED) if guard.get('status') == 'quarantined' else UNSUPPORTED
    if context.get('comparison'):
        response['history_comparison']={key:context['comparison'][key]['scope'] for key in ('before','after')}
    return response


def offline_chat(context, message):
    guarded = quarantine_request(context, message, {})
    if guarded:
        return decorate(context, guarded)
    execution=execution_context('offline')
    trace=[]
    route=offline_route(context,message)
    claims=[]
    if route:
        name,args=route
        claims=execute(context,name,args,execution,trace,tool_dispatch=dispatch)['claims']
    return decorate(context,result(context,execution,claims,trace))


async def live_chat(context, message, telemetry, *, request=None):
    guarded = quarantine_request(context, message, telemetry)
    if guarded:
        return decorate(context, guarded)
    route=offline_route(context,message)
    if route is None:
        response=decorate(context,result(context,execution_context('request_guard'),[],[]))
        response['provider_requests_made']=0
        return response
    name,raw_args=route
    bound_args=ARGUMENTS[name].model_validate(raw_args).model_dump()

    def bound_dispatch(ctx,tool,args):
        validated=ARGUMENTS[tool].model_validate(args).model_dump()
        if tool!=name or validated!=bound_args:
            raise ValueError('The model changed the bound record request')
        return dispatch(ctx,tool,validated)

    response=await live_selection(context,message,telemetry,
        arguments={name:ARGUMENTS[name],'select_claims':SelectionArgs},
        descriptions={**DESCRIPTIONS,'select_claims':'Finish with exact claim IDs returned by the bound record tool. Empty if unsupported.'},
        tool_dispatch=bound_dispatch,
        prompt=PROMPT+'\nBound record request: '+json.dumps({'tool':name,'arguments':bound_args}),request=request)
    return decorate(context,response)

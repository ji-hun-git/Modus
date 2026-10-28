"""One bounded selection loop; all returned findings originate in typed record tools."""
import json
import re
from pathlib import Path
from time import perf_counter
from modus.policy import POLICY
from modus.ontology import resolve_concepts, resolve_query_constraints, concept_terms
from modus.record_retrieval import UNSAFE_QUERY, query_requires_record_filter, has_negated_record_filter
from modus.provider import provider_status, meta_request, measured_request
from .runtime import execution_context
from .tools import ARGUMENTS, DESCRIPTIONS, dispatch
from .document_guard import screen_untrusted, QUARANTINED, REQUEST_QUARANTINED

PROMPT = (Path(__file__).resolve().parents[2] / 'entry/prompts/records.md').read_text(encoding='utf-8')
UNSUPPORTED = 'This workspace answers questions about recorded facts, sources, disagreements and availability. It does not assess health or recommend care.'

# A deliberately small lexical router, independent of record contents and
# evaluation questions. It only selects a tool/filter; all findings stay typed.
METRIC_PATTERNS = {
    'hba1c': r'\b(?:hba1c|a1c|(?:hemoglobin|haemoglobin) a1c|glycated (?:hemoglobin|haemoglobin))\b',
    'egfr': r'\b(?:egfr|estimated glomerular filtration rate)\b',
    'ldl': r'\b(?:ldl(?: c)?(?: cholesterol)?|low density lipoprotein(?: cholesterol)?)\b',
}
UNSUPPORTED_REQUEST = re.compile(
    r'\b(?:diagnos\w*|treat\w*|normal\w*|abnormal\w*|healthy|disease\w*|dose\w*|'
    r'prescri\w*|genetic\w*|cancer\w*|medicin\w*|medication\w*|recommend\w*|symptom\w*|'
    r'therap\w*|caus\w*|risk\w*|improv\w*|worsen\w*|trend\w*|average\w*|mean\w*|interpret\w*|'
    r'concern\w*|forecast\w*|predict\w*|'
    r'delete|erase|overwrite|edit|replace|merge|insert|commit|send|upload|download|export|'
    r'fetch|execute|shell|sql|permission\w*|glucose|creatinine|hdl|triglycerides?|'
    r'sodium|potassium|blood pressure|heart rate|weight|bmi)\b|'
    r'\bshould i\b|\b(?:ignore|bypass|override|widen|change)\b.{0,50}\b(?:scope|cutoff|bounds?|dates?|rules?)\b|'
    r'\b(?:another|other|different) (?:person|profile|user)\b|https?://'
)
RECORD_WORDS = r'\b(?:records?|documents?|measurements?|sources?|entries|inventory)\b'
ARRIVAL_WORDS = (
    r'\b(?:arriv\w*|added|newly available|became available|become available)\b|'
    r'\bfirst\b.{0,30}\bavailable\b|'
    r'\b(?:changed|compare|comparison)\b.{0,35}\b(?:views?|snapshots?|availability)\b'
)
CONFLICT_WORDS = r'\b(?:disagree\w*|conflict\w*|contradict\w*|mismatch\w*|inconsisten\w*)\b'
DIFFERENCE_WORDS = r'\b(?:differ\w*|distinct|not match|do not match|don\x27t match)\b'


def offline_route(context, message):
    """Return one supported intent and at most one explicit metric, or abstain.

    Record nouns within a conflict/arrival request describe its evidence, not a
    second inventory intent. Explicit combined tasks are not silently reduced
    to whichever keyword happens to appear first.
    """
    text = re.sub(r'\s+', ' ', re.sub(r'[-\u2010-\u2015]', ' ', message.lower())).strip()
    metrics = resolve_concepts(message)
    constraints = resolve_query_constraints(message)
    policy_text = text
    if metrics == ['egfr'] and constraints.get('methods'):
        policy_text = re.sub(r'\bcreatinine\b|크레아티닌', '', policy_text)
    if UNSUPPORTED_REQUEST.search(policy_text) or UNSAFE_QUERY.search(message) or has_negated_record_filter(message):
        return None
    if constraints.get('unsupported') or constraints.get('ambiguous'):
        return None
    if len(metrics) > 1:
        return None
    if re.search(r'\bcholesterol\b|콜레스테롤', text) and metrics != ['ldl']:
        return None
    if re.search(r'혈당|포도당|크레아티닌|트로포닌|페리틴|혈압|심박|체중|중성지방|총\s*콜레스테롤', policy_text):
        return None
    # Do not turn an unknown named filter ("show troponin records") into an
    # all-metric inventory. A closed set of ordinary record qualifiers keeps
    # this check conservative without guessing another metric's identity.
    targets = text
    for metric in metrics:
        for alias in sorted(concept_terms(metric), key=len, reverse=True):
            normalized = re.sub(r'\s+', ' ', re.sub(r'[-\u2010-\u2015]', ' ', alias.lower())).strip()
            targets = re.sub(r'(?<!\w)' + re.escape(normalized) + r'(?!\w)', 'metric', targets)
    qualifiers = {'my', 'the', 'all', 'every', 'any', 'only', 'recorded', 'available',
                  'newly', 'new', 'original', 'supporting', 'conflicting', 'inconsistent',
                  'same', 'day', 'date', 'late', 'metric', 'for', 'in', 'among', 'with',
                  'direct', 'calculated', 'assay', 'hplc', 'mdrd', 'ngsp', 'dcct', 'ifcc',
                  'disagreements', 'conflicts', 'mismatches', 'contradictions'}
    for target in re.finditer(r'\b(?:list|show|display|count|check|inspect)\s+'
                             r'((?:[a-z][a-z0-9]*\s+){0,8})(?:records?|measurements?|documents?|entries)\b', targets):
        if set(target[1].split()) - qualifiers:
            return None
    arrival = bool(re.search(ARRIVAL_WORDS, text) or re.search(r'나중에\s*(?:도착|추가)|늦게\s*(?:도착|추가)|새로\s*추가|추가된\s*(?:기록|문서)|이후.{0,20}(?:도착|추가)', text))
    conflict = bool(re.search(CONFLICT_WORDS, text) or (
        re.search(r'\b(?:same day|same date)\b', text) and re.search(DIFFERENCE_WORDS, text)
        and re.search(r'\b(?:values?|units?|records?|entries|measurements?)\b', text))
        or re.search(r'불일치|상충|충돌|(?:같은\s*날|동일\s*날짜).{0,30}(?:다른|차이)', text))
    # Count requests qualified by "arrived" belong to the arrival tool. A
    # separate inventory/count clause cannot be silently dropped, however.
    clauses = re.split(r'[.;?]|\band\s+(?:also\s+)?(?=(?:list|show|display|count|check|identify|find|compare|give|how|which|what)\b)', text)
    inventory = any(
        re.search(RECORD_WORDS, clause)
        and re.search(r'\b(?:list|show|display|count\w*|inventory|how many|number of|total|overall)\b', clause)
        and not re.search(ARRIVAL_WORDS + '|' + CONFLICT_WORDS + '|' + DIFFERENCE_WORDS, clause)
        and not re.search(r'\b(?:supporting|examined|checked|considered|affected|evidence)\b', clause)
        for clause in clauses)
    if arrival and conflict or (arrival or conflict) and inventory:
        return None
    if re.search(r'(?:그리고|또한|및|하고).{0,40}(?:몇|목록|개수|찾|검색|불일치|상충|추가)', text) and (arrival or conflict):
        return None
    # Unqualified compare/change requests and negated actions are ambiguous;
    # neither may fall through to the broad inventory vocabulary.
    if re.search(r'\b(?:compare|changed|change|difference|differences|different)\b', text) and not (arrival or conflict):
        return None
    if re.search(r'\b(?:not|never|without)\s+(?:list|show|count|compare|check|find|search|retrieve|conflicts?|disagreements?)\b', text):
        return None
    metric = metrics[0] if metrics else None
    precise = any(constraints.get(key) for key in ('loinc_codes', 'methods', 'standardizations', 'units'))
    count_request = bool(re.search(r'\b(?:count\w*|inventory|how many|number of|total|overall)\b|몇\s*개|개수|목록', text))
    # These tools only accept a coarse metric. Never silently discard a
    # requested assay/code/unit constraint and return a broader finding.
    filter_query = message
    if arrival and context['comparison'] is not None:
        # This refers to the already server-bound compare_from, not a date
        # inferred from prose. Numeric dates and other filters still abstain.
        filter_query = re.sub(r'\bafter\s+(?:(?:this|that)\s+date|the\s+selected\s+date)\b', '', message, flags=re.I)
    if (precise or query_requires_record_filter(filter_query)) and (arrival or conflict or count_request):
        return None
    if arrival:
        return ('compare_record_snapshots', {'metric': metric}) if context['comparison'] is not None else None
    if conflict:
        return 'record_conflicts', {'metric': metric}
    explicit_search = bool(re.search(r'\b(?:search|find|retrieve|look up|lookup|quoted?|mentions?|containing|title|titled|phrase|excerpt|passage)\b|검색|찾|조회', text))
    read_value = bool(re.search(r'\b(?:values?|readings?|results?)\b|수치|값|결과', text))
    if not count_request and (explicit_search or (read_value and metric is not None) or precise):
        return 'search_record_evidence', {'query': message, 'limit': 5}
    if query_requires_record_filter(message):
        return None
    if re.search(r'기록|문서|측정|자료|출처|보고서', text):
        return 'record_inventory', {'metric': metric}
    if re.search(RECORD_WORDS, text):
        return 'record_inventory', {'metric': metric}
    return None


def result(context, execution, claims, trace, telemetry=None):
    response = {'mode': execution['mode'], 'answer': '\n'.join(claim['text'] for claim in claims) if claims else UNSUPPORTED,
        'claims': claims, 'trace': trace, 'execution': execution, 'scope': context['view']['scope']}
    if context['comparison'] is not None:
        response['comparison'] = {k: context['comparison'][k]['scope'] for k in ('before', 'after')}
    if telemetry is not None:
        response['telemetry'] = telemetry
    return response


def execute(context, name, args, execution, trace, *, tool_dispatch=None):
    started = perf_counter()
    value = (tool_dispatch or dispatch)(context, name, args)
    trace.append({'name': name, 'arguments': args, 'result': value, 'status': 'completed',
        'duration_ms': round((perf_counter() - started) * 1000, 2),
        'executor': 'local deterministic tool' if execution['mode'] == 'offline' else 'Meta-selected local tool',
        **{k: execution[k] for k in ('run_id', 'bundle_id', 'config_id')}})
    return value


def quarantine_request(context, message, telemetry):
    started = perf_counter()
    guard = screen_untrusted(message)
    if guard['status'] != 'quarantined':
        return None
    guard['boundary'] = 'request'
    execution = execution_context('request_guard')
    telemetry.update(execution=execution, document_guard=guard)
    trace = [{'name': 'screen_record_request', 'arguments': {},
        'result': {'claims': [], 'document_guard': guard}, 'status': 'quarantined',
        'duration_ms': round((perf_counter() - started) * 1000, 2),
        'executor': 'local deterministic guard', 'document_guard': guard,
        **{key: execution[key] for key in ('run_id', 'bundle_id', 'config_id')}}]
    response = result(context, execution, [], trace, telemetry)
    response.update(answer=REQUEST_QUARANTINED, document_guard=guard, abstained=True, provider_requests_made=0)
    return response


def offline_chat(context, message):
    guarded = quarantine_request(context, message, {})
    if guarded:
        return guarded
    execution = execution_context('offline')
    trace, claims = [], []
    route = offline_route(context, message)
    if route is not None:
        name, arguments = route
        claims = execute(context, name, arguments, execution, trace)['claims']
    return result(context, execution, claims, trace)


async def live_chat(context, message, telemetry, *, request=None):
    permitted = {n: a for n, a in ARGUMENTS.items() if n != 'compare_record_snapshots' or context['comparison'] is not None}
    return await live_selection(context, message, telemetry, arguments=permitted,
        descriptions=DESCRIPTIONS, tool_dispatch=dispatch, prompt=PROMPT, request=request)


async def live_selection(context, message, telemetry, *, arguments, descriptions, tool_dispatch, prompt, request=None):
    """Shared bounded protocol; callers supply only code-owned tool registries."""
    guarded = quarantine_request(context, message, telemetry)
    if guarded:
        return guarded
    model = provider_status()['model']
    execution = execution_context('meta', model)
    telemetry['execution'] = execution
    permitted = arguments
    tool_specs = [{'type': 'function', 'function': {'name': n, 'description': descriptions[n], 'parameters': a.model_json_schema()}} for n, a in permitted.items()]
    messages = [{'role': 'system', 'content': prompt + '\nFixed scope: ' + json.dumps(context['view']['scope'])}, {'role': 'user', 'content': message}]
    trace, known, call_count = [], {}, 0
    for _ in range(POLICY.max_rounds):
        response = await measured_request({'model': model, 'messages': messages, 'tools': tool_specs,
            # Hosted Meta accepts auto only. The application still requires a
            # validated tool call and never displays unsupported model prose.
            'tool_choice': 'auto', 'reasoning_effort': 'minimal',
            'max_completion_tokens': POLICY.max_completion_tokens}, telemetry, request=request or meta_request)
        message_out = response['choices'][0]['message']
        calls = message_out.get('tool_calls', [])
        if not calls or not isinstance(calls, list):
            raise ValueError('A permitted tool call is required')
        # Validate the whole batch before executing any member. A final selection
        # cannot hide a forbidden call later in the same model response.
        validated = []
        for call in calls:
            name = call['function']['name']
            if name not in permitted:
                raise ValueError('Tool not permitted')
            args = permitted[name].model_validate(json.loads(call['function']['arguments'])).model_dump()
            validated.append((call, name, args))
        call_count += len(validated)
        if call_count > POLICY.max_tool_calls:
            raise ValueError('Tool budget reached')
        if any(n == 'select_claims' for _, n, _ in validated) and len(validated) != 1:
            raise ValueError('Final selection must be a separate call')
        messages.append({'role': 'assistant', 'content': None, 'tool_calls': calls})
        for call, name, args in validated:
            if name == 'select_claims':
                if any(key not in known for key in args['claim_ids']):
                    raise ValueError('Unsupported claim selection')
                chosen = [known[key] for key in dict.fromkeys(args['claim_ids'])]
                return result(context, execution, chosen, trace, telemetry)
            value = execute(context, name, args, execution, trace, tool_dispatch=tool_dispatch)
            guard = screen_untrusted(value)
            guard['boundary'] = 'tool_result'
            trace[-1]['document_guard'] = guard
            if guard['status'] == 'quarantined':
                # Keep originals and accepted facts in the store. Do not forward
                # this result (including quoted instructions) to another round.
                trace[-1]['status'] = 'quarantined'
                trace[-1]['result'] = {'claims': [], 'withheld_from_model': True,
                    'document_guard': guard}
                telemetry['document_guard'] = guard
                response = result(context, execution, [], trace, telemetry)
                response.update(answer=QUARANTINED, document_guard=guard, abstained=True)
                return response
            known.update({c['id']: c for c in value['claims']})
            encoded = json.dumps(value)
            if len(encoded) > 128000:
                raise ValueError('Tool output exceeds the bounded context budget')
            messages.append({'role': 'tool', 'tool_call_id': call['id'], 'content': encoded})
    raise ValueError('Reasoning-round budget reached')

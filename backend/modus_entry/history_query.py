"""Join plans, existing reviewed-record tools, and exact Ask claims."""
from copy import deepcopy
import re

from .agent import execute, result
from .runtime import execution_context
from .history_query_plan import interpret, QueryPlan, OP_PATTERN, CHANGE
from .blood_pressure import parse_question
from .history_query_executor import execute_query, MAX_EVIDENCE, TOOL
from .report_summary import build_report_summary
from .history_tools import claim
from .medical_terms import public_concept, mentions


def plan_for_chat(context, message):
    if parse_question(message):
        return None
    if re.search(r'''["“‘]''', message) and not (OP_PATTERN.search(message) or CHANGE.search(message)):
        return None
    if re.search(r'''\b(?:source|title|document|from)\s*:?\s*' ''', message, re.I | re.X) and not (OP_PATTERN.search(message) or CHANGE.search(message)):
        return None
    plan = interpret(context, message)
    # Keep the established exact latest route and its bound continuation tokens.
    # Dynamic qualified labels use the new resolver so a substring alias cannot
    # hijack e.g. an explicitly named "Urine glucose" result.
    if plan and plan.intent == 'latest_observation' and plan.metric.startswith('concept:') and not any(
            getattr(plan, name) for name in ('start_date','end_date','exclusive_before','exclusive_after')):
        return None
    if plan and plan.intent == 'historical_observations' and plan.selection == 'all' and not any(
            getattr(plan, name) for name in ('start_date','end_date','exclusive_before','exclusive_after')):
        return None  # Existing exact/alias source searches keep their retrieval contract.
    if plan and plan.intent == 'clarification' and plan.reason == 'measurement' and not OP_PATTERN.search(message):
        return None
    return plan


def _two_reports(context, plan):
    view = context['view']
    selected = [r for r in view['facts'] + view['undated_facts'] if r['source_id'] in plan.source_ids
                and not r.get('value_withheld') and r.get('within_date_scope', True)]
    ids = {r['id'] for r in selected}
    for group in view['conflicts']:
        if ids.intersection(group['fact_ids']):
            ids.update(group['fact_ids'])
    if len(ids) > MAX_EVIDENCE:
        return {'claims':[], 'query_result':{'status':'insufficient_evidence'}, 'clarification':{
            'reason':'evidence_limit','question':'These reports exceed the Ask evidence limit. Open Records → Compare for the complete two-report summary.'}}
    # Both exact source titles are explicit in the question. Ordering is derived
    # from visible full occurrence dates; filenames or upload dates are not dates.
    def last_day(sid):
        return max((r.get('date') or '' for r in selected if r['source_id']==sid), default='')
    sources = sorted(plan.source_ids, key=last_day, reverse=True)
    summary = build_report_summary(view, {'snapshot_id':'0'*32,
        'selected_source_id':sources[0], 'comparison_source_id':sources[1]})
    output = []
    for item in summary['claims']:
        if item['verification']['status'] == 'SUPPORTED':
            output.append({k:deepcopy(item[k]) for k in ('id','text','evidence_ids')} | {'tool_name':TOOL,'status':'observed'})
    notices = list(summary.get('limitations', []))
    notices.extend(note for group in summary['rows'] for note in group['notes'])
    output.insert(0, claim('reports-'+view['scope']['scope_id'],
        'Recorded comparison of the two selected files. '+' '.join(dict.fromkeys(notices)), sorted(ids), TOOL))
    return {'claims':output,'required_claim_ids':[c['id'] for c in output],
        'query_result':{'status':'answered' if any(g['difference'] is not None for g in summary['rows']) else 'insufficient_evidence',
            'intent':plan.intent,'source_ids':sources,'groups':summary['rows'],'limitations':list(dict.fromkeys(notices))}}


def query_response(context, plan, *, question='', telemetry=None, execution=None, planner_status='deterministic'):
    # All callers, including a provider transport, pass the same typed contract.
    plan = QueryPlan.model_validate(plan)
    execution = execution or execution_context('offline')
    trace = []
    if plan.intent in {'clarification','unsupported'}:
        status = ('unsupported' if plan.intent == 'unsupported' else 'not_understood'
            if plan.reason == 'unfamiliar_wording' else 'planner_unavailable'
            if plan.reason == 'planner_unavailable' else 'clarification')
        response = result(context, execution, [], trace, telemetry)
        response.update(clarification={'kind':'history_query','question':plan.question,'choices':[],
                'reason':'unsupported_filter' if plan.reason in {'unapplied_filter','multiple_conditions','multiple_tasks'} else plan.reason},
            query_result={'status':status,'reason':plan.reason}, provider_requests_made=len((telemetry or {}).get('calls',[])))
    else:
        def dispatch(ctx, name, arguments):
            bound = QueryPlan.model_validate(arguments)
            return _two_reports(ctx, bound) if bound.intent == 'two_checkup_comparison' else execute_query(ctx, bound)
        value = execute(context, TOOL, plan.model_dump(), execution, trace, tool_dispatch=dispatch)
        if plan.metric and plan.metric.startswith('concept:') and value.get('claims'):
            mapping = public_concept(plan.metric.split(':',1)[1])
            mapping['requested_terms'] = list(dict.fromkeys(phrase for _,_,key,phrase in mentions(question)[1]
                if 'concept:'+key == plan.metric))
            mapping['matched_labels'] = sorted({r['label'] for r in value['query_result'].get('observations',[])})
            mapping['match_scope'] = 'saved_label_and_kind'
            value['retrieval'] = {'mappings':[mapping]}
        response = result(context, execution, value['claims'], trace, telemetry)
        response['query_result'] = value['query_result']
        if value.get('clarification'):
            response['clarification'] = {'kind':'history_query', 'question':value['clarification']['question'],'choices':[]}
        response['provider_requests_made'] = len((telemetry or {}).get('calls', []))
    response['query_plan'] = plan.model_dump()
    response['planner'] = {'version':'record-query-plan-v1','status':planner_status,
        'model_calls':len((telemetry or {}).get('calls', [])), 'answer_composition':'deterministic_verified_records'}
    return response

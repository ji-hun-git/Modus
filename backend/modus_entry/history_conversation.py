"""Ephemeral, scope-bound continuations. No transcript persistence or model writes."""
from collections import OrderedDict
from copy import deepcopy
import re
import secrets
from threading import Lock
from time import monotonic

from .agent import execute, result
from .history_agent import decorate
from .investigation import read
from .runtime import execution_context
from .medical_terms import unquoted
from .history_query_plan import QueryPlan, interpret
from .history_query import query_response

PREVIOUS = re.compile(r'(?:and\s+)?(?:what about\s+)?(?:the\s+)?(?:one before that|previous one|earlier one)|(?:and\s+)?before that|그\s*전(?:에는|은)?|그\s*이전\s*기록', re.I)
POINTER = re.compile(r'\b(?:before that|previous one|earlier one)\b|그\s*(?:전|이전)', re.I)
SOURCE = re.compile(r'(?:where did (?:this|that) (?:value|result) come from|show (?:its|the) (?:original )?(?:source|evidence))', re.I)
HISTORY = re.compile(r'(?:show (?:me )?(?:its|matching) history)', re.I)
FOLLOWUP = re.compile(r'\b(?:this|that) (?:value|result)\b.*\bcome from\b|\b(?:its|matching) (?:history|source|evidence)\b', re.I)


def followup_text(message):
    return re.sub(r'[?.!]+$', '', message.strip()).strip()


class HistoryConversation:
    """Per-app bounded memory. Tokens identify one immutable answer context.

    Opaque tokens expire after 30 minutes or restart. They are not account
    authorization. The existing local single-owner deployment boundary applies.
    """
    def __init__(self, capacity=256, ttl=1800, clock=monotonic):
        self.capacity, self.ttl, self.clock = capacity, ttl, clock
        self.items, self.lock = OrderedDict(), Lock()

    @staticmethod
    def scope(context):
        return {k: context['view']['scope'][k] for k in ('as_of', 'known_at')}

    def remember(self, context, response, question):
        typed = response.get('query_plan')
        if typed and not context.get('comparison') and response.get('claims'):
            plan = QueryPlan.model_validate(typed)
            if plan.metric and plan.selection != 'count' and plan.intent in {
                    'latest_observation', 'historical_observations', 'threshold_observation', 'longitudinal_history'}:
                return self._remember_query(context, response, question, plan, plan)
        reads = [s for s in response.get('trace', []) if s['name'] == 'latest_history_match']
        if context.get('comparison') or len(response.get('trace', [])) != 1 or len(reads) != 1 or not response.get('claims'):
            return response
        step = reads[0]
        day = step['result'].get('latest_recorded_date')
        if not day:
            return response
        item = {'scope': self.scope(context), 'args': deepcopy(step['arguments']),
                'before': day, 'question': question, 'kind': 'legacy'}
        # Only an exact numerical plan may support a metric-history follow-up.
        # Legacy source/title restrictions stay on their established read path.
        plan = interpret(context, question)
        if plan and plan.intent == 'latest_observation' and plan.metric:
            item['origin_plan'] = plan.model_dump()
        selected = [r for r in response.get('history_evidence', {}).get('facts', []) if r.get('date') == day]
        item.update(self._source_selection(response, selected))
        return self._retain(response, item)

    @staticmethod
    def _source_selection(response, selected):
        evidence = response.get('history_evidence', {})
        rows = evidence.get('facts', []) + evidence.get('undated_facts', [])
        ids = {r['id'] for r in selected}
        return {'selected_fact_ids': sorted(ids),
            'source_ready': len(ids) == 1 and {r['id'] for r in rows} == ids and not evidence.get('conflicts')}

    def _remember_query(self, context, response, question, plan, origin):
        selected = response.get('query_result', {}).get('observations', [])
        if not selected:
            return response
        dates = {r.get('date') for r in selected}
        day = next(iter(dates)) if len(dates) == 1 and all(dates) else None
        item = {'kind':'query', 'scope':self.scope(context), 'plan':plan.model_dump(),
            'origin_plan':origin.model_dump(), 'before':day, 'question':question,
            **self._source_selection(response, selected)}
        return self._retain(response, item)

    def _retain(self, response, item):
        token = secrets.token_urlsafe(32)
        item = deepcopy(item)
        item['expires'] = self.clock()+self.ttl
        with self.lock:
            self.items = OrderedDict((k,v) for k,v in self.items.items() if v['expires'] > self.clock())
            self.items[token] = item
            while len(self.items) > self.capacity:
                self.items.popitem(last=False)
        suggestions = ['What about the one before that?'] if item['before'] else []
        if item.get('source_ready'):
            suggestions.append('Where did this value come from?')
        if item.get('origin_plan'):
            suggestions.append('Show matching history' if item['origin_plan'].get('condition') else 'Show its history')
        response['continuation'] = {'token':token, 'subject':item['question'], 'before_date':item['before'],
            'expires_in_seconds':self.ttl, 'suggested_question':suggestions[0] if suggestions else 'Name a result to inspect its source.',
            'supported_questions':suggestions}
        return response

    def answer(self, context, message, token=None):
        text = followup_text(message)
        if not (POINTER.search(unquoted(text)) or FOLLOWUP.search(unquoted(text)) or SOURCE.fullmatch(text) or HISTORY.fullmatch(text)):
            return None
        reason = None
        action = 'previous' if PREVIOUS.fullmatch(text) else 'source' if SOURCE.fullmatch(text) else 'history' if HISTORY.fullmatch(text) else None
        if action is None:
            reason = 'Please name the record and any new conditions in a full question. I will not guess which earlier record you mean.'
        with self.lock:
            item = deepcopy(self.items.get(token)) if token else None
        if not reason and (not item or item['expires'] <= self.clock()):
            reason = 'Ask a latest-record question first, then ask for the one before it. This conversation may have expired or restarted.'
        if not reason and (context.get('comparison') or item['scope'] != self.scope(context)):
            reason = 'Your history view changed. Ask the full question again so the answer uses the dates and saved versions you selected.'
        if not reason and action == 'previous' and not item.get('before'):
            reason = 'That answer does not identify one fully dated result group. Ask for a specific latest result before asking for the one before it.'
        if not reason and action == 'source' and not item.get('source_ready'):
            reason = 'That answer does not identify one unambiguous result. Open the Source button on the result you mean; I will not choose between tied, conflicting or uncertain records.'
        if not reason and action == 'history' and not item.get('origin_plan'):
            reason = 'Please name the measurement and any conditions in a full history question. I will not drop an earlier source or record restriction.'
        if reason:
            response = result(context, execution_context('request_guard'), [], [])
            response.update(provider_requests_made=0, clarification={'kind':'history_followup','question':reason,'choices':[]})
            return decorate(context,response)
        if action in {'source','history'} or item['kind'] == 'query':
            return self._query_answer(context, item, action)
        # The client and model cannot choose this cutoff or replace its query.
        bounded = {**context, 'previous_before':item['before']}
        trace=[]; execution=execution_context('offline')
        value=execute(bounded,'latest_history_match',item['args'],execution,trace,tool_dispatch=read)
        response=decorate(bounded,result(bounded,execution,value['claims'],trace))
        response.update(provider_requests_made=0, followup={'subject':item['question'], 'before_date':item['before'], 'operation':'previous'})
        return self.remember(context,response,item['question'])

    def _query_answer(self, context, item, action):
        original = item.get('origin_plan') or item.get('plan')
        origin = QueryPlan.model_validate(original) if original else None
        if action == 'source':
            plan = QueryPlan(intent='source_inspection', fact_id=item['selected_fact_ids'][0], metric=origin.metric if origin else None)
        elif action == 'history':
            plan = QueryPlan.model_validate({**origin.model_dump(), 'selection':'all',
                'intent':'threshold_observation' if origin.condition else 'longitudinal_history'})
        else:
            active = QueryPlan.model_validate(item.get('plan') or item['origin_plan'])
            cutoff = min(day for day in (active.exclusive_before, item['before']) if day)
            plan = QueryPlan.model_validate({**active.model_dump(), 'selection':'latest',
                'intent':'threshold_observation' if active.condition else 'latest_observation',
                'exclusive_before':cutoff})
        response = decorate(context, query_response(context, plan, question=item['question']))
        response['followup'] = {'subject':item['question'], 'before_date':item['before'], 'operation':action}
        if action == 'source':
            # Source inspection does not reset or broaden the navigation query.
            return self._retain(response, item)
        return self._remember_query(context, response, item['question'], plan, origin)

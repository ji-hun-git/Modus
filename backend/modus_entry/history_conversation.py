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

PREVIOUS = re.compile(r'(?:and\s+)?(?:what about\s+)?(?:the\s+)?(?:one before that|previous one|earlier one)|(?:and\s+)?before that|그\s*전(?:에는|은)?|그\s*이전\s*기록', re.I)
POINTER = re.compile(r'\b(?:before that|previous one|earlier one)\b|그\s*(?:전|이전)', re.I)


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
        reads = [s for s in response.get('trace', []) if s['name'] == 'latest_history_match']
        if context.get('comparison') or len(response.get('trace', [])) != 1 or len(reads) != 1 or not response.get('claims'):
            return response
        step = reads[0]
        day = step['result'].get('latest_recorded_date')
        if not day:
            return response
        token = secrets.token_urlsafe(32)
        item = {'scope': self.scope(context), 'args': deepcopy(step['arguments']),
                'before': day, 'question': question, 'expires': self.clock()+self.ttl}
        with self.lock:
            self.items = OrderedDict((k,v) for k,v in self.items.items() if v['expires'] > self.clock())
            self.items[token] = item
            while len(self.items) > self.capacity:
                self.items.popitem(last=False)
        response['continuation'] = {'token':token, 'subject':question, 'before_date':day,
            'expires_in_seconds':self.ttl, 'suggested_question':'What about the one before that?'}
        return response

    def answer(self, context, message, token=None):
        text = followup_text(message)
        if not POINTER.search(unquoted(text)):
            return None
        reason = None
        if not PREVIOUS.fullmatch(text):
            reason = 'Please name the record and any new conditions in a full question. I will not guess which earlier record you mean.'
        with self.lock:
            item = deepcopy(self.items.get(token)) if token else None
        if not reason and (not item or item['expires'] <= self.clock()):
            reason = 'Ask a latest-record question first, then ask for the one before it. This conversation may have expired or restarted.'
        if not reason and (context.get('comparison') or item['scope'] != self.scope(context)):
            reason = 'Your history view changed. Ask the full question again so the answer uses the dates and saved versions you selected.'
        if reason:
            response = result(context, execution_context('request_guard'), [], [])
            response.update(provider_requests_made=0, clarification={'kind':'history_followup','question':reason,'choices':[]})
            return decorate(context,response)
        # The client and model cannot choose this cutoff or replace its query.
        bounded = {**context, 'previous_before':item['before']}
        trace=[]; execution=execution_context('offline')
        value=execute(bounded,'latest_history_match',item['args'],execution,trace,tool_dispatch=read)
        response=decorate(bounded,result(bounded,execution,value['claims'],trace))
        response.update(provider_requests_made=0, followup={'subject':item['question'], 'before_date':item['before']})
        return self.remember(context,response,item['question'])

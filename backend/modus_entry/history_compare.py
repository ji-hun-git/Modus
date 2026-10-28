"""Bounded replay of reviewed record arrivals across one captured history."""
from datetime import date, datetime
import json
import re

from pydantic import AwareDatetime, field_validator

from .history_tools import capture_history
from .models import Strict

MAX_FACTS_PER_VIEW = 2000
MAX_RESPONSE_BYTES = 4 * 1024 * 1024


class HistoryCompareRequest(Strict):
    as_of: date | None = None
    before_known_at: AwareDatetime
    after_known_at: AwareDatetime | None = None

    @field_validator('as_of', mode='before')
    @classmethod
    def exact_event_date(cls, value):
        if value is not None and type(value) is not date and not (
                isinstance(value, str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}', value)):
            raise ValueError('Use an exact ISO event date or null')
        return value

    @field_validator('before_known_at', 'after_known_at', mode='before')
    @classmethod
    def explicit_availability(cls, value):
        if value is not None and not isinstance(value, datetime) and not (
                isinstance(value, str) and re.fullmatch(
                    r'\d{4}-\d{2}-\d{2}[Tt]\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:[Zz]|[+-]\d{2}:\d{2})', value)):
            raise ValueError('Availability must be an ISO timestamp with a timezone and at most six fractional digits')
        return value


def compare_history(store, request):
    pair = capture_history(store, request.as_of.isoformat() if request.as_of else None,
                           request.after_known_at, request.before_known_at)['comparison']
    for side in ('before', 'after'):
        if len(pair[side]['facts']) + len(pair[side]['undated_facts']) > MAX_FACTS_PER_VIEW:
            raise ValueError('This comparison exceeds 2,000 records per view. Choose an earlier event or availability cutoff.')
    added_dated = sum(row.get('date') is not None for row in pair['added'])
    result = {'format': 'modus-history-comparison-v1', **pair,
              'added_counts': {'total': len(pair['added']), 'dated': added_dated,
                               'undated': len(pair['added']) - added_dated}}
    if len(json.dumps(result, ensure_ascii=False, allow_nan=False).encode('utf-8')) > MAX_RESPONSE_BYTES:
        raise ValueError('This comparison exceeds the 4 MB response limit. Choose an earlier event or availability cutoff.')
    return result

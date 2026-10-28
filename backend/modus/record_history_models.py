"""Explicit owner-reviewed facts; original evidence and availability are server-owned."""
from datetime import date
from decimal import Decimal, InvalidOperation
import re
import math
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

FactKind = Literal['measurement', 'encounter', 'recorded_diagnosis', 'procedure', 'prescription',
                   'vaccination', 'imaging_text', 'recorded_text']


class ReviewedFact(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    id: str = Field(min_length=1, max_length=160)
    kind: FactKind
    label: str = Field(min_length=1, max_length=200)
    value: str = Field(min_length=1, max_length=16000)
    unit: str | None = Field(max_length=80)
    occurred_on: str | None = Field(max_length=100)
    facility: str | None = Field(max_length=200)

    @model_validator(mode='after')
    def nonblank_fields(self):
        if any(not value.strip() for value in (self.id, self.label, self.value)):
            raise ValueError('Fact identity, label and value cannot be blank')
        if any(value is not None and not value.strip() for value in (self.unit, self.occurred_on, self.facility)):
            raise ValueError('Use null for an unknown unit, date or facility')
        return self


class SourceEvidence(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    source_quote: str = Field(min_length=1, max_length=16000)
    page: int | None = Field(ge=1, le=1000)
    bbox: list[float] | None = Field(min_length=4, max_length=4)
    model_confidence: float | None = Field(ge=0, le=1, allow_inf_nan=False)

    @model_validator(mode='after')
    def check_region(self):
        if not self.source_quote.strip():
            raise ValueError('Source quote cannot be blank')
        if self.bbox is not None:
            x0, y0, x1, y1 = self.bbox
            if not all(math.isfinite(v) and 0 <= v <= 1 for v in self.bbox) or x0 >= x1 or y0 >= y1:
                raise ValueError('Invalid proposed source region')
        return self


def date_information(value):
    if value is None:
        return {'date': None, 'date_precision': 'unknown'}
    if re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        try:
            return {'date': date.fromisoformat(value).isoformat(), 'date_precision': 'day'}
        except ValueError:
            pass
    if re.fullmatch(r'\d{4}', value) and 1 <= int(value) <= 9999:
        return {'date': None, 'date_precision': 'year'}
    if re.fullmatch(r'\d{4}-\d{2}', value):
        try:
            date.fromisoformat(value + '-01')
            return {'date': None, 'date_precision': 'month'}
        except ValueError:
            pass
    return {'date': None, 'date_precision': 'unresolved'}


def numeric_value(value):
    if (not isinstance(value, str) or len(value) > 80 or
            not re.fullmatch(r'[+-]?(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+)(?:[eE][+-]?[0-9]{1,2})?', value)):
        return None
    try:
        parsed = Decimal(value)
        if parsed.is_finite():
            return format(parsed, 'f')
    except InvalidOperation:
        pass
    return None


def temporal_original_allowed(source, as_of):
    """Unknown or later source facts cannot leak through a dated original view."""
    if as_of is None:
        return True
    if 'source_fact_dates' in source:
        dates = source['source_fact_dates']
        return bool(dates) and all(isinstance(day, str) and day <= as_of for day in dates)
    return max(source.get('date') or '', source.get('original_date') or '') <= as_of


def proposed_facts(draft):
    facts = draft.get('facts')
    if facts is None:
        facts = draft.get('extraction_proposal', {}).get('fields', [])
    if not isinstance(facts, list) or not 1 <= len(facts) <= 1000:
        raise ValueError('A history draft requires 1 to 1,000 source facts')
    if any(not isinstance(fact, dict) or not isinstance(fact.get('id'), str) for fact in facts):
        raise ValueError('Invalid source fact identities')
    if len({fact['id'] for fact in facts}) != len(facts):
        raise ValueError('Source fact identities must be distinct')
    return {fact['id']: fact for fact in facts}

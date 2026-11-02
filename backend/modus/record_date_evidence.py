"""Separate date passages are evidence candidates, never automatic row joins."""
import math
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ProposedDateEvidence(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    value: str = Field(min_length=1, max_length=100)
    source_quote: str = Field(min_length=1, max_length=800)
    page: int = Field(ge=1, le=12)
    bbox: list[float] | None = Field(min_length=4, max_length=4)

    @model_validator(mode='after')
    def valid_passage(self):
        if not self.value.strip() or not self.source_quote.strip():
            raise ValueError('Date evidence must contain a value and verbatim passage')
        if self.bbox is not None:
            x0, y0, x1, y1 = self.bbox
            if not all(math.isfinite(v) and 0 <= v <= 1 for v in self.bbox) or x0 >= x1 or y0 >= y1:
                raise ValueError('Date source region must be a nonempty normalized rectangle')
        return self


class DateEvidenceCheck(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    status: Literal['matched_text', 'mismatch', 'unavailable']
    issues: list[Literal['quote_not_on_page', 'date_not_in_quote',
                         'no_independent_page_text', 'ocr_text_is_unverified']]


class RecordedDateEvidence(ProposedDateEvidence):
    check: DateEvidenceCheck
    # Even an exact quote cannot prove the date applies to this row.
    relation: Literal['requires_review']


def contains(value, text):
    return re.search(r'(?<![\w.])' + re.escape(' '.join(value.split())) + r'(?![\w.])', text) is not None


def checked_date_evidence(proposal, pages):
    anchor = ProposedDateEvidence.model_validate(proposal).model_dump()
    page = next((p for p in pages if p['page'] == anchor['page']), None)
    if page is None:
        raise ValueError('Date evidence references an unavailable page')
    quote = ' '.join(anchor['source_quote'].split())
    text = ' '.join(page['text'].split())
    issues = []
    if not contains(anchor['value'], quote):
        issues.append('date_not_in_quote')
    independent = bool(text) and page.get('text_source') != 'local_teleocr'
    if independent:
        if quote not in text:
            issues.append('quote_not_on_page')
    else:
        issues.append('ocr_text_is_unverified' if page.get('ocr_text') or text else 'no_independent_page_text')
    status = ('mismatch' if any(i in {'date_not_in_quote', 'quote_not_on_page'} for i in issues)
              else 'matched_text' if independent else 'unavailable')
    return {**anchor, 'check': {'status': status, 'issues': issues}, 'relation': 'requires_review'}

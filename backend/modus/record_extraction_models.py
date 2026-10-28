"""Bounded draft schemas; model confidence and source regions are proposals."""
import math
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

DOCUMENT_KINDS = {
    'lab_report': ('measurement', 'recorded_text'),
    'checkup': ('measurement', 'encounter', 'recorded_diagnosis', 'recorded_text'),
    'prescription': ('prescription', 'recorded_text'),
    'discharge_summary': ('encounter', 'recorded_diagnosis', 'procedure', 'prescription', 'measurement', 'recorded_text'),
    'vaccination_card': ('vaccination', 'recorded_text'),
    'imaging_report': ('imaging_text', 'encounter', 'recorded_text'),
    'other': ('measurement', 'encounter', 'recorded_diagnosis', 'procedure', 'prescription', 'vaccination', 'imaging_text', 'recorded_text'),
}
MAX_FIELDS = 100
REASONS = ('matches_source', 'value_mismatch', 'quote_mismatch', 'date_mismatch',
           'unit_mismatch', 'page_mismatch', 'unclear_source')


class ProposedField(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    kind: Literal['measurement', 'encounter', 'recorded_diagnosis', 'procedure', 'prescription', 'vaccination', 'imaging_text', 'recorded_text']
    label: str = Field(min_length=1, max_length=200)
    value: str = Field(min_length=1, max_length=800)
    unit: str | None = Field(max_length=80)
    occurred_on: str | None = Field(max_length=100)
    source_quote: str = Field(min_length=1, max_length=800)
    page: int = Field(ge=1, le=12)
    bbox: list[float] | None = Field(min_length=4, max_length=4)
    model_confidence: float | None = Field(ge=0, le=1, allow_inf_nan=False)

    @model_validator(mode='after')
    def bounded_source(self):
        if not self.label.strip() or not self.value.strip() or not self.source_quote.strip():
            raise ValueError('Empty source values are not facts')
        if self.unit is not None and not self.unit.strip():
            raise ValueError('Use null for unknown units')
        if self.occurred_on is not None and not self.occurred_on.strip():
            raise ValueError('Use null for unknown dates')
        if self.bbox is not None:
            x0, y0, x1, y1 = self.bbox
            if not all(math.isfinite(v) and 0 <= v <= 1 for v in self.bbox) or x0 >= x1 or y0 >= y1:
                raise ValueError('Source region must be a nonempty normalized rectangle')
        return self


class ProposedExtraction(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    document_type: Literal['lab_report', 'checkup', 'prescription', 'discharge_summary', 'vaccination_card', 'imaging_report', 'other']
    fields: list[ProposedField] = Field(max_length=MAX_FIELDS)

    @model_validator(mode='after')
    def type_appropriate_fields(self):
        if any(field.kind not in DOCUMENT_KINDS[self.document_type] for field in self.fields):
            raise ValueError('Field kind does not match the document schema')
        return self


class ExtractionResponse(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    extraction: ProposedExtraction


class FieldCheck(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    field_id: str = Field(pattern=r'^field-[1-9][0-9]{0,2}$')
    status: Literal['supported', 'mismatch', 'uncertain']
    reason: Literal['matches_source', 'value_mismatch', 'quote_mismatch', 'date_mismatch', 'unit_mismatch', 'page_mismatch', 'unclear_source']

    @model_validator(mode='after')
    def consistent_result(self):
        if (self.status == 'supported') != (self.reason == 'matches_source'):
            raise ValueError('Verifier status and reason disagree')
        if self.status == 'uncertain' and self.reason != 'unclear_source':
            raise ValueError('Uncertain verifier result needs unclear_source')
        if self.status == 'mismatch' and self.reason == 'unclear_source':
            raise ValueError('Unclear source is uncertain, not a confirmed mismatch')
        return self


class VerificationResponse(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    checks: list[FieldCheck] = Field(max_length=MAX_FIELDS)


def _object(properties):
    return {'type': 'object', 'properties': properties, 'required': list(properties), 'additionalProperties': False}


def extraction_schema():
    """Seven nested alternatives, without unsupported top-level anyOf/oneOf."""
    properties = ProposedField.model_json_schema()['properties']
    alternatives = []
    for document_type, kinds in DOCUMENT_KINDS.items():
        fields = {**properties, 'kind': {'type': 'string', 'enum': list(kinds)}}
        alternatives.append(_object({
            'document_type': {'type': 'string', 'enum': [document_type]},
            'fields': {'type': 'array', 'maxItems': MAX_FIELDS, 'items': _object(fields)},
        }))
    return _object({'extraction': {'anyOf': alternatives}})


def verification_schema():
    return _object({'checks': {'type': 'array', 'maxItems': MAX_FIELDS, 'items': _object({
        'field_id': {'type': 'string'}, 'status': {'type': 'string', 'enum': ['supported', 'mismatch', 'uncertain']},
        'reason': {'type': 'string', 'enum': list(REASONS)},
    })}})

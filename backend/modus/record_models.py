"""Recorded facts and review proposals, with no interpretation metadata."""
from datetime import date, datetime
import json
import math
from typing import Annotated, Literal

from pydantic import AfterValidator, AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator


# The legacy LOINC entries are recognition/demo metadata, not validated outbound
# mappings. A metric category alone does not establish method, specimen or scale.
METRICS = {
    "hba1c": {"label": "HbA1c", "unit": "%", "loinc": "4548-4"},
    "egfr": {"label": "eGFR", "unit": "mL/min/1.73m2", "loinc": "33914-3"},
    "ldl": {"label": "LDL cholesterol", "unit": "mg/dL", "loinc": "13457-7"},
}


def _nonblank_unit(value):
    if not value.strip():
        raise ValueError('A recorded unit must contain non-whitespace text')
    return value


RecordedUnit = Annotated[str, AfterValidator(_nonblank_unit)]


class FHIRCoding(BaseModel):
    """Allowlisted source coding data; unrecognized systems/codes grant no authority."""
    model_config = ConfigDict(extra='ignore')
    system: str | None = Field(default=None, max_length=240)
    version: str | None = Field(default=None, max_length=80)
    code: str | None = Field(default=None, max_length=160)
    display: str | None = Field(default=None, max_length=500)
    userSelected: bool | None = None


class FHIRCodeableConcept(BaseModel):
    model_config = ConfigDict(extra='ignore')
    coding: list[FHIRCoding] = Field(default_factory=list, max_length=32)
    text: str | None = Field(default=None, max_length=2000)


class FHIRIdentifier(BaseModel):
    model_config = ConfigDict(extra='ignore')
    system: str | None = Field(default=None, max_length=240)
    value: str | None = Field(default=None, max_length=500)
    use: str | None = Field(default=None, max_length=80)


class FHIRSpecimenReference(BaseModel):
    model_config = ConfigDict(extra='ignore')
    reference: str | None = Field(default=None, max_length=500)
    type: str | None = Field(default=None, max_length=240)
    display: str | None = Field(default=None, max_length=500)
    identifier: FHIRIdentifier | None = None


class FHIRQuantity(BaseModel):
    model_config = ConfigDict(extra='ignore')
    value: float = Field(ge=0, allow_inf_nan=False, strict=True)
    unit: str | None = Field(default=None, max_length=80)
    system: str | None = Field(default=None, max_length=240)
    code: str | None = Field(default=None, max_length=80)
    comparator: Literal['<', '<=', '>=', '>'] | None = None


class OntologyUnit(BaseModel):
    model_config = ConfigDict(extra='forbid')
    raw_unit: str | None = Field(default=None, max_length=80)
    system: str | None = Field(default=None, max_length=240)
    code: str | None = Field(default=None, max_length=80)
    identity: str | None = Field(default=None, max_length=80)
    status: Literal['recognized', 'missing', 'unrecognized', 'conflicting']


class OntologyMatch(BaseModel):
    model_config = ConfigDict(extra='forbid')
    system: str = Field(max_length=240)
    code: str = Field(max_length=160)
    display: str = Field(max_length=160)
    metric: Literal['hba1c', 'egfr', 'ldl']
    property: Literal['mass_fraction', 'substance_fraction', 'mass_concentration', 'volume_rate_per_area']
    specimen: Literal['blood', 'serum_or_plasma', 'serum_plasma_or_blood']
    method: Literal['unspecified', 'hplc', 'creatinine_mdrd', 'creatinine_ckd_epi_2009', 'creatinine_ckd_epi_2021', 'calculated', 'direct_assay']
    standardization: Literal['unspecified', 'ngsp_dcct', 'ifcc']
    code_status: Literal['active', 'discouraged']
    source: str = Field(max_length=240)


class OntologyResolution(BaseModel):
    model_config = ConfigDict(extra='forbid')
    catalog_version: str = Field(max_length=100)
    status: Literal['resolved', 'unresolved', 'conflicting', 'unit_unresolved', 'unit_mismatch']
    metric: Literal['hba1c', 'egfr', 'ldl'] | None
    concept_ids: list[Literal['hba1c', 'egfr', 'ldl']] = Field(max_length=3)
    matches: list[OntologyMatch] = Field(max_length=32)
    issues: list[str] = Field(max_length=8)
    unit: OntologyUnit


class FHIRNormalizationBasis(BaseModel):
    model_config = ConfigDict(extra='forbid')
    metric: Literal['hba1c', 'egfr', 'ldl']
    value: float = Field(ge=0, allow_inf_nan=False)
    unit: RecordedUnit = Field(max_length=80)
    date: date
    reported_at: str | None = Field(default=None, max_length=120)


class FHIRProvenance(BaseModel):
    """Bounded lossless slice of FHIR source semantics, never executable content.

    Extension/contained resources and unknown fields are outside this projection;
    original uploaded bytes remain the authority for the complete source document.
    """
    model_config = ConfigDict(extra='forbid')
    origin: Literal['fhir'] = 'fhir'
    original_code: FHIRCodeableConcept
    original_status: str | None = Field(default=None, max_length=80)
    original_method: FHIRCodeableConcept | None = None
    original_specimen: FHIRSpecimenReference | None = None
    original_quantity: FHIRQuantity
    original_effective_date_time: str = Field(min_length=10, max_length=80)
    original_issued: str | None = Field(default=None, max_length=120)
    basis: FHIRNormalizationBasis
    resolution: OntologyResolution

    @field_validator('original_effective_date_time')
    @classmethod
    def actual_date_or_timestamp(cls, value):
        if len(value) == 10:
            date.fromisoformat(value)
        else:
            timestamp = datetime.fromisoformat(value.replace('Z', '+00:00'))
            if 'T' not in value or timestamp.tzinfo is None:
                raise ValueError('FHIR measurement timestamp needs an offset')
        return value

    @model_validator(mode='after')
    def bounded_metadata(self):
        if len(json.dumps(self.model_dump(mode='json'), ensure_ascii=False).encode('utf-8')) > 65536:
            raise ValueError('FHIR provenance exceeds the bounded metadata limit')
        return self


class Observation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1, max_length=160)
    metric: Literal["hba1c", "egfr", "ldl"]
    value: float
    unit: RecordedUnit = Field(min_length=1, max_length=80)
    date: date
    source_id: str = Field(min_length=1, max_length=160)
    source_span: str = Field(min_length=1, max_length=800)
    source_span_withheld: bool = False
    page: int | None = Field(default=None, ge=1)
    reviewed_fields: list[Literal['metric', 'value', 'unit', 'date']] = Field(default_factory=list)
    reported_at: AwareDatetime | None = None
    reported_at_raw: str | None = Field(default=None, max_length=120)
    fhir_provenance: FHIRProvenance | None = None
    # Read projections add availability from the source; ingestion cannot set it.
    available_at: AwareDatetime | None = None
    availability_basis: str | None = None

    @field_validator("value")
    @classmethod
    def finite(cls, value):
        if not math.isfinite(value) or value < 0:
            raise ValueError("A laboratory value must be finite and non-negative")
        return value


class Claim(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    metric: str | None = None
    text: str
    evidence_ids: list[str] = Field(min_length=1)
    tool_name: str
    status: Literal["observed", "limited", "conflict", "unknown"]
    window_start: str | None = None
    window_end: str | None = None


class ExtractedObservation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    metric: Literal["hba1c", "egfr", "ldl"]
    value: float = Field(ge=0, allow_inf_nan=False)
    unit: RecordedUnit = Field(min_length=1, max_length=80)
    date: date
    source_span: str = Field(min_length=1, max_length=800)
    page: int | None = Field(ge=1)


class ExtractedDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")
    observations: list[ExtractedObservation] = Field(max_length=1000)


class ReviewedObservation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1, max_length=160)
    metric: Literal["hba1c", "egfr", "ldl"]
    value: float = Field(ge=0, allow_inf_nan=False)
    unit: RecordedUnit = Field(min_length=1, max_length=80)
    date: date

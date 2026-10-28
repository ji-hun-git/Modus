from datetime import date
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, AwareDatetime
from modus.record_models import ReviewedObservation
from modus.record_history_models import ReviewedFact

RELEASE = '0.1.0-records'


class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid')


class ScopeRequest(Strict):
    as_of: date
    known_at: AwareDatetime | None = None
    compare_from: AwareDatetime | None = None


class CompareRequest(Strict):
    as_of: date
    before_known_at: AwareDatetime
    after_known_at: AwareDatetime | None = None


class ChatRequest(ScopeRequest):
    message: str = Field(min_length=1, max_length=2000)


class ExportRequest(ScopeRequest):
    known_at: AwareDatetime


class CommitRequest(Strict):
    draft_id: str = Field(min_length=1, max_length=160)
    synthetic_confirmed: Literal[True]
    reviewed_observations: list[ReviewedObservation] = Field(min_length=1, max_length=1000)


class HistoryCommitRequest(Strict):
    draft_id: str = Field(min_length=1, max_length=160)
    synthetic_confirmed: Literal[True]
    reviewed_facts: list[ReviewedFact] = Field(min_length=1, max_length=1000)


class ProfileRequest(Strict):
    date_of_birth: str | None = Field(max_length=10)

"""Strict jury contracts and bounded, explicitly supplied synthetic inputs."""
import hashlib
import io
import json
import math
from pathlib import Path
from typing import Literal

from PIL import Image
from pydantic import BaseModel, ConfigDict, Field, model_validator

ENDPOINTS = {
    'meta': ('https://api.meta.ai/v1/chat/completions', 'MODUS_META_KEY', 'muse'),
    'anthropic': ('https://api.anthropic.com/v1/messages', 'ANTHROPIC_API_KEY', 'claude'),
    'openai': ('https://api.openai.com/v1/responses', 'OPENAI_API_KEY', 'gpt'),
}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)


def fingerprint(value):
    return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()


def json_loads(text):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('Duplicate JSON key')
            result[key] = value
        return result
    return json.loads(text, object_pairs_hook=unique, parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Nonfinite JSON')))


class Provider(BaseModel):
    model_config = ConfigDict(extra='allow', strict=True)
    provider: Literal['meta', 'anthropic', 'openai']
    family: str
    model: str = Field(min_length=1, max_length=100)
    endpoint: str
    env_key: str
    input_usd_per_million: float | int
    output_usd_per_million: float | int
    max_output_tokens: int = Field(ge=100, le=4000)
    settings: dict
    prior_spend_usd: float | int
    ceiling_usd: float | int
    allocation_usd: float | int
    input_cost_multiplier: float | int = 1
    api_version: str | None = None

    @model_validator(mode='after')
    def locked_endpoint_and_settings(self):
        if (self.endpoint, self.env_key, self.family) != ENDPOINTS[self.provider]:
            raise ValueError('Provider endpoint, key or family is outside the literal allowlist')
        costs = (self.input_usd_per_million, self.output_usd_per_million, self.ceiling_usd,
                 self.allocation_usd, self.input_cost_multiplier)
        if any(isinstance(n, bool) or not math.isfinite(n) or n <= 0 for n in costs):
            raise ValueError('Invalid provider prices or limits')
        if self.ceiling_usd > 10 or self.allocation_usd > self.ceiling_usd or not 0 <= self.prior_spend_usd <= self.ceiling_usd:
            raise ValueError('Provider ceiling cannot exceed $10')
        if self.provider == 'meta' and (set(self.settings) - {'reasoning_effort'} or self.settings.get('reasoning_effort') not in {'minimal', 'low', 'medium'}):
            raise ValueError('Unsupported Meta settings')
        if self.provider == 'anthropic' and (self.settings != {'thinking': {'type': 'between_tools'}, 'effort': 'low'} or self.api_version != '2026-10-21'):
            raise ValueError('Unsupported Anthropic settings')
        if self.provider == 'openai' and self.settings != {'reasoning': {'effort': 'none'}, 'store': False}:
            raise ValueError('Unsupported OpenAI settings')
        return self


class ModelLock(BaseModel):
    model_config = ConfigDict(extra='allow', strict=True)
    schema_name: Literal['modus-jury-models-v1'] = Field(alias='schema')
    rubric_version: Literal['poll-v1']
    providers: list[Provider]

    @model_validator(mode='after')
    def independent_families(self):
        if {p.provider for p in self.providers} != set(ENDPOINTS) or len(self.providers) != 3:
            raise ValueError('Exactly three distinct configured provider families are required')
        return self


class Verdict(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    status: Literal['pass', 'fail', 'ambiguous', 'fuzzy', 'not_applicable']
    reason: str = Field(min_length=1, max_length=2000)
    checker_sha256: str = Field(pattern=r'^[0-9a-f]{64}$')
    artifact_sha256: str = Field(pattern=r'^[0-9a-f]{64}$')


class Case(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    id: str = Field(pattern=r'^[A-Za-z0-9_-]{1,100}$')
    candidate_provider: Literal['meta', 'anthropic', 'openai', 'local', 'unknown']
    artifact: dict
    screenshots: list[str] = Field(max_length=1)
    deterministic: dict[str, Verdict]

    @model_validator(mode='after')
    def code_first(self):
        if set(self.deterministic) != {'C', 'E'}:
            raise ValueError('Explicit code verdicts for C and E are required')
        digest = fingerprint(self.artifact)
        if len(canonical(self.artifact).encode()) > 180000:
            raise ValueError('Artifact exceeds the bounded input size')
        for key, value in self.deterministic.items():
            if value.artifact_sha256 != digest or value.status == ('fuzzy' if key == 'C' else 'ambiguous'):
                raise ValueError('Code verdict does not match this artifact or criterion')
        return self


class Inputs(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    schema_name: Literal['modus-jury-input-v1'] = Field(alias='schema')
    synthetic: Literal[True]
    cases: list[Case] = Field(min_length=1, max_length=30)

    @model_validator(mode='after')
    def unique_ids(self):
        if len({c.id for c in self.cases}) != len(self.cases):
            raise ValueError('Duplicate case ID')
        return self


class Assessment(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    criterion: Literal['A', 'B', 'C', 'D', 'E']
    score: int = Field(ge=1, le=5)
    passed: bool
    advice_flag: bool
    reason: str = Field(min_length=1, max_length=1800)
    evidence_refs: list[str] = Field(max_length=12)


class Judgement(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    assessments: list[Assessment] = Field(min_length=1, max_length=5)


def validate_judgement(text, criteria):
    value = Judgement.model_validate(json_loads(text))
    keys = [a.criterion for a in value.assessments]
    if len(keys) != len(set(keys)) or set(keys) != set(criteria):
        raise ValueError('Judge omitted, repeated or invented a criterion')
    return value.model_dump()


def output_schema(criteria):
    # Provider-portable wire schema; numerical/string bounds are enforced locally.
    properties = {'criterion': {'type': 'string', 'enum': criteria}, 'score': {'type': 'integer'},
        'passed': {'type': 'boolean'}, 'advice_flag': {'type': 'boolean'},
        'reason': {'type': 'string'}, 'evidence_refs': {'type': 'array', 'items': {'type': 'string'}}}
    return {'type': 'object', 'properties': {'assessments': {'type': 'array', 'items': {
        'type': 'object', 'properties': properties, 'required': list(properties), 'additionalProperties': False}}},
        'required': ['assessments'], 'additionalProperties': False}


def permitted_path(path):
    path = Path(path)
    if any(any(word in part.casefold() for word in ('holdout', 'heldout', 'workflow_v1', 'documents_v1', 'baseline')) for part in path.parts):
        raise ValueError('Protected evaluation paths are forbidden')
    return path


def checked_path(path):
    path = permitted_path(path).absolute()
    if '..' in path.parts:
        raise ValueError('Parent traversal is forbidden')
    # Inspect link entries before resolving; never follow a link into a sealed set.
    for part in (*reversed(path.parents), path):
        if part.is_symlink() or (hasattr(part, 'is_junction') and part.is_junction()):
            raise ValueError('Linked evaluation paths are forbidden')
    return permitted_path(path.resolve())


def load_inputs(path):
    path = checked_path(path)
    if path.stat().st_size > 1024 * 1024:
        raise ValueError('Input manifest too large')
    inputs = Inputs.model_validate(json_loads(path.read_text(encoding='utf-8')))
    loaded = []
    for case in inputs.cases:
        images = []
        for relative in case.screenshots:
            if Path(relative).is_absolute() or '..' in Path(relative).parts:
                raise ValueError('Screenshots must stay in the supplied fixture folder')
            candidate = checked_path(path.parent / relative)
            if not candidate.is_relative_to(path.parent):
                raise ValueError('Screenshot escapes the supplied fixture folder')
            if candidate.stat().st_size > 4 * 1024 * 1024:
                raise ValueError('Screenshot too large')
            raw = candidate.read_bytes()
            with Image.open(io.BytesIO(raw)) as image:
                if image.format not in {'PNG', 'JPEG'} or image.width * image.height > 16_000_000 or getattr(image, 'n_frames', 1) != 1:
                    raise ValueError('Use one bounded PNG/JPEG screenshot')
                image.verify()
                mime = 'image/png' if image.format == 'PNG' else 'image/jpeg'
            images.append({'raw': raw, 'mime': mime, 'sha256': hashlib.sha256(raw).hexdigest()})
        loaded.append((case, images))
    return inputs, loaded

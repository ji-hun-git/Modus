"""Versioned, server-owned agent limits. Model input cannot override these."""
import json
from pathlib import Path
from pydantic import BaseModel, ConfigDict, Field

class AgentPolicy(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    version: str
    max_rounds: int = Field(ge=1, le=12)
    max_tool_calls: int = Field(ge=1, le=30)
    max_selected_claims: int = Field(ge=1, le=12)
    max_completion_tokens: int = Field(ge=128, le=4096)
    request_timeout_seconds: int = Field(ge=5, le=120)
    allow_contributor_mode: bool = False

POLICY = AgentPolicy.model_validate(json.loads((Path(__file__).resolve().parents[2]/'config/agent-policy.json').read_text(encoding='utf-8')))

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from backend.models.response import JudgeSynthesis, JudgeVerdict, ParsedResponse


TaskType = str
ModeType = str
SessionStatus = str


class AgentResponse(BaseModel):
    agent_id: str
    anonymous_label: str
    parsed: ParsedResponse
    raw_content: str = ""
    tokens_input: int = 0
    tokens_output: int = 0
    cost_usd: float = 0.0
    latency_ms: int = 0
    error: str | None = None


class RoundData(BaseModel):
    round_number: int
    responses: list[AgentResponse] = Field(default_factory=list)
    judge_verdict: JudgeVerdict | None = None
    anonymization_mapping: dict[str, str] = Field(default_factory=dict)


class SessionConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_type: TaskType = "review_text"
    question: str = ""
    source_text: str = ""
    context: str = ""
    preserve_style: bool = True
    allow_restructure: bool = False
    ask_clarifying_questions: bool = True
    mode: ModeType = "peer_review"
    agents: list[str] = Field(default_factory=list)
    max_rounds: int = Field(default=3, ge=1, le=5)
    web_search: bool = False
    budget_usd: float | None = Field(default=None, ge=0.0)
    language: str = "ru"

    @field_validator("task_type")
    @classmethod
    def validate_task_type(cls, value: str) -> str:
        allowed = {"review_text", "fact_check"}
        if value not in allowed:
            raise ValueError(f"task_type must be one of {sorted(allowed)}")
        return value

    @field_validator("mode")
    @classmethod
    def validate_mode(cls, value: str) -> str:
        allowed = {"debate", "consensus", "peer_review"}
        if value not in allowed:
            raise ValueError(f"mode must be one of {sorted(allowed)}")
        return value

    @field_validator("source_text")
    @classmethod
    def normalize_source_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("question")
    @classmethod
    def normalize_question(cls, value: str) -> str:
        return value.strip()

    @field_validator("agents")
    @classmethod
    def validate_agents(cls, value: list[str]) -> list[str]:
        if value and len(value) < 2:
            raise ValueError("at least two agents are required")
        return value

    @field_validator("language")
    @classmethod
    def normalize_language(cls, value: str) -> str:
        value = value.strip() or "ru"
        return value

    @field_validator("context")
    @classmethod
    def normalize_context(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def validate_required_fields(self) -> "SessionConfig":
        if self.task_type == "review_text" and not self.source_text:
            raise ValueError("source_text is required for review_text")
        if self.task_type == "fact_check" and not self.question and not self.source_text:
            raise ValueError("question or source_text is required for fact_check")
        return self


class SessionResult(BaseModel):
    session_id: str = Field(default_factory=lambda: str(uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    status: SessionStatus = "completed"
    task_type: str
    question: str
    source_text: str = ""
    context: str = ""
    rounds: list[RoundData] = Field(default_factory=list)
    clarification_requests: list[str] = Field(default_factory=list)
    synthesis: JudgeSynthesis | None = None
    total_tokens: int = 0
    total_cost_usd: float = 0.0


class SessionSummary(BaseModel):
    session_id: str
    created_at: datetime
    task_type: str
    status: SessionStatus
    question: str
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    rounds_count: int = 0
    has_synthesis: bool = False


class StoredSessionRecord(BaseModel):
    saved_at: datetime
    config: SessionConfig
    result: SessionResult

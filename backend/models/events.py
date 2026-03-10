from __future__ import annotations

from pydantic import BaseModel, Field

from backend.models.response import JudgeSynthesis, JudgeVerdict, ParsedResponse


class RoundStartEvent(BaseModel):
    round: int
    agents: list[str] = Field(default_factory=list)


class ResponseChunkEvent(BaseModel):
    round: int
    agent_id: str
    chunk: str


class ResponseCompleteEvent(BaseModel):
    round: int
    agent_id: str
    parsed: ParsedResponse
    tokens: int
    cost: float


class JudgeVerdictEvent(BaseModel):
    round: int
    verdict: JudgeVerdict


class SynthesisCompleteEvent(BaseModel):
    synthesis: JudgeSynthesis


class ErrorEvent(BaseModel):
    agent_id: str | None = None
    error: str
    debate_continues: bool = True


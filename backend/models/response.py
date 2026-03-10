from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


ConfidenceLevel = Literal["high", "medium", "low"]
SeverityLevel = Literal["high", "medium", "low"]
ParseQuality = Literal["json_clean", "json_extracted", "free_text_fallback"]
StopReason = Literal["consensus", "stagnation", "max_rounds", "needs_user_input"]


class Agreement(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    with_: str = Field(alias="with")
    point: str
    why: str


class Disagreement(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    with_: str = Field(alias="with")
    point: str
    counterargument: str


class Issue(BaseModel):
    segment: str
    problem: str
    severity: SeverityLevel
    suggestion: str


class ParsedResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    position: str
    confidence: ConfidenceLevel
    position_changed: bool = False
    change_reason: str = ""
    agreements: list[Agreement] = Field(default_factory=list)
    disagreements: list[Disagreement] = Field(default_factory=list)
    issues: list[Issue] = Field(default_factory=list)
    clarification_requests: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    revised_text: str = ""
    full_argument: str
    parse_quality: ParseQuality = "json_clean"


class JudgeVerdict(BaseModel):
    round_number: int
    argument_novelty: float = Field(ge=0.0, le=1.0)
    position_changes: list[str] = Field(default_factory=list)
    stagnation: bool
    convergence_points: list[str] = Field(default_factory=list)
    remaining_disagreements: list[str] = Field(default_factory=list)
    needs_user_input: bool = False
    clarification_requests: list[str] = Field(default_factory=list)
    should_stop: bool = False
    stop_reason: StopReason | None = None


class JudgeSynthesis(BaseModel):
    summary: str
    revised_text: str = ""
    key_changes: list[str] = Field(default_factory=list)
    fact_check_summary: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    remaining_disagreements: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)


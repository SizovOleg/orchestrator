from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


ProviderName = Literal["anthropic", "openai"]


class ProviderConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    api_key: str
    model: str


class AgentConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = ""
    provider: ProviderName
    display_name: str
    temperature: float = Field(ge=0.0, le=1.0)
    persona: str


class JudgeConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: ProviderName
    temperature: float = Field(ge=0.0, le=1.0)
    display_name: str = "Судья"

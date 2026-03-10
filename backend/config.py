from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from backend.models.agent import AgentConfig, JudgeConfig, ProviderConfig


ENV_PATTERN = re.compile(r"\$\{([^}]+)\}")


class DatabaseSettings(BaseModel):
    dsn: str


class BraveSearchSettings(BaseModel):
    api_key: str = ""
    max_results_per_query: int = Field(default=5, ge=1)


class ServerSettings(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8001
    cors_origins: list[str] = Field(default_factory=list)


class LimitsSettings(BaseModel):
    max_rounds: int = Field(default=5, ge=1, le=10)
    max_agents_per_debate: int = Field(default=6, ge=2, le=10)
    budget_default_usd: float = Field(default=5.0, ge=0.0)


class FeatureSettings(BaseModel):
    enable_sse: bool = False
    enable_web_search: bool = True
    enable_storage: bool = False


class AppSettings(BaseModel):
    database: DatabaseSettings
    brave_search: BraveSearchSettings
    server: ServerSettings
    limits: LimitsSettings
    features: FeatureSettings = Field(default_factory=FeatureSettings)
    providers: dict[str, ProviderConfig] = Field(default_factory=dict)
    agents: dict[str, AgentConfig] = Field(default_factory=dict)
    judge: JudgeConfig | None = None


def _substitute_env(value: Any) -> Any:
    if isinstance(value, str):
        def replace(match: re.Match[str]) -> str:
            return os.environ.get(match.group(1), "")

        return ENV_PATTERN.sub(replace, value)
    if isinstance(value, list):
        return [_substitute_env(item) for item in value]
    if isinstance(value, dict):
        return {key: _substitute_env(item) for key, item in value.items()}
    return value


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    content = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return _substitute_env(content)


def load_config(
    settings_path: str | Path = "config/settings.yaml",
    agents_path: str | Path | None = None,
) -> AppSettings:
    settings_file = Path(settings_path)
    agents_file = Path(agents_path) if agents_path else Path("config/agents.yaml")
    if not agents_file.exists():
        agents_file = Path("config/agents.example.yaml")

    settings_data = _read_yaml(settings_file)
    agents_data = _read_yaml(agents_file)

    providers = {
        provider_name: ProviderConfig(**provider_data)
        for provider_name, provider_data in agents_data.get("providers", {}).items()
    }
    agents = {
        agent_id: AgentConfig(id=agent_id, **agent_data)
        for agent_id, agent_data in agents_data.get("agents", {}).items()
    }
    judge_raw = agents_data.get("judge")
    judge = JudgeConfig(**judge_raw) if judge_raw else None

    return AppSettings(
        **settings_data,
        providers=providers,
        agents=agents,
        judge=judge,
    )


def default_agent_ids(settings: AppSettings) -> list[str]:
    return list(settings.agents.keys())[:4]

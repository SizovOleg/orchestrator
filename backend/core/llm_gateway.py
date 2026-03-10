from __future__ import annotations

from time import perf_counter

from litellm import acompletion, completion_cost
from litellm.exceptions import Timeout
from pydantic import BaseModel

from backend.config import AppSettings
from backend.models.agent import AgentConfig


class LLMCallResult(BaseModel):
    content: str
    tokens_input: int = 0
    tokens_output: int = 0
    cost_usd: float = 0.0
    latency_ms: int = 0
    agent_id: str = ""


class LLMGateway:
    def __init__(self, config: AppSettings) -> None:
        self.config = config

    async def call(
        self,
        agent: AgentConfig,
        messages: list[dict[str, str]],
        stream: bool = False,
    ) -> LLMCallResult:
        if stream:
            raise NotImplementedError("Streaming is deferred in the local MVP.")

        provider = self.config.providers[agent.provider]
        last_error: Exception | None = None

        for _ in range(2):
            started_at = perf_counter()
            try:
                response = await acompletion(
                    model=provider.model,
                    messages=messages,
                    temperature=self._resolve_temperature(provider.model, agent.temperature),
                    api_key=provider.api_key,
                    max_tokens=4096,
                    stream=False,
                )
                usage = getattr(response, "usage", None)
                latency_ms = int((perf_counter() - started_at) * 1000)
                return LLMCallResult(
                    content=response.choices[0].message.content or "",
                    tokens_input=int(getattr(usage, "prompt_tokens", 0) or 0),
                    tokens_output=int(getattr(usage, "completion_tokens", 0) or 0),
                    cost_usd=float(completion_cost(completion_response=response)),
                    latency_ms=latency_ms,
                    agent_id=agent.id,
                )
            except Timeout as exc:
                last_error = exc
                continue

        raise RuntimeError(f"LLM call failed for agent {agent.id}: {last_error}")

    async def call_judge(self, messages: list[dict[str, str]]) -> LLMCallResult:
        if self.config.judge is None:
            raise RuntimeError("Judge is not configured.")
        provider = self.config.providers[self.config.judge.provider]
        started_at = perf_counter()
        response = await acompletion(
            model=provider.model,
            messages=messages,
            temperature=self._resolve_temperature(provider.model, self.config.judge.temperature),
            api_key=provider.api_key,
            max_tokens=4096,
            stream=False,
        )
        usage = getattr(response, "usage", None)
        latency_ms = int((perf_counter() - started_at) * 1000)
        return LLMCallResult(
            content=response.choices[0].message.content or "",
            tokens_input=int(getattr(usage, "prompt_tokens", 0) or 0),
            tokens_output=int(getattr(usage, "completion_tokens", 0) or 0),
            cost_usd=float(completion_cost(completion_response=response)),
            latency_ms=latency_ms,
            agent_id="judge",
        )

    async def health_check(self) -> dict[str, bool]:
        return {
            provider_name: bool(provider.api_key and provider.model)
            for provider_name, provider in self.config.providers.items()
        }

    def _resolve_temperature(self, model: str, requested: float) -> float:
        normalized_model = model.removeprefix("openai/")
        if normalized_model.startswith("gpt-5"):
            return 1.0
        return requested

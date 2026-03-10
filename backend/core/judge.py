from __future__ import annotations

import json
import re

from backend.models.response import JudgeSynthesis, JudgeVerdict
from backend.models.session import RoundData, SessionConfig, SessionResult


CODE_BLOCK_PATTERN = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL | re.IGNORECASE)


class Judge:
    def __init__(self, gateway, prompt_builder) -> None:
        self.gateway = gateway
        self.prompt_builder = prompt_builder

    async def evaluate_round(self, config: SessionConfig, current_round: RoundData) -> JudgeVerdict:
        messages = self.prompt_builder.judge_round(config, current_round)
        result = await self.gateway.call_judge(messages)
        payload = self._extract_json(result.content)
        if payload is None:
            return JudgeVerdict(
                round_number=current_round.round_number,
                argument_novelty=0.0,
                stagnation=False,
                should_stop=False,
                needs_user_input=False,
            )
        return JudgeVerdict.model_validate(payload)

    async def synthesize(self, config: SessionConfig, session: SessionResult) -> JudgeSynthesis:
        messages = self.prompt_builder.judge_synthesis(config, session)
        result = await self.gateway.call_judge(messages)
        payload = self._extract_json(result.content)
        if payload is None:
            return JudgeSynthesis(
                summary=result.content.strip() or "Синтез отсутствует.",
                revised_text="",
                key_changes=[],
                fact_check_summary=[],
                open_questions=[],
                remaining_disagreements=[],
                sources=[],
            )
        return JudgeSynthesis.model_validate(payload)

    def _extract_json(self, raw: str) -> dict | None:
        raw = (raw or "").strip()
        try:
            payload = json.loads(raw)
            return payload if isinstance(payload, dict) else None
        except json.JSONDecodeError:
            pass
        match = CODE_BLOCK_PATTERN.search(raw)
        if not match:
            return None
        try:
            payload = json.loads(match.group(1))
        except json.JSONDecodeError:
            return None
        return payload if isinstance(payload, dict) else None


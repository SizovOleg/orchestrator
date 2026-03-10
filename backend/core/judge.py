from __future__ import annotations

import json
import re

from backend.core.json_repair import load_json_object
from backend.models.response import JudgeSynthesis, JudgeVerdict
from backend.models.session import RoundData, SessionConfig, SessionResult


CODE_BLOCK_PATTERN = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)


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
        return JudgeVerdict.model_validate(self._normalize_verdict_payload(payload))

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
        for candidate in self._json_candidates(raw):
            payload = load_json_object(candidate)
            if payload is not None:
                return payload
        return None

    def _json_candidates(self, raw: str) -> list[str]:
        candidates: list[str] = []
        seen: set[str] = set()

        def add(candidate: str | None) -> None:
            if not candidate:
                return
            normalized = candidate.strip()
            if normalized and normalized not in seen:
                seen.add(normalized)
                candidates.append(normalized)

        add(raw)
        add(self._extract_first_json_object(raw))
        for block in CODE_BLOCK_PATTERN.findall(raw):
            add(block)
            add(self._extract_first_json_object(block))
        return candidates

    def _extract_first_json_object(self, text: str) -> str | None:
        start = text.find("{")
        if start == -1:
            return None

        depth = 0
        in_string = False
        escaped = False

        for index in range(start, len(text)):
            char = text[index]
            if in_string:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    in_string = False
                continue

            if char == '"':
                in_string = True
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return text[start:index + 1]
        return None

    def _normalize_verdict_payload(self, payload: dict) -> dict:
        allowed_stop_reasons = {"consensus", "stagnation", "max_rounds", "needs_user_input"}
        normalized = dict(payload)
        stop_reason = normalized.get("stop_reason")
        if stop_reason not in allowed_stop_reasons:
            normalized["stop_reason"] = None
            if normalized.get("should_stop") and not normalized.get("needs_user_input"):
                normalized["should_stop"] = False
        return normalized

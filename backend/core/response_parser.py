from __future__ import annotations

import json
import re
from typing import Any

from backend.models.response import ParsedResponse


CODE_BLOCK_PATTERN = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL | re.IGNORECASE)


class ResponseParser:
    def parse(self, raw: str) -> ParsedResponse:
        raw = (raw or "").strip()

        payload = self._load_json(raw)
        if payload is not None:
            return self._to_model(payload, "json_clean", raw)

        match = CODE_BLOCK_PATTERN.search(raw)
        if match:
            payload = self._load_json(match.group(1))
            if payload is not None:
                return self._to_model(payload, "json_extracted", raw)

        return ParsedResponse(
            position=self._extract_position(raw),
            confidence="low",
            revised_text="",
            full_argument=raw or "Ответ отсутствует.",
            parse_quality="free_text_fallback",
        )

    def _load_json(self, candidate: str) -> dict[str, Any] | None:
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            return None
        return payload if isinstance(payload, dict) else None

    def _to_model(self, payload: dict[str, Any], quality: str, raw: str) -> ParsedResponse:
        normalized = {
            "position": self._as_text(payload.get("position")) or self._extract_position(raw),
            "confidence": self._normalize_confidence(payload.get("confidence")),
            "position_changed": bool(payload.get("position_changed", False)),
            "change_reason": self._as_text(payload.get("change_reason")),
            "agreements": payload.get("agreements") or [],
            "disagreements": payload.get("disagreements") or [],
            "issues": payload.get("issues") or [],
            "clarification_requests": self._normalize_strings(payload.get("clarification_requests")),
            "sources": self._normalize_strings(payload.get("sources")),
            "revised_text": self._as_text(payload.get("revised_text")),
            "full_argument": self._as_text(payload.get("full_argument")) or raw,
            "parse_quality": quality,
        }
        return ParsedResponse.model_validate(normalized)

    def _normalize_confidence(self, value: Any) -> str:
        normalized = self._as_text(value).lower()
        if normalized in {"high", "medium", "low"}:
            return normalized
        return "low"

    def _normalize_strings(self, value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        return [self._as_text(item) for item in value if self._as_text(item)]

    def _as_text(self, value: Any) -> str:
        if value is None:
            return ""
        return str(value).strip()

    def _extract_position(self, raw: str) -> str:
        if not raw:
            return "Позиция не распознана."
        first_line = raw.splitlines()[0].strip()
        return first_line[:200] if first_line else raw[:200]

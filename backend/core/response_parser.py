from __future__ import annotations

import json
import re
from typing import Any

from backend.core.json_repair import load_json_object
from backend.models.response import ParsedResponse


CODE_BLOCK_PATTERN = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)


class ResponseParser:
    def parse(self, raw: str) -> ParsedResponse:
        raw = (raw or "").strip()

        for candidate, quality in self._json_candidates(raw):
            payload = self._load_json(candidate)
            if payload is not None:
                return self._to_model(payload, quality, raw)

        return ParsedResponse(
            position=self._extract_position(raw),
            confidence="low",
            revised_text="",
            full_argument=raw or "Ответ отсутствует.",
            parse_quality="free_text_fallback",
        )

    def _json_candidates(self, raw: str) -> list[tuple[str, str]]:
        candidates: list[tuple[str, str]] = []
        seen: set[str] = set()

        def add(candidate: str, quality: str) -> None:
            normalized = candidate.strip()
            if normalized and normalized not in seen:
                seen.add(normalized)
                candidates.append((normalized, quality))

        add(raw, "json_clean")
        extracted = self._extract_first_json_object(raw)
        if extracted:
            add(extracted, "json_extracted")

        for block in CODE_BLOCK_PATTERN.findall(raw):
            add(block, "json_extracted")
            extracted = self._extract_first_json_object(block)
            if extracted:
                add(extracted, "json_extracted")

        return candidates

    def _load_json(self, candidate: str) -> dict[str, Any] | None:
        return load_json_object(candidate)

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

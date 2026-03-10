from __future__ import annotations

import json
import re
from typing import Any


TRAILING_COMMA_PATTERN = re.compile(r",(\s*[}\]])")


def load_json_object(candidate: str) -> dict[str, Any] | None:
    normalized = candidate.strip()
    if not normalized:
        return None

    for variant in (normalized, repair_json_like_text(normalized)):
        try:
            payload = json.loads(variant)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload
    return None


def repair_json_like_text(text: str) -> str:
    text = TRAILING_COMMA_PATTERN.sub(r"\1", text)

    repaired: list[str] = []
    in_string = False
    escaped = False

    for char in text:
        if in_string:
            if escaped:
                repaired.append(char)
                escaped = False
                continue

            if char == "\\":
                repaired.append(char)
                escaped = True
                continue

            if char == '"':
                repaired.append(char)
                in_string = False
                continue

            if char == "\n":
                repaired.append("\\n")
                continue
            if char == "\r":
                continue
            if char == "\t":
                repaired.append("\\t")
                continue

            repaired.append(char)
            continue

        repaired.append(char)
        if char == '"':
            in_string = True

    return "".join(repaired)

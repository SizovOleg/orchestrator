from backend.core.response_parser import ResponseParser


def test_parse_clean_json() -> None:
    parser = ResponseParser()
    parsed = parser.parse(
        """{
          "position": "Текст нуждается в доработке.",
          "confidence": "high",
          "position_changed": false,
          "change_reason": "",
          "agreements": [],
          "disagreements": [],
          "issues": [],
          "clarification_requests": [],
          "sources": [],
          "revised_text": "Исправленный текст",
          "full_argument": "Подробный аргумент."
        }"""
    )
    assert parsed.parse_quality == "json_clean"
    assert parsed.revised_text == "Исправленный текст"


def test_parse_json_from_code_block() -> None:
    parser = ResponseParser()
    parsed = parser.parse(
        """```json
        {
          "position": "Факт пока не доказан.",
          "confidence": "low",
          "position_changed": false,
          "change_reason": "",
          "agreements": [],
          "disagreements": [],
          "issues": [],
          "clarification_requests": [],
          "sources": [],
          "revised_text": "",
          "full_argument": "Требуется уточнение."
        }
        ```"""
    )
    assert parsed.parse_quality == "json_extracted"
    assert parsed.confidence == "low"


def test_parse_free_text_fallback() -> None:
    parser = ResponseParser()
    parsed = parser.parse("Свободный текст без JSON")
    assert parsed.parse_quality == "free_text_fallback"
    assert parsed.confidence == "low"


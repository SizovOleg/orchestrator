from __future__ import annotations

import json

from backend.core.llm_gateway import LLMCallResult


class FakeGateway:
    def __init__(self, settings) -> None:
        self.settings = settings
        self.agent_calls = 0
        self.judge_calls = 0

    async def call(self, agent, messages, stream: bool = False) -> LLMCallResult:
        self.agent_calls += 1
        user_prompt = messages[-1]["content"]
        needs_context = "Дополнительный контекст" not in user_prompt
        round_number = 2 if "Ответы оппонентов" in user_prompt else 1

        payload = {
            "position": f"{agent.display_name}: текст требует доработки.",
            "confidence": "medium" if agent.id == "claude-creative" else "high",
            "position_changed": round_number > 1,
            "change_reason": "После обсуждения позиция стала точнее." if round_number > 1 else "",
            "agreements": [] if round_number == 1 else [
                {
                    "with": "Response A",
                    "point": "Нужна более ясная структура",
                    "why": "Это повышает читаемость текста.",
                }
            ],
            "disagreements": [] if round_number == 1 else [
                {
                    "with": "Response B",
                    "point": "Слишком глубокая перестройка текста",
                    "counterargument": "По умолчанию надо сохранить авторский стиль.",
                }
            ],
            "issues": [
                {
                    "segment": "Первый абзац",
                    "problem": "Формулировка перегружена и неясна.",
                    "severity": "medium",
                    "suggestion": "Разбить предложение и уточнить причинно-следственную связь.",
                }
            ],
            "clarification_requests": (
                [
                    "Нужно ли сохранять академический стиль без упрощения терминов?",
                    "Нужно ли сокращать текст или только улучшить ясность?",
                ]
                if needs_context and round_number == 1
                else []
            ),
            "sources": ["https://example.org/fact"] if "fact_check" in user_prompt else [],
            "revised_text": "" if needs_context and round_number == 1 else (
                "Исправленный текст. Формулировки упрощены, логика связана, стиль автора в целом сохранён."
            ),
            "full_argument": "Подробное объяснение замечаний и предлагаемых правок.",
        }
        return LLMCallResult(
            content=json.dumps(payload, ensure_ascii=False),
            tokens_input=120,
            tokens_output=220,
            cost_usd=0.02,
            latency_ms=25,
            agent_id=agent.id,
        )

    async def call_judge(self, messages) -> LLMCallResult:
        self.judge_calls += 1
        if self.judge_calls <= 2:
            payload = {
                "round_number": self.judge_calls,
                "argument_novelty": 0.5,
                "position_changes": ["Response C уточнил критерии правки"] if self.judge_calls == 2 else [],
                "stagnation": False,
                "convergence_points": ["Текст надо сделать яснее и точнее"],
                "remaining_disagreements": ["Степень допустимой перестройки структуры"] if self.judge_calls == 2 else [],
                "needs_user_input": False,
                "clarification_requests": [],
                "should_stop": self.judge_calls >= 2,
                "stop_reason": "max_rounds" if self.judge_calls >= 2 else None,
            }
        else:
            payload = {
                "summary": "Текст улучшен, основные логические и стилистические проблемы устранены.",
                "revised_text": "Итоговая версия текста после коллективной правки.",
                "key_changes": [
                    "Упрощены перегруженные формулировки",
                    "Уточнены причинно-следственные связи",
                ],
                "fact_check_summary": ["Явных неподтверждённых утверждений не осталось."],
                "open_questions": [],
                "remaining_disagreements": [],
                "sources": ["https://example.org/fact"],
            }
        return LLMCallResult(
            content=json.dumps(payload, ensure_ascii=False),
            tokens_input=80,
            tokens_output=100,
            cost_usd=0.01,
            latency_ms=20,
            agent_id="judge",
        )

    async def health_check(self) -> dict[str, bool]:
        return {"anthropic": True, "openai": True}


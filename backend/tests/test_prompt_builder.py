from backend.core.prompt_builder import PromptBuilder
from backend.models.agent import AgentConfig
from backend.models.response import ParsedResponse
from backend.models.session import AgentResponse, RoundData, SessionConfig, SessionResult


def test_round_1_contains_persona_and_source_text() -> None:
    builder = PromptBuilder("backend/prompts")
    agent = AgentConfig(
        id="claude-analyst",
        provider="anthropic",
        display_name="Аналитик",
        temperature=0.3,
        persona="Строгий аналитик.",
    )
    config = SessionConfig(
        task_type="review_text",
        question="Улучши текст",
        source_text="Исходный текст",
    )
    messages = builder.round_1(agent, config)
    assert "Строгий аналитик." in messages[0]["content"]
    assert "Исходный текст" in messages[1]["content"]


def test_round_n_uses_anonymous_labels() -> None:
    builder = PromptBuilder("backend/prompts")
    agent = AgentConfig(
        id="gpt-critic",
        provider="openai",
        display_name="Критик",
        temperature=0.4,
        persona="Методологический критик.",
    )
    config = SessionConfig(
        task_type="review_text",
        question="Улучши текст",
        source_text="Исходный текст",
    )
    responses = [
        AgentResponse(
            agent_id="claude-analyst",
            anonymous_label="Response A",
            parsed=ParsedResponse(
                position="Нужна правка.",
                confidence="high",
                revised_text="Текст",
                full_argument="Аргумент",
            ),
        )
    ]
    anonymized, _ = builder.anonymize(responses)
    messages = builder.round_n(agent, config, history=[], anonymized=anonymized, is_skeptic=True)
    assert "Response A" in messages[1]["content"]
    assert "claude-analyst" not in messages[1]["content"]
    assert "роль скептика" in messages[0]["content"]


def test_judge_synthesis_contains_history() -> None:
    builder = PromptBuilder("backend/prompts")
    session = SessionResult(
        task_type="review_text",
        question="Улучши текст",
        source_text="Исходный текст",
        rounds=[
            RoundData(
                round_number=1,
                responses=[
                    AgentResponse(
                        agent_id="a",
                        anonymous_label="Response A",
                        parsed=ParsedResponse(
                            position="Нужно упростить текст.",
                            confidence="high",
                            revised_text="Исправленный текст",
                            full_argument="Подробное объяснение.",
                        ),
                    )
                ],
            )
        ],
    )
    config = SessionConfig(
        task_type="review_text",
        question="Улучши текст",
        source_text="Исходный текст",
    )
    messages = builder.judge_synthesis(config, session)
    assert "История раундов" in messages[1]["content"]
    assert "Нужно упростить текст." in messages[1]["content"]


import pytest

from backend.config import load_config
from backend.core.judge import Judge
from backend.core.orchestrator import SessionOrchestrator
from backend.core.prompt_builder import PromptBuilder
from backend.core.response_parser import ResponseParser
from backend.core.web_search import WebSearch
from backend.models.response import JudgeVerdict
from backend.models.session import SessionConfig
from backend.tests.integration.test_data import FakeGateway


@pytest.mark.asyncio
async def test_orchestrator_requests_clarification_without_context() -> None:
    settings = load_config()
    gateway = FakeGateway(settings)
    orchestrator = SessionOrchestrator(
        gateway=gateway,
        prompt_builder=PromptBuilder("backend/prompts"),
        response_parser=ResponseParser(),
        judge=Judge(gateway, PromptBuilder("backend/prompts")),
        web_search=WebSearch(settings.brave_search),
        config=settings,
    )
    result = await orchestrator.run_session(
        SessionConfig(
            task_type="review_text",
            question="Улучши текст",
            source_text="Это сложный научный абзац с перегруженной формулировкой.",
            max_rounds=2,
        )
    )
    assert result.status == "needs_user_input"
    assert result.clarification_requests
    assert result.synthesis is None


@pytest.mark.asyncio
async def test_orchestrator_completes_when_context_present() -> None:
    settings = load_config()
    gateway = FakeGateway(settings)
    orchestrator = SessionOrchestrator(
        gateway=gateway,
        prompt_builder=PromptBuilder("backend/prompts"),
        response_parser=ResponseParser(),
        judge=Judge(gateway, PromptBuilder("backend/prompts")),
        web_search=WebSearch(settings.brave_search),
        config=settings,
    )
    result = await orchestrator.run_session(
        SessionConfig(
            task_type="review_text",
            question="Улучши текст",
            source_text="Это сложный научный абзац с перегруженной формулировкой.",
            context="Сохраняй академический стиль и не сокращай текст слишком сильно.",
            max_rounds=2,
        )
    )
    assert result.status == "completed"
    assert result.synthesis is not None
    assert result.synthesis.revised_text
    assert result.total_tokens > 0


class JudgeNeedsUserInputStub:
    async def evaluate_round(self, config, current_round):
        return JudgeVerdict(
            round_number=current_round.round_number,
            argument_novelty=0.2,
            position_changes=[],
            stagnation=False,
            convergence_points=[],
            remaining_disagreements=[],
            needs_user_input=True,
            clarification_requests=["Уточните исходный источник."],
            should_stop=False,
            stop_reason="needs_user_input",
        )

    async def synthesize(self, config, session):
        from backend.models.response import JudgeSynthesis

        return JudgeSynthesis(
            summary="Синтез выполнен без уточняющих вопросов.",
            revised_text="Итоговый текст.",
            key_changes=[],
            fact_check_summary=[],
            open_questions=[],
            remaining_disagreements=[],
            sources=[],
        )


@pytest.mark.asyncio
async def test_orchestrator_ignores_judge_questions_when_disabled() -> None:
    settings = load_config()
    gateway = FakeGateway(settings)
    orchestrator = SessionOrchestrator(
        gateway=gateway,
        prompt_builder=PromptBuilder("backend/prompts"),
        response_parser=ResponseParser(),
        judge=JudgeNeedsUserInputStub(),
        web_search=WebSearch(settings.brave_search),
        config=settings,
    )
    result = await orchestrator.run_session(
        SessionConfig(
            task_type="fact_check",
            question="Проверь утверждение",
            source_text="Это тестовый фрагмент.",
            ask_clarifying_questions=False,
            max_rounds=1,
        )
    )
    assert result.status == "completed"
    assert result.clarification_requests == []
    assert result.synthesis is not None

import pytest

from backend.config import load_config
from backend.core.judge import Judge
from backend.core.orchestrator import SessionOrchestrator
from backend.core.prompt_builder import PromptBuilder
from backend.core.response_parser import ResponseParser
from backend.core.web_search import WebSearch
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


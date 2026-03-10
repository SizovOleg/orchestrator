import pytest
from httpx import ASGITransport, AsyncClient

from backend.config import load_config
from backend.main import create_app
from backend.tests.integration.test_data import FakeGateway


@pytest.mark.asyncio
async def test_api_returns_questions_when_context_missing() -> None:
    settings = load_config()
    app = create_app(settings=settings, gateway=FakeGateway(settings))
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.post(
            "/api/sessions",
            json={
                "task_type": "review_text",
                "question": "Улучши текст",
                "source_text": "Это деловой абзац, который нужно переписать яснее.",
                "max_rounds": 2,
            },
        )
    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "needs_user_input"
    assert payload["clarification_requests"]


@pytest.mark.asyncio
async def test_api_completes_review_when_context_given() -> None:
    settings = load_config()
    app = create_app(settings=settings, gateway=FakeGateway(settings))
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.post(
            "/api/sessions",
            json={
                "task_type": "review_text",
                "question": "Улучши текст",
                "source_text": "Это научный абзац, который нужно переписать точнее.",
                "context": "Сохраняй научный стиль, но сделай фразы короче.",
                "max_rounds": 2,
            },
        )
    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "completed"
    assert payload["synthesis"]["revised_text"]
    assert len(payload["rounds"]) >= 1

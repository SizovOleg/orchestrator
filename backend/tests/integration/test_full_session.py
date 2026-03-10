import pytest
from httpx import ASGITransport, AsyncClient

from backend.config import load_config
from backend.main import create_app
from backend.storage.session_store import FileSessionStore
from backend.tests.integration.test_data import FakeGateway


@pytest.mark.asyncio
async def test_api_returns_questions_when_context_missing(tmp_path) -> None:
    settings = load_config()
    app = create_app(
        settings=settings,
        gateway=FakeGateway(settings),
        session_store=FileSessionStore(tmp_path / "sessions"),
    )
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
async def test_api_completes_review_when_context_given(tmp_path) -> None:
    settings = load_config()
    app = create_app(
        settings=settings,
        gateway=FakeGateway(settings),
        session_store=FileSessionStore(tmp_path / "sessions"),
    )
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


@pytest.mark.asyncio
async def test_api_metrics_summary_contains_provider_models(tmp_path) -> None:
    settings = load_config()
    app = create_app(
        settings=settings,
        gateway=FakeGateway(settings),
        session_store=FileSessionStore(tmp_path / "sessions"),
    )
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.get("/api/metrics/summary")
    payload = response.json()
    assert response.status_code == 200
    assert payload["app"] == "SciProof"
    assert payload["storage"]["backend"] == "local_file"
    assert payload["providers"]["anthropic"]["model"]
    assert payload["providers"]["openai"]["model"]


@pytest.mark.asyncio
async def test_api_persists_and_returns_session_history(tmp_path) -> None:
    settings = load_config()
    app = create_app(
        settings=settings,
        gateway=FakeGateway(settings),
        session_store=FileSessionStore(tmp_path / "sessions"),
    )
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        create_response = await client.post(
            "/api/sessions",
            json={
                "task_type": "review_text",
                "question": "Улучши текст",
                "source_text": "Это научный абзац, который нужно переписать точнее.",
                "context": "Сохраняй научный стиль.",
                "max_rounds": 2,
            },
        )
        created = create_response.json()

        history_response = await client.get("/api/sessions")
        history = history_response.json()

        stored_response = await client.get(f"/api/sessions/{created['session_id']}")
        stored = stored_response.json()

    assert create_response.status_code == 200
    assert history_response.status_code == 200
    assert stored_response.status_code == 200
    assert len(history) == 1
    assert history[0]["session_id"] == created["session_id"]
    assert stored["config"]["question"] == "Улучши текст"
    assert stored["result"]["session_id"] == created["session_id"]

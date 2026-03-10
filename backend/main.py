from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api import agents, metrics, sessions
from backend.config import AppSettings, load_config
from backend.core.judge import Judge
from backend.core.llm_gateway import LLMGateway
from backend.core.orchestrator import SessionOrchestrator
from backend.core.prompt_builder import PromptBuilder
from backend.core.response_parser import ResponseParser
from backend.core.web_search import WebSearch


def create_app(settings: AppSettings | None = None, gateway=None) -> FastAPI:
    settings = settings or load_config()
    prompt_builder = PromptBuilder("backend/prompts")
    response_parser = ResponseParser()
    llm_gateway = gateway or LLMGateway(settings)
    judge = Judge(llm_gateway, prompt_builder)
    web_search = WebSearch(settings.brave_search)
    orchestrator = SessionOrchestrator(
        gateway=llm_gateway,
        prompt_builder=prompt_builder,
        response_parser=response_parser,
        judge=judge,
        web_search=web_search,
        config=settings,
    )

    app = FastAPI(title="SciProof", version="0.1.0")
    app.state.settings = settings
    app.state.orchestrator = orchestrator

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.server.cors_origins or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(sessions.router)
    app.include_router(agents.router)
    app.include_router(metrics.router)

    @app.get("/api/health")
    async def health() -> dict[str, object]:
        return {
            "status": "ok",
            "providers": await llm_gateway.health_check(),
        }

    return app


app = create_app()


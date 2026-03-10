from __future__ import annotations

from fastapi import APIRouter, Request


router = APIRouter(prefix="/api/metrics", tags=["metrics"])


@router.get("/summary")
async def summary(request: Request) -> dict[str, object]:
    settings = request.app.state.settings
    session_store = request.app.state.session_store
    return {
        "app": "SciProof",
        "mode": "local_mvp",
        "server": {
            "host": settings.server.host,
            "port": settings.server.port,
        },
        "features": settings.features.model_dump(),
        "limits": settings.limits.model_dump(),
        "storage": {
            "backend": session_store.backend_name,
            "sessions_saved": await session_store.count_sessions(),
        },
        "providers": {
            provider_name: {
                "configured": bool(provider.api_key and provider.model),
                "model": provider.model,
            }
            for provider_name, provider in settings.providers.items()
        },
        "judge": (
            {
                "provider": settings.judge.provider,
                "temperature": settings.judge.temperature,
                "display_name": settings.judge.display_name,
            }
            if settings.judge
            else None
        ),
    }

from __future__ import annotations

from fastapi import APIRouter, Request


router = APIRouter(prefix="/api/agents", tags=["agents"])


@router.get("")
async def list_agents(request: Request) -> list[dict[str, object]]:
    return [
        {
            "id": agent.id,
            "provider": agent.provider,
            "display_name": agent.display_name,
            "temperature": agent.temperature,
            "persona": agent.persona,
        }
        for agent in request.app.state.settings.agents.values()
    ]


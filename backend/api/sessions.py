from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from backend.models.session import SessionConfig, SessionResult


router = APIRouter(prefix="/api/sessions", tags=["sessions"])


def get_orchestrator(request: Request):
    return request.app.state.orchestrator


@router.post("", response_model=SessionResult)
async def run_session(
    payload: SessionConfig,
    orchestrator=Depends(get_orchestrator),
) -> SessionResult:
    return await orchestrator.run_session(payload)


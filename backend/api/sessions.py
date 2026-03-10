from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from backend.models.session import SessionConfig, SessionResult, SessionSummary, StoredSessionRecord


router = APIRouter(prefix="/api/sessions", tags=["sessions"])


def get_orchestrator(request: Request):
    return request.app.state.orchestrator


def get_session_store(request: Request):
    return request.app.state.session_store


@router.post("", response_model=SessionResult)
async def run_session(
    payload: SessionConfig,
    orchestrator=Depends(get_orchestrator),
    session_store=Depends(get_session_store),
) -> SessionResult:
    result = await orchestrator.run_session(payload)
    await session_store.save_session(payload, result)
    return result


@router.get("", response_model=list[SessionSummary])
async def list_sessions(
    limit: int = Query(default=20, ge=1, le=100),
    session_store=Depends(get_session_store),
) -> list[SessionSummary]:
    return await session_store.list_sessions(limit=limit)


@router.get("/{session_id}", response_model=StoredSessionRecord)
async def get_session(
    session_id: str,
    session_store=Depends(get_session_store),
) -> StoredSessionRecord:
    record = await session_store.get_session(session_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return record

from __future__ import annotations

from fastapi import APIRouter


router = APIRouter(prefix="/api/metrics", tags=["metrics"])


@router.get("/summary")
async def summary() -> dict[str, object]:
    return {
        "storage": "disabled",
        "streaming": "disabled",
        "web_search": "optional",
        "mode": "local_mvp",
    }


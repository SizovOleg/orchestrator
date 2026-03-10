from __future__ import annotations

import asyncio
import json
from pathlib import Path

from backend.models.session import SessionConfig, SessionResult, SessionSummary, StoredSessionRecord


class FileSessionStore:
    def __init__(self, base_dir: str | Path = "data/sessions") -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    async def save_session(self, config: SessionConfig, result: SessionResult) -> None:
        record = StoredSessionRecord(
            saved_at=result.created_at,
            config=config,
            result=result,
        )
        await asyncio.to_thread(self._write_record, record)

    async def get_session(self, session_id: str) -> StoredSessionRecord | None:
        path = self._path_for_session(session_id)
        if not path.exists():
            return None
        return await asyncio.to_thread(self._read_record, path)

    async def list_sessions(self, limit: int = 20) -> list[SessionSummary]:
        return await asyncio.to_thread(self._list_sessions_sync, limit)

    async def count_sessions(self) -> int:
        return await asyncio.to_thread(lambda: len(list(self.base_dir.glob("*.json"))))

    @property
    def backend_name(self) -> str:
        return "local_file"

    def _path_for_session(self, session_id: str) -> Path:
        return self.base_dir / f"{session_id}.json"

    def _write_record(self, record: StoredSessionRecord) -> None:
        path = self._path_for_session(record.result.session_id)
        path.write_text(
            json.dumps(record.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _read_record(self, path: Path) -> StoredSessionRecord:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return StoredSessionRecord.model_validate(payload)

    def _list_sessions_sync(self, limit: int) -> list[SessionSummary]:
        records: list[SessionSummary] = []
        for path in sorted(self.base_dir.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True):
            try:
                record = self._read_record(path)
            except Exception:
                continue
            records.append(
                SessionSummary(
                    session_id=record.result.session_id,
                    created_at=record.result.created_at,
                    task_type=record.result.task_type,
                    status=record.result.status,
                    question=record.result.question,
                    total_tokens=record.result.total_tokens,
                    total_cost_usd=record.result.total_cost_usd,
                    rounds_count=len(record.result.rounds),
                    has_synthesis=record.result.synthesis is not None,
                )
            )
            if len(records) >= limit:
                break
        return records

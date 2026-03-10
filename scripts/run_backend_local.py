from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.config import load_config

import uvicorn


def normalize_secret(env_name: str, value: str) -> str:
    normalized = value.strip().strip('"').strip("'")
    if env_name == "OPENAI_API_KEY" and normalized.startswith("sk-sk-"):
        return normalized[3:]
    return normalized


def load_local_secrets() -> None:
    secrets_file = ROOT / "secrets.txt"
    if not secrets_file.exists():
        return

    mapping = {
        "OpenAI key:": "OPENAI_API_KEY",
        "Claude key:": "ANTHROPIC_API_KEY",
        "Brave key:": "BRAVE_API_KEY",
    }

    for line in secrets_file.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        for prefix, env_name in mapping.items():
            if stripped.startswith(prefix) and not os.getenv(env_name):
                os.environ[env_name] = normalize_secret(
                    env_name,
                    stripped.removeprefix(prefix),
                )


if __name__ == "__main__":
    load_local_secrets()
    settings = load_config()
    uvicorn.run(
        "backend.main:app",
        host=settings.server.host,
        port=settings.server.port,
        reload=False,
    )

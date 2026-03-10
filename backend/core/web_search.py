from __future__ import annotations

from urllib.parse import quote_plus

import httpx

from backend.config import BraveSearchSettings


class WebSearch:
    def __init__(self, settings: BraveSearchSettings) -> None:
        self.settings = settings

    async def search(self, query: str) -> str:
        query = query.strip()
        if not query or not self.settings.api_key:
            return ""

        url = f"https://api.search.brave.com/res/v1/web/search?q={quote_plus(query)}&count={self.settings.max_results_per_query}"
        headers = {
            "Accept": "application/json",
            "X-Subscription-Token": self.settings.api_key,
        }
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            payload = response.json()

        results = payload.get("web", {}).get("results", [])
        lines: list[str] = []
        for item in results:
            title = item.get("title") or ""
            description = item.get("description") or ""
            link = item.get("url") or ""
            lines.append(f"- {title}: {description} ({link})")
        return "\n".join(lines)


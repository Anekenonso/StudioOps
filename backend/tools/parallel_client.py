import os
from typing import List, Dict, Any, Optional
import httpx


class ParallelClient:
    """Configurable REST adapter for Parallel Search.

    This implementation uses a configurable `PARALLEL_BASE_URL` and
    `PARALLEL_API_KEY`. It assumes a POST ` /search` endpoint that
    accepts JSON {"q": "...", "limit": N}. Adjust the endpoint
    and headers to match the official Parallel API contract when
    available.
    """

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key or os.getenv("PARALLEL_API_KEY")
        self.base_url = base_url or os.getenv("PARALLEL_BASE_URL")
        if not self.api_key:
            raise RuntimeError("PARALLEL_API_KEY not set")
        if not self.base_url:
            raise RuntimeError("PARALLEL_BASE_URL not set")

    async def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Run a search query and return a list of normalized evidence dicts.

        Returned item shape:
        {
            "title": str,
            "url": str,
            "source": str,
            "snippet": str,
            "relevance": float,
            "raw": {...}
        }
        """
        url = f"{self.base_url.rstrip('/')}/search"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        payload = {"q": query, "limit": limit}

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.post(url, json=payload, headers=headers)
            except httpx.RequestError as exc:
                raise RuntimeError(f"Parallel request failed: {exc}") from exc

        if resp.status_code >= 400:
            raise RuntimeError(f"Parallel API error: {resp.status_code} {resp.text}")

        data = resp.json()

        # Normalization: attempt to extract a list of results from common keys.
        results = data.get("results") or data.get("items") or data.get("data") or []

        normalized: List[Dict[str, Any]] = []
        for item in results:
            title = item.get("title") or item.get("headline") or item.get("name") or ""
            urlv = item.get("url") or item.get("link") or item.get("canonical_url") or ""
            snippet = item.get("snippet") or item.get("excerpt") or item.get("summary") or ""
            source = item.get("source") or item.get("publisher") or ""
            relevance = float(item.get("score") or item.get("relevance") or 0.0)

            normalized.append({
                "title": title,
                "url": urlv,
                "source": source,
                "snippet": snippet,
                "relevance": relevance,
                "raw": item,
            })

        return normalized

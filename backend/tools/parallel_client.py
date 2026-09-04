import os
from typing import List, Dict, Any, Optional
import httpx
import asyncio
import time
from urllib.parse import urlparse, urlunparse


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

        # Retry/backoff parameters
        self._max_retries = 3
        self._backoff_base = 0.5

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
        endpoints = ["/search", "/v1/search", "/api/search"]
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        payload = {"q": query, "limit": limit}

        # Try multiple endpoints (legacy and v1) with retries/backoff
        resp = None
        last_exc = None
        data = None
        for ep in endpoints:
            url = f"{self.base_url.rstrip('/')}{ep}"
            for attempt in range(1, self._max_retries + 1):
                try:
                    async with httpx.AsyncClient(timeout=30.0) as client:
                        resp = await client.post(url, json=payload, headers=headers)
                    if resp.status_code < 500:
                        break
                    last_exc = RuntimeError(f"Parallel API server error: {resp.status_code}")
                except httpx.RequestError as exc:
                    last_exc = exc

                # backoff
                await asyncio.sleep(self._backoff_base * (2 ** (attempt - 1)))

            if resp is None:
                continue

            # If the API returns a 422 indicating a different schema (e.g. v1 expects
            # `search_queries`), attempt a fallback request using the v1 payload shape.
            if resp.status_code == 422 and resp.text and "search_queries" in resp.text:
                # v1 expects a list of query strings under `search_queries`.
                v1_payload = {"search_queries": [query]}
                async with httpx.AsyncClient(timeout=30.0) as client:
                    v1_resp = await client.post(url, json=v1_payload, headers=headers)
                if v1_resp.status_code >= 400:
                    last_exc = RuntimeError(f"Parallel API error (v1 fallback): {v1_resp.status_code} {v1_resp.text}")
                    resp = v1_resp
                    continue
                data = v1_resp.json()
                break

            if resp.status_code >= 400:
                last_exc = RuntimeError(f"Parallel API error: {resp.status_code} {resp.text}")
                # try next endpoint
                continue

            data = resp.json()
            break

        if data is None:
            raise RuntimeError(f"Parallel request failed: {last_exc}")

        if resp is None:
            raise RuntimeError(f"Parallel request failed: {last_exc}")

        # Normalization: attempt to extract a list of results from common keys.
        results = data.get("results") or data.get("items") or data.get("data") or []

        # Normalize and deduplicate by canonical URL
        normalized: List[Dict[str, Any]] = []
        seen_urls = set()

        def canonicalize(u: str) -> str:
            try:
                p = urlparse(u)
                # drop fragment and default ports
                netloc = p.hostname or ""
                if p.port:
                    netloc += f":{p.port}"
                path = p.path or "/"
                return urlunparse((p.scheme or "https", netloc, path.rstrip('/'), '', '', ''))
            except Exception:
                return u

        for item in results:
            title = item.get("title") or item.get("headline") or item.get("name") or ""
            urlv = item.get("url") or item.get("link") or item.get("canonical_url") or ""
            if not urlv:
                # skip items without a URL
                continue
            urlc = canonicalize(urlv)
            if urlc in seen_urls:
                continue
            seen_urls.add(urlc)
            snippet = item.get("snippet") or item.get("excerpt") or item.get("summary") or ""
            source = item.get("source") or item.get("publisher") or ""
            relevance = float(item.get("score") or item.get("relevance") or 0.0)

            normalized.append({
                "title": title,
                "url": urlc,
                "source": source,
                "snippet": snippet,
                "relevance": relevance,
                "raw": item,
            })

        return normalized

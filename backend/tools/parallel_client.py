"""Parallel Search API adapter.

Implements the current official Parallel Search contract:

    POST {PARALLEL_BASE_URL}/v1beta/search
    Header: x-api-key: <PARALLEL_API_KEY>
    Body:   {
              "objective": "natural-language research objective",
              "search_queries": ["query", ...],
              "max_results": int,
              "max_chars_per_result": int
            }
    Response: {"search_id": "...", "results": [{"url", "title", "publish_date", "excerpts": [...]}]}

Responsibilities (per build spec): authenticate securely, submit searches,
handle errors/timeouts/rate limits, normalize results, and return structured
evidence. This adapter never fabricates results — a failed search raises
`ParallelSearchError` and the caller records the failure.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse, urlunparse

import httpx

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://api.parallel.ai"
SEARCH_PATH = "/v1beta/search"

# Query params that are dropped from URLs when canonicalizing. Parallel appends
# its own attribution params, which would otherwise defeat deduplication.
_TRACKING_PREFIXES = ("utm_", "ref_")
_TRACKING_KEYS = {"ref", "source", "fbclid", "gclid", "mc_cid", "mc_eid"}


class ParallelSearchError(RuntimeError):
    """Raised when a Parallel search cannot be completed."""


def canonicalize_url(raw_url: str) -> str:
    """Return a canonical form of `raw_url` for deduplication.

    Drops fragments and tracking query params, lowercases the host, strips a
    trailing slash, and removes default ports. Meaningful query params are
    preserved because they often identify distinct pages (e.g. IMDb searches).
    """
    try:
        parsed = urlparse(raw_url.strip())
    except Exception:
        return raw_url.strip()

    if not parsed.netloc and not parsed.path:
        return raw_url.strip()

    host = (parsed.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    netloc = host
    if parsed.port and parsed.port not in (80, 443):
        netloc = f"{host}:{parsed.port}"

    kept_params = []
    if parsed.query:
        for pair in parsed.query.split("&"):
            if not pair:
                continue
            key = pair.split("=", 1)[0].lower()
            if key in _TRACKING_KEYS or key.startswith(_TRACKING_PREFIXES):
                continue
            kept_params.append(pair)

    path = parsed.path or "/"
    if len(path) > 1:
        path = path.rstrip("/")

    scheme = parsed.scheme or "https"
    if scheme == "http":
        # Treat http/https variants of the same page as one source.
        scheme = "https"

    return urlunparse((scheme, netloc, path, "", "&".join(kept_params), ""))


def _publisher_from_url(url: str) -> str:
    try:
        host = (urlparse(url).hostname or "").lower()
    except Exception:
        return ""
    return host[4:] if host.startswith("www.") else host


class ParallelClient:
    """Async adapter for the Parallel Search API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 60.0,
        max_retries: int = 3,
    ) -> None:
        self.api_key = api_key or os.getenv("PARALLEL_API_KEY")
        self.base_url = (base_url or os.getenv("PARALLEL_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
        if not self.api_key:
            raise ParallelSearchError(
                "PARALLEL_API_KEY is not set. Add it to your .env or runtime secrets."
            )

        self.timeout = timeout
        self._max_retries = max_retries
        self._backoff_base = 0.75

    @property
    def search_url(self) -> str:
        return f"{self.base_url}{SEARCH_PATH}"

    def _headers(self) -> Dict[str, str]:
        return {
            "x-api-key": self.api_key or "",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def search(
        self,
        query: str,
        objective: Optional[str] = None,
        max_results: int = 6,
        max_chars_per_result: int = 1500,
        client: Optional[httpx.AsyncClient] = None,
    ) -> List[Dict[str, Any]]:
        """Run one search and return normalized evidence dicts.

        `objective` gives Parallel the research intent behind the query, which
        materially improves result relevance. It defaults to the query itself.

        Each returned item:
            {"title", "url", "publisher", "published_date", "snippet",
             "excerpts": [...], "relevance", "raw"}

        Raises `ParallelSearchError` if the search cannot be completed.
        """
        payload: Dict[str, Any] = {
            "objective": (objective or query).strip(),
            "search_queries": [query.strip()],
            "max_results": max_results,
            "max_chars_per_result": max_chars_per_result,
        }

        started = time.perf_counter()
        data = await self._post_with_retries(payload, client=client)
        duration_ms = int((time.perf_counter() - started) * 1000)

        results = data.get("results") or []
        normalized = self.normalize_results(results)
        logger.info(
            "parallel.search query=%r duration_ms=%d raw=%d normalized=%d search_id=%s",
            query,
            duration_ms,
            len(results),
            len(normalized),
            data.get("search_id"),
        )
        return normalized

    async def _post_with_retries(
        self,
        payload: Dict[str, Any],
        client: Optional[httpx.AsyncClient] = None,
    ) -> Dict[str, Any]:
        """POST to the search endpoint with retries on transient failures."""
        owns_client = client is None
        http = client or httpx.AsyncClient(timeout=self.timeout)
        last_error: Optional[str] = None

        try:
            for attempt in range(1, self._max_retries + 1):
                try:
                    resp = await http.post(
                        self.search_url, json=payload, headers=self._headers()
                    )
                except httpx.TimeoutException as exc:
                    last_error = f"timeout after {self.timeout}s ({exc.__class__.__name__})"
                except httpx.RequestError as exc:
                    last_error = f"network error: {exc.__class__.__name__}: {exc}"
                else:
                    status = resp.status_code

                    if status == 200:
                        try:
                            return resp.json()
                        except ValueError as exc:
                            raise ParallelSearchError(
                                f"Parallel returned a malformed JSON body: {exc}"
                            ) from exc

                    if status in (401, 403):
                        # Never retry an auth failure, and never echo the key.
                        raise ParallelSearchError(
                            f"Parallel rejected the API key (HTTP {status}). "
                            "Verify PARALLEL_API_KEY."
                        )

                    if status == 429 or status >= 500:
                        retry_after = self._retry_after_seconds(resp)
                        last_error = f"HTTP {status}"
                        if attempt < self._max_retries:
                            await asyncio.sleep(retry_after or self._backoff(attempt))
                            continue
                    else:
                        # 4xx other than auth/rate-limit: request is wrong, don't retry.
                        raise ParallelSearchError(
                            f"Parallel rejected the request (HTTP {status}): "
                            f"{resp.text[:300]}"
                        )

                if attempt < self._max_retries:
                    await asyncio.sleep(self._backoff(attempt))

            raise ParallelSearchError(
                f"Parallel search failed after {self._max_retries} attempts: {last_error}"
            )
        finally:
            if owns_client:
                await http.aclose()

    def _backoff(self, attempt: int) -> float:
        return self._backoff_base * (2 ** (attempt - 1))

    @staticmethod
    def _retry_after_seconds(resp: httpx.Response) -> Optional[float]:
        value = resp.headers.get("retry-after")
        if not value:
            return None
        try:
            return min(float(value), 15.0)
        except ValueError:
            return None

    @staticmethod
    def normalize_results(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Normalize and deduplicate raw Parallel results.

        Parallel returns page text in an `excerpts` array; that text is the
        substance the synthesizer reasons over, so it is preserved in full and
        also joined into a `snippet` for display.
        """
        normalized: List[Dict[str, Any]] = []
        seen: set[str] = set()

        for item in results:
            if not isinstance(item, dict):
                continue

            url = (item.get("url") or "").strip()
            if not url:
                continue

            canonical = canonicalize_url(url)
            if canonical in seen:
                continue
            seen.add(canonical)

            excerpts = item.get("excerpts") or []
            if isinstance(excerpts, str):
                excerpts = [excerpts]
            excerpts = [e.strip() for e in excerpts if isinstance(e, str) and e.strip()]

            snippet = " ".join(excerpts)
            title = (item.get("title") or "").strip()
            if not title or title.startswith("http"):
                title = _publisher_from_url(canonical) or canonical

            normalized.append(
                {
                    "title": title,
                    "url": canonical,
                    "publisher": _publisher_from_url(canonical),
                    "published_date": item.get("publish_date") or None,
                    "snippet": snippet,
                    "excerpts": excerpts,
                    "relevance": 0.0,
                    "raw": item,
                }
            )

        return normalized

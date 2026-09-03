from __future__ import annotations

import os
from typing import Any

import httpx

from backend.models.research import SearchTask


class ParallelSearchClient:
    """Adapter for the Parallel Search API."""

    def __init__(self, api_key: str | None = None, base_url: str = "https://api.parallel.ai/v1/search"):
        self.api_key = api_key or os.getenv("PARALLEL_API_KEY")
        self.base_url = base_url

    async def search(self, query: str, *, category: str | None = None) -> list[dict[str, Any]]:
        if not self.api_key:
            raise ValueError("PARALLEL_API_KEY is not configured.")

        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
        }

        payload = {
            "query": query,
            "category": category,
        }

        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(self.base_url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

        items = data.get("results") or data.get("data") or []
        if not isinstance(items, list):
            return []
        return items

    async def search_many(self, tasks: list[SearchTask]) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for task in tasks:
            fetched = await self.search(task.query, category=task.category)
            for item in fetched:
                item["category"] = task.category
                item["question"] = task.question
                results.append(item)
        return results

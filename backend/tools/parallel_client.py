import os
from typing import List, Dict, Any
import httpx


class ParallelClient:
    """Minimal Parallel client stub for Phase 1.

    This is a placeholder. Implementations must follow the current
    official Parallel API and keep the API key server-side.
    """

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("PARALLEL_API_KEY")
        if not self.api_key:
            raise RuntimeError("PARALLEL_API_KEY not set")

    async def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Run a search query against Parallel and return normalized results.

        Phase 1: stubbed to an empty list. Replace with the official API
        call when available.
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            # TODO: implement using official Parallel API SDK/endpoint
            return []

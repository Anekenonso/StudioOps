"""Shared test fixtures.

External services are always mocked here. Nothing in this suite makes a real
network call; live integration checks live in `backend/tools/run_e2e_research.py`.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import pytest

from backend.integrations.gemini_client import GeminiStatus
from backend.models.brief import ProjectBrief


@pytest.fixture(autouse=True)
def isolated_env(monkeypatch, tmp_path):
    """Keep tests off real credentials and out of the repo's outputs dir."""
    for key in (
        "PARALLEL_API_KEY",
        "PARALLEL_BASE_URL",
        "GEMINI_API_KEY",
        "GOOGLE_API_KEY",
        "GOOGLE_CLOUD_PROJECT",
        "GOOGLE_GENAI_USE_VERTEXAI",
        "GOOGLE_APPLICATION_CREDENTIALS",
        "GOOGLE_SERVICE_ACCOUNT_JSON",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("PARALLEL_API_KEY", "test-key")

    report_dir = tmp_path / "reports"
    report_dir.mkdir()
    monkeypatch.setattr("backend.tools.report_store.REPORT_DIR", str(report_dir))
    return report_dir


@pytest.fixture
def brief() -> ProjectBrief:
    return ProjectBrief(
        title="Lagos After Dark",
        description="A contemporary Nigerian crime thriller series set in Lagos.",
        format="Series",
        genre="Crime Thriller",
        geography="Nigeria",
        target_audience="Young adults",
        research_questions=["What are comparable recent titles?"],
    )


def parallel_result(
    url: str,
    title: str = "Example article",
    excerpt: str = "",
    publish_date: Optional[str] = None,
) -> Dict[str, Any]:
    """A raw Parallel API result item."""
    return {
        "url": url,
        "title": title,
        "publish_date": publish_date,
        "excerpts": [excerpt or ("Nollywood crime thriller coverage. " * 8)],
    }


class FakeGemini:
    """Stand-in for GeminiClient with scripted JSON responses."""

    def __init__(
        self,
        responses: Optional[List[Dict[str, Any]]] = None,
        configured: bool = True,
        raise_error: Optional[Exception] = None,
    ) -> None:
        self._responses = list(responses or [])
        self._configured = configured
        self._raise = raise_error
        self.calls: List[Dict[str, Any]] = []
        self.status = GeminiStatus(
            configured=configured,
            mode="api_key" if configured else "unconfigured",
            model="gemini-2.5-flash",
            detail="test double",
        )

    @property
    def configured(self) -> bool:
        return self._configured

    async def generate_json(self, system_instruction: str, prompt: str, **kwargs: Any):
        self.calls.append({"system": system_instruction, "prompt": prompt, **kwargs})
        if self._raise is not None:
            raise self._raise
        if not self._responses:
            raise AssertionError("FakeGemini ran out of scripted responses")
        return self._responses.pop(0)


class FakeParallel:
    """Stand-in for ParallelClient returning normalized results per query."""

    def __init__(
        self,
        by_query: Optional[Dict[str, List[Dict[str, Any]]]] = None,
        default: Optional[List[Dict[str, Any]]] = None,
        errors: Optional[Dict[str, Exception]] = None,
        error_all: Optional[Exception] = None,
    ) -> None:
        self.by_query = by_query or {}
        self.default = default
        self.errors = errors or {}
        self.error_all = error_all
        self.timeout = 5.0
        self.queries: List[str] = []
        self.objectives: List[str] = []

    async def search(
        self,
        query: str,
        objective: Optional[str] = None,
        max_results: int = 6,
        max_chars_per_result: int = 1500,
        client: Any = None,
    ) -> List[Dict[str, Any]]:
        self.queries.append(query)
        self.objectives.append(objective or "")

        if self.error_all is not None:
            raise self.error_all
        for needle, exc in self.errors.items():
            if needle in query:
                raise exc

        from backend.tools.parallel_client import ParallelClient

        for needle, results in self.by_query.items():
            if needle in query:
                return ParallelClient.normalize_results(results)

        if self.default is not None:
            return ParallelClient.normalize_results(self.default)

        # Deterministic per-query results so dedup behaviour is testable.
        index = len(self.queries)
        return ParallelClient.normalize_results(
            [
                parallel_result(
                    f"https://variety.com/article-{index}",
                    f"Industry report {index}",
                    "Nigerian streaming commissions grew across the region. " * 6,
                ),
                parallel_result(
                    "https://deadline.com/shared-article",
                    "Shared coverage",
                    "Global streamers are touring Africa for local scripted drama. " * 6,
                ),
            ]
        )

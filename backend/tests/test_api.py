"""HTTP API: research endpoints, run status, SSE progress, error shaping."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

import backend.api.routes as routes
from backend.agent.workflow import ResearchFailure, run_studioops
from backend.main import app
from backend.services.run_store import store

from .conftest import FakeGemini, FakeParallel

BRIEF = {
    "title": "Lagos After Dark",
    "description": "A contemporary Nigerian crime thriller series set in Lagos.",
    "format": "Series",
    "genre": "Crime Thriller",
    "geography": "Nigeria",
    "target_audience": "Young adults",
}


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def mocked_run(monkeypatch):
    """Run the real workflow with mocked Gemini and Parallel."""

    async def fake_run(brief, on_progress=None, run_id=None, **_kwargs):
        return await run_studioops(
            brief,
            on_progress=on_progress,
            run_id=run_id,
            gemini=FakeGemini(configured=False),
            parallel=FakeParallel(),
        )

    monkeypatch.setattr(routes, "run_studioops", fake_run)


class TestConfigEndpoint:
    def test_reports_integration_readiness(self, client):
        body = client.get("/api/v1/config").json()

        assert body["parallel"]["configured"] is True
        assert body["gemini"]["configured"] is False
        assert body["gemini"]["mode"] == "unconfigured"
        assert body["gemini"]["detail"]

    def test_never_returns_key_material(self, client, monkeypatch):
        """API keys must never reach the browser."""
        monkeypatch.setenv("PARALLEL_API_KEY", "pk-live-secret")
        monkeypatch.setenv("GEMINI_API_KEY", "gm-live-secret")

        raw = client.get("/api/v1/config").text
        assert "pk-live-secret" not in raw
        assert "gm-live-secret" not in raw

    def test_flags_a_missing_parallel_key(self, client, monkeypatch):
        monkeypatch.delenv("PARALLEL_API_KEY", raising=False)
        body = client.get("/api/v1/config").json()

        assert body["parallel"]["configured"] is False
        assert "PARALLEL_API_KEY" in body["parallel"]["detail"]


class TestHealth:
    def test_health_is_ok(self, client):
        assert client.get("/health").json() == {"status": "ok"}


class TestSynchronousResearch:
    def test_returns_a_studio_brief(self, client, mocked_run):
        body = client.post("/api/v1/research", json=BRIEF).json()

        assert body["status"] in ("completed", "partial")
        assert body["run_id"]
        assert body["project"]["title"] == "Lagos After Dark"
        assert body["report"]["executive_summary"]
        assert body["report"]["sources"]
        assert body["research_metadata"]["unique_sources"] > 0

    def test_exposes_the_research_plan(self, client, mocked_run):
        body = client.post("/api/v1/research", json=BRIEF).json()
        plan = body["plan"]

        assert plan["tasks"]
        assert plan["generated_by"] in ("gemini", "fallback")
        assert all(task["query"] for task in plan["tasks"])

    def test_every_source_has_a_clickable_url(self, client, mocked_run):
        body = client.post("/api/v1/research", json=BRIEF).json()

        for source in body["report"]["sources"]:
            assert source["url"].startswith("https://")
            assert source["id"].startswith("S")

    def test_attaches_report_download_urls(self, client, mocked_run):
        body = client.post("/api/v1/research", json=BRIEF).json()

        assert body["report_url_json"].startswith("/reports/")
        assert body["report_url_md"].endswith(".md")

    def test_registers_the_run_for_later_retrieval(self, client, mocked_run):
        run_id = client.post("/api/v1/research", json=BRIEF).json()["run_id"]
        body = client.get(f"/api/v1/research/{run_id}").json()

        assert body["run_id"] == run_id
        assert body["status"] in ("completed", "partial")
        assert body["result"]["report"]
        assert body["event_count"] > 0

    def test_rejects_a_brief_with_no_title(self, client, mocked_run):
        response = client.post("/api/v1/research", json={"description": "d"})
        assert response.status_code == 422

    def test_accepts_a_minimal_brief(self, client, mocked_run):
        response = client.post(
            "/api/v1/research", json={"title": "T", "description": "A short film idea."}
        )
        assert response.status_code == 200


class TestErrorHandling:
    def test_research_failure_returns_502_with_a_safe_message(self, client, monkeypatch):
        async def boom(*_args, **_kwargs):
            raise ResearchFailure("Parallel returned HTTP 500 for key sk-abc123", stage="search")

        monkeypatch.setattr(routes, "run_studioops", boom)
        response = client.post("/api/v1/research", json=BRIEF)

        assert response.status_code == 502
        detail = response.json()["detail"]
        assert detail["stage"] == "search"
        assert detail["run_id"]
        # No internals, and certainly no credentials.
        assert "sk-abc123" not in response.text
        assert "HTTP 500" not in response.text

    def test_an_unexpected_error_returns_a_generic_500(self, client, monkeypatch):
        async def boom(*_args, **_kwargs):
            raise ValueError("Traceback: /app/backend/agent/workflow.py line 42")

        monkeypatch.setattr(routes, "run_studioops", boom)
        response = client.post("/api/v1/research", json=BRIEF)

        assert response.status_code == 500
        assert response.json()["detail"]["message"] == routes.GENERIC_ERROR
        assert "workflow.py" not in response.text

    def test_a_missing_parallel_key_yields_an_actionable_message(self, client, monkeypatch):
        async def boom(*_args, **_kwargs):
            raise ResearchFailure(
                "PARALLEL_API_KEY is not set. Add it to your .env.", stage="search"
            )

        monkeypatch.setattr(routes, "run_studioops", boom)
        message = client.post("/api/v1/research", json=BRIEF).json()["detail"]["message"]

        assert "not configured" in message

    def test_a_plan_failure_suggests_more_detail(self, client, monkeypatch):
        async def boom(*_args, **_kwargs):
            raise ResearchFailure("no tasks", stage="plan")

        monkeypatch.setattr(routes, "run_studioops", boom)
        message = client.post("/api/v1/research", json=BRIEF).json()["detail"]["message"]

        assert "more detail" in message

    def test_a_failed_run_is_still_queryable(self, client, monkeypatch):
        async def boom(*_args, **_kwargs):
            raise ResearchFailure("nope", stage="search")

        monkeypatch.setattr(routes, "run_studioops", boom)
        run_id = client.post("/api/v1/research", json=BRIEF).json()["detail"]["run_id"]
        body = client.get(f"/api/v1/research/{run_id}").json()

        assert body["status"] == "failed"
        assert body["error_stage"] == "search"

    def test_unknown_run_returns_404(self, client):
        assert client.get("/api/v1/research/does-not-exist").status_code == 404

    def test_unknown_run_events_returns_404(self, client):
        assert client.get("/api/v1/research/does-not-exist/events").status_code == 404


class TestAsyncResearch:
    def test_returns_a_run_id_immediately(self, client, mocked_run):
        body = client.post("/api/v1/research/async", json=BRIEF).json()

        assert body["run_id"]
        assert body["status"] == "running"

    def test_the_run_finishes_and_exposes_its_result(self, client, mocked_run):
        run_id = client.post("/api/v1/research/async", json=BRIEF).json()["run_id"]

        # Draining the event stream blocks until the run signals completion.
        _consume_events(client, run_id)

        body = client.get(f"/api/v1/research/{run_id}").json()
        assert body["status"] in ("completed", "partial")
        assert body["result"]["report"]["sources"]

    def test_a_failed_async_run_records_a_safe_message(self, client, monkeypatch):
        async def boom(*_args, **_kwargs):
            raise ResearchFailure("internal detail", stage="search")

        monkeypatch.setattr(routes, "run_studioops", boom)
        run_id = client.post("/api/v1/research/async", json=BRIEF).json()["run_id"]
        _consume_events(client, run_id)

        body = client.get(f"/api/v1/research/{run_id}").json()
        assert body["status"] == "failed"
        assert "internal detail" not in json.dumps(body)


class TestServerSentEvents:
    def test_streams_real_progress_for_a_finished_run(self, client, mocked_run):
        """Progress must come from the backend, not a frontend timer."""
        run_id = client.post("/api/v1/research", json=BRIEF).json()["run_id"]
        events, final = _consume_events(client, run_id)

        stages = [e["stage"] for e in events]
        assert stages[0] == "intake"
        assert "plan" in stages
        assert "search" in stages
        assert "synthesize" in stages
        assert final["status"] in ("completed", "partial")

    def test_declares_the_sse_content_type_and_no_buffering(self, client, mocked_run):
        run_id = client.post("/api/v1/research", json=BRIEF).json()["run_id"]

        with client.stream("GET", f"/api/v1/research/{run_id}/events") as response:
            assert response.headers["content-type"].startswith("text/event-stream")
            assert "no-cache" in response.headers["cache-control"]
            assert response.headers["x-accel-buffering"] == "no"
            response.read()

    def test_events_name_their_type(self, client, mocked_run):
        run_id = client.post("/api/v1/research", json=BRIEF).json()["run_id"]

        with client.stream("GET", f"/api/v1/research/{run_id}/events") as response:
            body = "".join(response.iter_text())

        assert "event: progress" in body
        assert "event: complete" in body

    def test_search_progress_names_each_query(self, client, mocked_run):
        run_id = client.post("/api/v1/research", json=BRIEF).json()["run_id"]
        events, _ = _consume_events(client, run_id)
        search_events = [e for e in events if e["stage"] == "search" and e.get("query")]

        assert search_events
        assert all(e["message"].startswith("Searching") for e in search_events)

    def test_completion_event_reports_a_failure(self, client, monkeypatch):
        async def boom(*_args, **_kwargs):
            raise ResearchFailure("nope", stage="search")

        monkeypatch.setattr(routes, "run_studioops", boom)
        run_id = client.post("/api/v1/research", json=BRIEF).json()["detail"]["run_id"]
        _, final = _consume_events(client, run_id)

        assert final["status"] == "failed"
        assert final["error"]

    def test_a_second_subscriber_replays_the_whole_run(self, client, mocked_run):
        run_id = client.post("/api/v1/research", json=BRIEF).json()["run_id"]
        first, _ = _consume_events(client, run_id)
        second, _ = _consume_events(client, run_id)

        assert [e["stage"] for e in first] == [e["stage"] for e in second]


def _consume_events(client: TestClient, run_id: str):
    """Read an SSE stream to completion, returning (progress_events, final)."""
    progress: list[dict] = []
    final: dict = {}

    with client.stream("GET", f"/api/v1/research/{run_id}/events") as response:
        assert response.status_code == 200
        event_name = None
        for line in response.iter_lines():
            line = line.rstrip("\r")
            if line.startswith("event: "):
                event_name = line[len("event: ") :]
            elif line.startswith("data: "):
                payload = json.loads(line[len("data: ") :])
                if event_name == "complete":
                    final = payload
                    break
                progress.append(payload)

    return progress, final

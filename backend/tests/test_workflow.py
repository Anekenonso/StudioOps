"""Workflow orchestration: stage sequence, real progress events, degradation."""

from __future__ import annotations

import pytest

from backend.agent.workflow import (
    STAGES,
    Emitter,
    ResearchFailure,
    _objective_context,
    run_studioops,
)
from backend.models.brief import ProjectBrief
from backend.tools.parallel_client import ParallelSearchError

from .conftest import FakeGemini, FakeParallel, parallel_result


async def run(brief, **kwargs):
    """Run the workflow with mocked integrations, collecting progress events."""
    events: list[dict] = []

    async def on_progress(event):
        events.append(event)

    kwargs.setdefault("gemini", FakeGemini(configured=False))
    kwargs.setdefault("parallel", FakeParallel())
    response = await run_studioops(brief, on_progress=on_progress, **kwargs)
    return response, events


class TestHappyPath:
    async def test_produces_a_report_with_sources(self, brief):
        response, _ = await run(brief)

        assert response.run_id
        assert response.report.sources
        assert response.research_metadata.unique_sources > 0
        assert response.project.title == "Lagos After Dark"

    async def test_walks_every_pipeline_stage_in_order(self, brief):
        """The spec fixes the pipeline: intake -> plan -> search -> collect ->
        synthesize -> report. Progress must reflect that real sequence."""
        _, events = await run(brief)
        seen = []
        for event in events:
            if event["stage"] not in seen:
                seen.append(event["stage"])

        assert seen == list(STAGES)

    async def test_events_carry_the_run_id_and_a_timestamp(self, brief):
        response, events = await run(brief)
        for event in events:
            assert event["run_id"] == response.run_id
            assert event["at"]
            assert event["status"] in ("active", "done", "error", "info")
            assert event["message"]

    async def test_uses_an_explicit_run_id(self, brief):
        response, events = await run(brief, run_id="fixed123")
        assert response.run_id == "fixed123"
        assert events[0]["run_id"] == "fixed123"

    async def test_plan_event_exposes_the_planned_tasks(self, brief):
        """The UI renders the real plan, not a canned checklist."""
        _, events = await run(brief)
        plan_done = next(e for e in events if e["stage"] == "plan" and e["status"] == "done")

        assert plan_done["tasks"]
        assert all(t["query"] and t["label"] for t in plan_done["tasks"])
        assert plan_done["planner"] == "fallback"

    async def test_emits_one_event_per_search_as_it_starts(self, brief):
        parallel = FakeParallel()
        _, events = await run(brief, parallel=parallel)
        started = [
            e
            for e in events
            if e["stage"] == "search" and e["status"] == "info" and "result_count" not in e
        ]
        assert len(started) == len(parallel.queries)

    async def test_search_completion_events_report_result_counts(self, brief):
        _, events = await run(brief)
        finished = [e for e in events if e.get("result_count") is not None]
        assert finished
        assert all(e["result_count"] >= 0 for e in finished)

    async def test_progress_metrics_match_the_metadata(self, brief):
        response, events = await run(brief)
        search_done = next(
            e for e in events if e["stage"] == "search" and e["status"] == "done"
        )
        meta = response.research_metadata

        assert search_done["queries_run"] == meta.queries_run
        assert search_done["results"] == meta.sources_reviewed

    async def test_passes_the_brief_as_search_objective(self, brief):
        """Parallel uses the objective to judge relevance, so it must describe
        the actual project, not just echo the query."""
        parallel = FakeParallel()
        await run(brief, parallel=parallel)

        assert all("Lagos After Dark" in o for o in parallel.objectives)
        assert all("Crime Thriller" in o for o in parallel.objectives)

    async def test_report_stage_reports_the_final_status(self, brief):
        response, events = await run(brief)
        final = next(e for e in events if e["stage"] == "report")

        assert final["run_status"] == response.status
        assert final["sources"] == len(response.report.sources)

    async def test_records_the_research_trail_per_task(self, brief):
        response, _ = await run(brief)
        tasks = response.plan["tasks"]

        assert tasks
        for task in tasks:
            assert task["query"]
            assert task["duration_ms"] >= 0
            assert "evidence_ids" in task


class TestEvidenceWiring:
    async def test_deduplicates_a_source_returned_by_every_query(self, brief):
        """FakeParallel returns one shared URL for every query."""
        response, _ = await run(brief)
        urls = [s.url for s in response.report.sources]

        assert len(urls) == len(set(urls))
        assert response.research_metadata.sources_reviewed > response.research_metadata.unique_sources

    async def test_task_evidence_ids_resolve_to_real_sources(self, brief):
        response, _ = await run(brief)
        valid = {s.id for s in response.report.sources}

        for task in response.plan["tasks"]:
            assert set(task["evidence_ids"]) <= valid


class TestGeminiUnconfigured:
    async def test_labels_the_run_as_partial_and_says_why(self, brief):
        """Templated output must never be presented as model analysis."""
        response, events = await run(brief, gemini=FakeGemini(configured=False))

        assert response.status == "partial"
        assert response.report.generated_by == "fallback"
        assert response.research_metadata.synthesizer == "fallback"
        assert any("Gemini synthesis unavailable" in w for w in response.research_metadata.warnings)
        assert any(
            e["stage"] == "synthesize" and e["status"] == "info" for e in events
        )

    async def test_completes_when_gemini_synthesizes(self, brief):
        from .test_synthesizer import model_report

        plan = {
            "reasoning": "r",
            "tasks": [
                {"category": "market", "query": "nigeria tv market", "priority": 1},
                {"category": "comparables", "query": "nigerian crime series", "priority": 2},
            ],
        }
        gemini = FakeGemini([plan, model_report(comparable_titles=[], market_signals=[])])
        response, events = await run(brief, gemini=gemini)

        assert response.status == "completed"
        assert response.report.generated_by == "gemini"
        assert response.research_metadata.planner == "gemini"
        assert response.research_metadata.synthesis_duration_ms >= 0
        assert any(e["message"] == "Gemini synthesis complete" for e in events)


class TestPartialFailure:
    async def test_one_failed_search_degrades_rather_than_aborts(self, brief):
        parallel = FakeParallel(errors={"market": ParallelSearchError("HTTP 500")})
        response, events = await run(brief, parallel=parallel)

        assert response.status == "partial"
        assert response.research_metadata.queries_failed >= 1
        assert response.report.sources
        assert any("Search failed" in w for w in response.research_metadata.warnings)

    async def test_failed_task_is_recorded_in_the_trail(self, brief):
        parallel = FakeParallel(errors={"market": ParallelSearchError("HTTP 500")})
        response, _ = await run(brief, parallel=parallel)
        failed = [t for t in response.plan["tasks"] if t["error"]]

        assert failed
        assert failed[0]["result_count"] == 0
        assert "HTTP 500" in failed[0]["error"]

    async def test_an_unexpected_search_error_is_contained(self, brief):
        parallel = FakeParallel(errors={"market": ValueError("boom")})
        response, _ = await run(brief, parallel=parallel)

        assert response.status == "partial"
        assert any("ValueError" in w for w in response.research_metadata.warnings)


class TestHardFailure:
    async def test_all_searches_failing_raises(self, brief):
        parallel = FakeParallel(error_all=ParallelSearchError("network down"))
        with pytest.raises(ResearchFailure) as excinfo:
            await run(brief, parallel=parallel)

        assert excinfo.value.stage == "search"
        assert "network down" in str(excinfo.value)

    async def test_an_empty_plan_raises_at_the_plan_stage(self, brief, monkeypatch):
        from backend.models.research import ResearchPlan

        async def empty_plan(*_args, **_kwargs):
            return ResearchPlan(tasks=[], generated_by="fallback")

        monkeypatch.setattr("backend.agent.workflow.create_research_plan", empty_plan)

        with pytest.raises(ResearchFailure) as excinfo:
            await run(brief)
        assert excinfo.value.stage == "plan"

    async def test_a_missing_parallel_key_fails_at_the_search_stage(self, brief, monkeypatch):
        monkeypatch.delenv("PARALLEL_API_KEY", raising=False)
        with pytest.raises(ResearchFailure) as excinfo:
            await run_studioops(brief, gemini=FakeGemini(configured=False))

        assert excinfo.value.stage == "search"
        assert "PARALLEL_API_KEY" in str(excinfo.value)


class TestNoUsableEvidence:
    async def test_searches_returning_only_empty_pages_yield_an_honest_report(self, brief):
        """Parallel can return hits whose page text is empty; those cannot be
        cited, so the report must say so rather than invent findings."""
        parallel = FakeParallel(
            default=[{"url": "https://example.com/a", "title": "A", "excerpts": []}]
        )
        response, events = await run(brief, parallel=parallel)

        assert response.report.sources == []
        assert response.research_metadata.unique_sources == 0
        assert response.report.comparable_titles == []
        assert any(
            e["stage"] == "synthesize" and e["status"] == "error" for e in events
        )


class TestEmitter:
    async def test_extra_fields_cannot_shadow_the_event_shape(self):
        """A caller passing status=... must not corrupt the event contract."""
        emitter = Emitter(None, "run1")
        await emitter.emit("report", "done", "ready", status="ignored", run_id="ignored")
        event = emitter.events[0]

        assert event["status"] == "done"
        assert event["run_id"] == "run1"

    async def test_a_failing_listener_does_not_kill_the_run(self, brief):
        async def broken(_event):
            raise RuntimeError("listener exploded")

        response = await run_studioops(
            brief,
            on_progress=broken,
            gemini=FakeGemini(configured=False),
            parallel=FakeParallel(),
        )
        assert response.report.sources

    async def test_works_without_a_listener(self, brief):
        response = await run_studioops(
            brief, gemini=FakeGemini(configured=False), parallel=FakeParallel()
        )
        assert response.run_id


class TestObjectiveContext:
    def test_summarizes_the_brief(self, brief):
        context = _objective_context(brief)
        assert "Lagos After Dark" in context
        assert "Crime Thriller" in context
        assert "Nigeria" in context

    def test_truncates_a_long_description(self):
        brief = ProjectBrief(title="T", description="x" * 5000)
        assert len(_objective_context(brief)) < 400

    def test_falls_back_to_the_title(self):
        assert _objective_context(ProjectBrief(title="Solo", description="")) == "Solo"

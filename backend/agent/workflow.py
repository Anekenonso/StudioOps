"""StudioOps agent workflow.

Fixed pipeline, per the technical spec:

    INTAKE -> PLAN -> SEARCH -> COLLECT -> VALIDATE -> SYNTHESIZE -> REPORT

Progress is emitted from the real execution path — each event corresponds to
work that has actually happened, so the UI timeline is not a simulation.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple

import httpx

from backend.agent.planner import create_research_plan
from backend.agent.synthesizer import build_empty_report, synthesize_report
from backend.integrations.gemini_client import GeminiClient
from backend.models.brief import ProjectBrief
from backend.models.report import ProjectSummary, ResearchResponse, StudioOpsReport
from backend.models.research import (
    Evidence,
    ResearchContext,
    ResearchMetadata,
    ResearchPlan,
    SearchTask,
    TaskResult,
)
from backend.services.evidence import process_evidence
from backend.tools.parallel_client import ParallelClient, ParallelSearchError

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[Dict[str, Any]], Awaitable[None]]

# Concurrent Parallel searches. Bounded to stay well inside rate limits and the
# hackathon search credit.
MAX_CONCURRENT_SEARCHES = 4

STAGES = ("intake", "plan", "search", "collect", "synthesize", "report")


class ResearchFailure(RuntimeError):
    """Raised when the run cannot produce a report at all."""

    def __init__(self, message: str, stage: str = "search") -> None:
        super().__init__(message)
        self.stage = stage


class Emitter:
    """Serializes progress events to an optional async callback."""

    def __init__(self, callback: Optional[ProgressCallback], run_id: str) -> None:
        self._callback = callback
        self.run_id = run_id
        self.events: List[Dict[str, Any]] = []

    async def emit(self, stage: str, status: str, message: str, /, **extra: Any) -> None:
        # Positional-only, so an extra field named `stage`/`status`/`message`
        # lands in **extra instead of colliding with the parameter and raising
        # TypeError mid-run. Reserved keys then win when the event is built.
        event = {
            **extra,
            "run_id": self.run_id,
            "stage": stage,
            "status": status,  # active | done | error | info
            "message": message,
            "at": datetime.now(timezone.utc).isoformat(),
        }
        self.events.append(event)
        logger.info("progress stage=%s status=%s %s", stage, status, message)
        if self._callback is not None:
            try:
                await self._callback(event)
            except Exception as exc:  # pragma: no cover - a dead listener must not kill a run
                logger.debug("progress.callback_failed: %s", exc)


async def run_studioops(
    brief: ProjectBrief,
    on_progress: Optional[ProgressCallback] = None,
    run_id: Optional[str] = None,
    gemini: Optional[GeminiClient] = None,
    parallel: Optional[ParallelClient] = None,
) -> ResearchResponse:
    """Execute the full research workflow and return the Studio Brief."""
    run_id = run_id or uuid.uuid4().hex[:12]
    started = time.perf_counter()
    emitter = Emitter(on_progress, run_id)

    # --- INTAKE -------------------------------------------------------------
    await emitter.emit(
        "intake", "done", f"Brief analyzed: {brief.title}", title=brief.title
    )

    gemini_client = gemini or GeminiClient()
    if not gemini_client.configured:
        logger.warning("gemini.unconfigured: %s", gemini_client.status.detail)

    # --- PLAN ---------------------------------------------------------------
    await emitter.emit("plan", "active", "Creating research plan")
    plan = await create_research_plan(brief, gemini=gemini_client)

    if not plan.tasks:
        raise ResearchFailure("The research planner produced no tasks.", stage="plan")

    await emitter.emit(
        "plan",
        "done",
        f"Research plan created: {len(plan.tasks)} tasks",
        planner=plan.generated_by,
        reasoning=plan.reasoning,
        tasks=[
            {
                "id": t.id,
                "category": t.category,
                "question": t.question,
                "query": t.query,
                "label": t.label(),
            }
            for t in plan.tasks
        ],
    )

    # --- SEARCH -------------------------------------------------------------
    await emitter.emit(
        "search", "active", f"Searching the live web with Parallel ({len(plan.tasks)} queries)"
    )
    search_started = time.perf_counter()

    try:
        client = parallel or ParallelClient()
    except ParallelSearchError as exc:
        raise ResearchFailure(str(exc), stage="search") from exc

    task_results, raw_by_task = await _execute_searches(brief, plan, client, emitter)
    search_duration_ms = int((time.perf_counter() - search_started) * 1000)

    successful = [t for t in task_results if t.ok]
    failed = [t for t in task_results if not t.ok]

    if not successful:
        detail = failed[0].error if failed else "unknown error"
        raise ResearchFailure(
            f"All {len(task_results)} web searches failed. Last error: {detail}",
            stage="search",
        )

    total_raw = sum(t.result_count for t in task_results)
    await emitter.emit(
        "search",
        "done",
        f"Parallel search completed: {total_raw} results from {len(successful)} queries",
        queries_run=len(successful),
        queries_failed=len(failed),
        results=total_raw,
    )

    # --- COLLECT / VALIDATE -------------------------------------------------
    await emitter.emit("collect", "active", "Normalizing and deduplicating evidence")

    evidence, task_evidence_ids = process_evidence(
        [(result.task, raw_by_task.get(result.task.id, [])) for result in task_results]
    )
    for result in task_results:
        result.evidence_ids = task_evidence_ids.get(result.task.id, [])

    metadata = ResearchMetadata(
        queries_run=len(successful),
        queries_failed=len(failed),
        sources_reviewed=total_raw,
        unique_sources=len(evidence),
        search_duration_ms=search_duration_ms,
        planner=plan.generated_by,
        warnings=[
            f"Search failed for '{t.task.query}': {t.error}" for t in failed
        ],
    )

    context = ResearchContext(
        plan=plan, evidence=evidence, task_results=task_results, metadata=metadata
    )

    await emitter.emit(
        "collect",
        "done",
        f"Evidence processed: {len(evidence)} unique sources",
        unique_sources=len(evidence),
        duplicates_removed=max(0, total_raw - len(evidence)),
    )

    # --- SYNTHESIZE ---------------------------------------------------------
    if not evidence:
        report = build_empty_report(brief, context)
        await emitter.emit(
            "synthesize", "error", "No usable evidence was retrieved to analyze"
        )
    else:
        await emitter.emit(
            "synthesize",
            "active",
            f"Analyzing {len(evidence)} sources with Gemini",
            model=gemini_client.status.model if gemini_client.configured else None,
        )
        synth_started = time.perf_counter()
        report = await synthesize_report(brief, context, gemini=gemini_client)
        metadata.synthesis_duration_ms = int((time.perf_counter() - synth_started) * 1000)
        metadata.synthesizer = report.generated_by

        if report.generated_by == "gemini":
            await emitter.emit(
                "synthesize",
                "done",
                "Gemini synthesis complete",
                comparables=len(report.comparable_titles),
                signals=len(report.market_signals),
                risks=len(report.risks),
            )
        else:
            metadata.warnings.append(
                "Gemini synthesis unavailable — report contains retrieved evidence "
                f"without analysis. ({gemini_client.status.detail})"
            )
            await emitter.emit(
                "synthesize",
                "info",
                "Gemini synthesis unavailable — returning retrieved evidence without analysis",
                reason=gemini_client.status.detail,
            )

    # --- REPORT -------------------------------------------------------------
    metadata.total_duration_ms = int((time.perf_counter() - started) * 1000)
    status = "partial" if (failed or report.generated_by == "fallback") else "completed"

    response = ResearchResponse(
        status=status,
        run_id=run_id,
        project=ProjectSummary(
            title=brief.title,
            format=brief.format,
            genre=brief.genre,
            geography=brief.geography,
            target_audience=brief.target_audience,
            researched_at=datetime.now(timezone.utc).isoformat(),
        ),
        plan={
            "reasoning": plan.reasoning,
            "generated_by": plan.generated_by,
            "tasks": [
                {
                    "id": t.task.id,
                    "category": t.task.category,
                    "question": t.task.question,
                    "query": t.task.query,
                    "label": t.task.label(),
                    "result_count": t.result_count,
                    "duration_ms": t.duration_ms,
                    "evidence_ids": t.evidence_ids,
                    "error": t.error,
                }
                for t in task_results
            ],
        },
        report=report,
        research_metadata=metadata,
    )

    await emitter.emit(
        "report",
        "done",
        "Studio Brief ready",
        run_status=status,
        sources=len(report.sources),
        duration_ms=metadata.total_duration_ms,
    )
    return response


async def _execute_searches(
    brief: ProjectBrief,
    plan: ResearchPlan,
    client: ParallelClient,
    emitter: Emitter,
) -> Tuple[List[TaskResult], Dict[str, List[Dict[str, Any]]]]:
    """Run every planned search concurrently, tolerating individual failures."""
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_SEARCHES)
    raw_by_task: Dict[str, List[Dict[str, Any]]] = {}
    objective_context = _objective_context(brief)

    async with httpx.AsyncClient(timeout=client.timeout) as http:

        async def run_task(task: SearchTask) -> TaskResult:
            async with semaphore:
                await emitter.emit(
                    "search",
                    "info",
                    task.label(),
                    task_id=task.id,
                    category=task.category,
                    query=task.query,
                )
                started = time.perf_counter()
                try:
                    results = await client.search(
                        task.query,
                        objective=f"{task.question} (context: {objective_context})",
                        client=http,
                    )
                except ParallelSearchError as exc:
                    duration = int((time.perf_counter() - started) * 1000)
                    logger.warning("search.failed task=%s: %s", task.id, exc)
                    raw_by_task[task.id] = []
                    return TaskResult(
                        task=task, result_count=0, duration_ms=duration, error=str(exc)
                    )
                except Exception as exc:  # pragma: no cover - defensive
                    duration = int((time.perf_counter() - started) * 1000)
                    logger.warning("search.unexpected_error task=%s: %s", task.id, exc)
                    raw_by_task[task.id] = []
                    return TaskResult(
                        task=task,
                        result_count=0,
                        duration_ms=duration,
                        error=f"{exc.__class__.__name__}: {exc}",
                    )

                duration = int((time.perf_counter() - started) * 1000)
                raw_by_task[task.id] = results
                await emitter.emit(
                    "search",
                    "info",
                    f"{task.label()} — {len(results)} results",
                    task_id=task.id,
                    category=task.category,
                    query=task.query,
                    result_count=len(results),
                )
                return TaskResult(
                    task=task, result_count=len(results), duration_ms=duration
                )

        results = await asyncio.gather(*(run_task(t) for t in plan.tasks))

    return list(results), raw_by_task


def _objective_context(brief: ProjectBrief) -> str:
    """Compact brief description passed to Parallel as search intent."""
    parts = [
        brief.title,
        brief.format,
        brief.genre,
        brief.geography,
        brief.target_audience,
    ]
    context = ", ".join(p for p in parts if p)
    description = (brief.description or "").strip()
    if description:
        context = f"{context}. {description[:300]}"
    return context or brief.title

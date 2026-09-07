"""StudioOps HTTP API.

    POST /api/v1/research              run synchronously, return the Studio Brief
    POST /api/v1/research/async        start a run, return a run_id immediately
    GET  /api/v1/research/{run_id}     run status (+ result when finished)
    GET  /api/v1/research/{run_id}/events   SSE stream of real progress events
    GET  /api/v1/config                which integrations are configured

Client-facing errors carry a safe message; details go to the logs. Raw
exceptions and credentials are never returned to the browser.
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from backend.agent.workflow import ResearchFailure, run_studioops
from backend.integrations.gemini_client import GeminiClient
from backend.models.brief import ProjectBrief
from backend.services.run_store import DONE, store
from backend.tools.parallel_client import ParallelClient, ParallelSearchError
from backend.tools.report_store import save_report

logger = logging.getLogger(__name__)

router = APIRouter()

GENERIC_ERROR = "We couldn't complete the research. Please try again."


def _persist(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Save the report to disk and attach download URLs."""
    try:
        names = save_report(payload)
        payload["report_url_json"] = f"/reports/{names['json']}"
        payload["report_url_md"] = f"/reports/{names['md']}"
    except Exception as exc:
        logger.warning("report.persist_failed: %s", exc)
    return payload


@router.get("/api/v1/config")
async def config() -> Dict[str, Any]:
    """Report integration readiness. Never returns key material."""
    gemini = GeminiClient()
    try:
        ParallelClient()
        parallel_ready, parallel_detail = True, "Parallel Search API configured"
    except ParallelSearchError as exc:
        parallel_ready, parallel_detail = False, str(exc)

    return {
        "parallel": {"configured": parallel_ready, "detail": parallel_detail},
        "gemini": gemini.status.as_dict(),
    }


@router.post("/api/v1/research")
async def start_research(brief: ProjectBrief) -> Dict[str, Any]:
    """Run the full workflow and return the Studio Brief."""
    run_id = uuid.uuid4().hex[:12]
    run = store.create(run_id, brief.model_dump())

    try:
        response = await run_studioops(brief, on_progress=run.publish, run_id=run_id)
    except ResearchFailure as exc:
        logger.warning("research.failed run=%s stage=%s: %s", run_id, exc.stage, exc)
        run.fail(str(exc), stage=exc.stage)
        raise HTTPException(
            status_code=502,
            detail={
                "run_id": run_id,
                "stage": exc.stage,
                "message": _user_message(exc),
            },
        )
    except Exception as exc:
        logger.exception("research.unexpected_error run=%s", run_id)
        run.fail(str(exc), stage="unknown")
        raise HTTPException(
            status_code=500,
            detail={"run_id": run_id, "stage": "unknown", "message": GENERIC_ERROR},
        )

    payload = _persist(response.model_dump())
    run.complete(payload)
    return payload


@router.post("/api/v1/research/async")
async def start_research_async(brief: ProjectBrief) -> Dict[str, Any]:
    """Start a run in the background and return its run_id immediately.

    Progress is available at /api/v1/research/{run_id}/events, the result at
    /api/v1/research/{run_id}.
    """
    run_id = uuid.uuid4().hex[:12]
    run = store.create(run_id, brief.model_dump())

    async def _execute() -> None:
        try:
            response = await run_studioops(brief, on_progress=run.publish, run_id=run_id)
        except ResearchFailure as exc:
            logger.warning("research.failed run=%s stage=%s: %s", run_id, exc.stage, exc)
            await run.publish(
                {
                    "run_id": run_id,
                    "stage": exc.stage,
                    "status": "error",
                    "message": _user_message(exc),
                }
            )
            run.fail(_user_message(exc), stage=exc.stage)
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception("research.unexpected_error run=%s", run_id)
            await run.publish(
                {
                    "run_id": run_id,
                    "stage": "unknown",
                    "status": "error",
                    "message": GENERIC_ERROR,
                }
            )
            run.fail(GENERIC_ERROR, stage="unknown")
        else:
            run.complete(_persist(response.model_dump()))

    task = asyncio.create_task(_execute())
    # Hold a reference so the task isn't garbage-collected mid-flight.
    run.task = task  # type: ignore[attr-defined]

    return {"run_id": run_id, "status": "running"}


@router.get("/api/v1/research/{run_id}")
async def research_status(run_id: str) -> Dict[str, Any]:
    """Return run status, including the full result once finished."""
    run = store.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail={"message": "Run not found."})

    payload = run.status_payload()
    if run.result is not None:
        payload["result"] = run.result
    return payload


@router.get("/api/v1/research/{run_id}/events")
async def research_events(run_id: str, request: Request) -> StreamingResponse:
    """Stream real progress events for a run as Server-Sent Events."""
    run = store.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail={"message": "Run not found."})

    queue = run.subscribe()

    async def event_stream():
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    item = await asyncio.wait_for(queue.get(), timeout=15.0)
                except asyncio.TimeoutError:
                    # Keep-alive comment so proxies don't close an idle stream.
                    yield ": keep-alive\n\n"
                    continue

                if item is DONE:
                    final = {
                        "stage": "complete",
                        "status": run.status,
                        "run_id": run.run_id,
                        "error": run.error,
                    }
                    yield f"event: complete\ndata: {json.dumps(final)}\n\n"
                    break

                yield f"event: progress\ndata: {json.dumps(item)}\n\n"
        finally:
            run.unsubscribe(queue)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


def _user_message(exc: ResearchFailure) -> str:
    """Map an internal failure onto a safe, actionable user message."""
    stage_messages = {
        "plan": "We couldn't build a research plan for that brief. Try adding more detail.",
        "search": "The live web research couldn't be completed. Please try again.",
    }
    message = str(exc)
    # Configuration problems are actionable for the operator, and contain no secrets.
    if "PARALLEL_API_KEY" in message or "API key" in message:
        return "Web research is not configured on the server (missing or invalid Parallel API key)."
    return stage_messages.get(exc.stage, GENERIC_ERROR)

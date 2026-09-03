from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel

from backend.agent.workflow import run_studioops
from backend.models.brief import ProjectBrief
from backend.models.report import StudioOpsReport

app = FastAPI(title="StudioOps")


class ResearchRequest(BaseModel):
    title: str
    description: str
    format: str | None = None
    genre: str | None = None
    target_audience: str | None = None
    geography: str | None = None
    budget_tier: str | None = None
    production_stage: str | None = None


class ResearchResponse(BaseModel):
    status: str
    report: StudioOpsReport | None = None
    error: str | None = None


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/v1/research")
async def research(request: ResearchRequest) -> ResearchResponse:
    brief = ProjectBrief(**request.model_dump())

    try:
        report = await run_studioops(brief)
        return ResearchResponse(status="completed", report=report)
    except ValueError as exc:
        return ResearchResponse(status="failed", report=None, error=str(exc))
    except Exception:  # pragma: no cover - defensive fallback for runtime failures
        return ResearchResponse(status="failed", report=None, error="Research failed due to a backend runtime error.")

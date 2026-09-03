from __future__ import annotations

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


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/v1/research")
async def research(request: ResearchRequest) -> dict[str, str | StudioOpsReport]:
    brief = ProjectBrief(**request.model_dump())
    report = await run_studioops(brief)
    return {"status": "completed", "report": report}

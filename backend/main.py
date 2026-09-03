from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel

from backend.agent.workflow import run_studioops
from backend.models.brief import ProjectBrief
from backend.models.report import StudioOpsReport

app = FastAPI(title="StudioOps")


class ResearchRequest(BaseModel):
    project_title: str | None = None
    title: str | None = None
    format: str | None = None
    genre: str | None = None
    market: str | None = None
    territory: str | None = None
    geography: str | None = None
    brief: str | None = None
    description: str | None = None
    research_questions: list[str] = []
    target_audience: str | None = None
    budget_tier: str | None = None
    production_stage: str | None = None

    @property
    def resolved_title(self) -> str:
        return self.project_title or self.title or "Untitled Project"

    @property
    def resolved_description(self) -> str:
        return self.brief or self.description or "No brief provided."

    @property
    def resolved_market(self) -> str | None:
        return self.market or self.territory or self.geography


class ResearchResponse(BaseModel):
    status: str
    project: dict[str, str] | None = None
    summary: str | None = None
    sections: list[dict[str, Any]] = []
    recommendations: list[str] = []
    sources: list[str] = []
    research_metadata: dict[str, int] = {"queries_run": 0, "sources_reviewed": 0}
    report: StudioOpsReport | None = None
    error: str | None = None


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/research")
@app.post("/api/v1/research")
async def research(request: ResearchRequest) -> ResearchResponse:
    brief = ProjectBrief(
        title=request.resolved_title,
        description=request.resolved_description,
        format=request.format,
        genre=request.genre,
        target_audience=request.target_audience,
        geography=request.resolved_market,
        budget_tier=request.budget_tier,
        production_stage=request.production_stage,
    )

    try:
        report = await run_studioops(brief)
        project = {
            "title": brief.title,
            "format": brief.format or "",
            "genre": brief.genre or "",
            "market": brief.geography or "",
        }
        sections = [
            {"title": "Executive Summary", "content": report.executive_summary},
            {"title": "Comparable Titles", "content": report.comparable_titles},
            {"title": "Market Signals", "content": report.market_signals},
            {"title": "Production Intelligence", "content": report.production_intelligence},
            {"title": "Risks", "content": report.risks},
        ]
        return ResearchResponse(
            status="completed",
            project=project,
            summary=report.executive_summary,
            sections=sections,
            recommendations=report.next_steps,
            sources=[source.url for source in report.sources],
            research_metadata={
                "queries_run": max(1, len(report.sources) or 1),
                "sources_reviewed": max(1, len(report.sources) or 1),
            },
            report=report,
        )
    except ValueError as exc:
        return ResearchResponse(status="failed", project=None, summary=None, error=str(exc))
    except Exception:  # pragma: no cover - defensive fallback for runtime failures
        return ResearchResponse(status="failed", project=None, summary=None, error="Research failed due to a backend runtime error.")

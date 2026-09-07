"""Studio Brief report models.

Every substantive claim carries `evidence_ids` pointing at retrieved sources.
`confidence` and the `insufficient_evidence` flags let the synthesizer say
"the research does not support a conclusion here" instead of inventing one.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from backend.models.research import Evidence, ResearchMetadata


class Cited(BaseModel):
    """Base for any claim that must be traceable to evidence."""

    evidence_ids: List[str] = Field(default_factory=list)


class ComparableTitle(Cited):
    title: str
    year: Optional[str] = None
    genre: Optional[str] = None
    market: Optional[str] = None
    insight: str = ""


class MarketSignal(Cited):
    signal: str
    detail: str = ""
    metric: Optional[str] = None  # only when the number appears in a source
    trend: Optional[str] = None  # "up" | "down" | "flat" | None


class AudienceInsight(Cited):
    insight: str
    detail: str = ""


class CompetitiveInsight(Cited):
    observation: str
    detail: str = ""
    gap_or_opportunity: Optional[str] = None


class Opportunity(Cited):
    title: str
    category: Optional[str] = None  # partner | location | distribution | funding | talent
    detail: str = ""


class Risk(Cited):
    title: str
    severity: str = "medium"  # low | medium | high
    explanation: str = ""
    recommended_action: str = ""


class NextStep(BaseModel):
    step: str
    rationale: str = ""


class ReportSection(BaseModel):
    """Wraps a section so the UI can render an honest empty state."""

    insufficient_evidence: bool = False
    note: str = ""


class StudioOpsReport(BaseModel):
    executive_summary: str = ""
    key_opportunities: List[str] = Field(default_factory=list)
    comparable_titles: List[ComparableTitle] = Field(default_factory=list)
    market_signals: List[MarketSignal] = Field(default_factory=list)
    audience_insights: List[AudienceInsight] = Field(default_factory=list)
    competitive_landscape: List[CompetitiveInsight] = Field(default_factory=list)
    production_opportunities: List[Opportunity] = Field(default_factory=list)
    risks: List[Risk] = Field(default_factory=list)
    next_steps: List[NextStep] = Field(default_factory=list)
    evidence_gaps: List[str] = Field(default_factory=list)
    sources: List[Evidence] = Field(default_factory=list)
    section_notes: Dict[str, ReportSection] = Field(default_factory=dict)
    generated_by: str = "fallback"  # "gemini" | "fallback"


class ProjectSummary(BaseModel):
    title: str
    format: Optional[str] = None
    genre: Optional[str] = None
    geography: Optional[str] = None
    target_audience: Optional[str] = None
    researched_at: Optional[str] = None


class ResearchResponse(BaseModel):
    """Top-level API response for a completed run."""

    status: str = "completed"  # completed | partial | failed
    run_id: str
    project: ProjectSummary
    plan: Dict[str, Any] = Field(default_factory=dict)
    report: StudioOpsReport = Field(default_factory=StudioOpsReport)
    research_metadata: ResearchMetadata = Field(default_factory=ResearchMetadata)
    report_url_json: Optional[str] = None
    report_url_md: Optional[str] = None
    message: Optional[str] = None

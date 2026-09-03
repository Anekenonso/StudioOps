from pydantic import BaseModel, Field

from .research import Evidence


class Risk(BaseModel):
    title: str
    severity: str
    explanation: str
    evidence_urls: list[str] = Field(default_factory=list)
    recommended_action: str


class StudioOpsReport(BaseModel):
    executive_summary: str
    key_opportunities: list[str] = Field(default_factory=list)
    comparable_titles: list[dict] = Field(default_factory=list)
    market_signals: list[dict] = Field(default_factory=list)
    production_intelligence: list[dict] = Field(default_factory=list)
    risks: list[Risk] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)
    sources: list[Evidence] = Field(default_factory=list)

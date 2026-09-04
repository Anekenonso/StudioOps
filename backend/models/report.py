from pydantic import BaseModel
from typing import List, Dict, Any


class Evidence(BaseModel):
    title: str
    url: str
    source: str | None = None
    snippet: str | None = None
    relevance: float | None = 0.0


class ComparableTitle(BaseModel):
    title: str
    year: str | None = None
    genre: str | None = None
    market: str | None = None
    source: str | None = None


class Risk(BaseModel):
    title: str
    severity: str | None = None
    explanation: str | None = None
    evidence_urls: List[str] = []


class StudioOpsReport(BaseModel):
    executive_summary: str
    key_opportunities: List[str] = []
    comparable_titles: List[ComparableTitle] = []
    market_signals: List[Dict[str, Any]] = []
    production_intelligence: List[Dict[str, Any]] = []
    risks: List[Risk] = []
    next_steps: List[str] = []
    sources: List[Evidence] = []

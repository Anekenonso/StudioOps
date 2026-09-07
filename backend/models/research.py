"""Research plan and evidence models.

These sit between the planner (Gemini) and the synthesizer (Gemini), and are
the schema the Parallel search layer fills in.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

# Research categories the planner may assign. Kept as a plain tuple (rather than
# an Enum) so an unexpected model-provided category degrades to "other" instead
# of failing validation mid-run.
RESEARCH_CATEGORIES = (
    "comparables",
    "market",
    "audience",
    "competition",
    "production",
    "distribution",
    "developments",
    "other",
)

CATEGORY_LABELS: Dict[str, str] = {
    "comparables": "Searching comparable titles",
    "market": "Searching market & industry data",
    "audience": "Searching audience & demand signals",
    "competition": "Searching the competitive landscape",
    "production": "Searching production companies & locations",
    "distribution": "Searching distribution & platforms",
    "developments": "Searching recent industry developments",
    "other": "Searching industry publications",
}


class SearchTask(BaseModel):
    """One unit of planned research."""

    id: str
    category: str = "other"
    question: str
    query: str
    priority: int = 3

    def label(self) -> str:
        return CATEGORY_LABELS.get(self.category, CATEGORY_LABELS["other"])


class ResearchPlan(BaseModel):
    """The planner's output: what StudioOps decided to investigate and why."""

    reasoning: str = ""
    tasks: List[SearchTask] = Field(default_factory=list)
    generated_by: str = "fallback"  # "gemini" | "fallback"

    @property
    def queries(self) -> List[str]:
        return [t.query for t in self.tasks]


class Evidence(BaseModel):
    """A single normalized web source retrieved through Parallel."""

    id: str  # stable citation handle, e.g. "S3"
    title: str
    url: str
    publisher: Optional[str] = None
    published_date: Optional[str] = None
    snippet: str = ""
    excerpts: List[str] = Field(default_factory=list)
    categories: List[str] = Field(default_factory=list)
    queries: List[str] = Field(default_factory=list)
    relevance: float = 0.0


class TaskResult(BaseModel):
    """Outcome of executing one SearchTask against Parallel."""

    task: SearchTask
    evidence_ids: List[str] = Field(default_factory=list)
    result_count: int = 0
    duration_ms: int = 0
    error: Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.error is None


class ResearchMetadata(BaseModel):
    """Auditable facts about a run — what ran, how long, what failed."""

    queries_run: int = 0
    queries_failed: int = 0
    sources_reviewed: int = 0
    unique_sources: int = 0
    search_duration_ms: int = 0
    synthesis_duration_ms: int = 0
    total_duration_ms: int = 0
    planner: str = "fallback"
    synthesizer: str = "fallback"
    warnings: List[str] = Field(default_factory=list)


class ResearchContext(BaseModel):
    """Everything gathered before synthesis."""

    plan: ResearchPlan
    evidence: List[Evidence] = Field(default_factory=list)
    task_results: List[TaskResult] = Field(default_factory=list)
    metadata: ResearchMetadata = Field(default_factory=ResearchMetadata)

    def evidence_by_id(self) -> Dict[str, Evidence]:
        return {e.id: e for e in self.evidence}

    def as_prompt_payload(self, max_chars_per_source: int = 1200) -> List[Dict[str, Any]]:
        """Compact evidence for a model prompt, keyed by citation id."""
        payload = []
        for ev in self.evidence:
            text = " ".join(ev.excerpts) or ev.snippet
            payload.append(
                {
                    "id": ev.id,
                    "title": ev.title,
                    "url": ev.url,
                    "publisher": ev.publisher,
                    "published_date": ev.published_date,
                    "categories": ev.categories,
                    "content": text[:max_chars_per_source],
                }
            )
        return payload

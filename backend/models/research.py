from pydantic import BaseModel, Field


class SearchTask(BaseModel):
    category: str
    question: str
    query: str
    priority: int


class Evidence(BaseModel):
    title: str
    url: str
    snippet: str = ""
    source_type: str | None = None
    relevance: float = 0.0


class ResearchPlan(BaseModel):
    tasks: list[SearchTask] = Field(..., min_length=1)

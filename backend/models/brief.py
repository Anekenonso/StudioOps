from pydantic import BaseModel


class ProjectBrief(BaseModel):
    title: str
    description: str
    format: str | None = None
    genre: str | None = None
    target_audience: str | None = None
    geography: str | None = None
    budget_tier: str | None = None
    production_stage: str | None = None

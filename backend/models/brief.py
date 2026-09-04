from pydantic import BaseModel
from typing import List, Optional


class ProjectBrief(BaseModel):
    title: str
    description: str
    format: Optional[str] = None
    genre: Optional[str] = None
    target_audience: Optional[str] = None
    geography: Optional[str] = None
    budget_tier: Optional[str] = None
    production_stage: Optional[str] = None
    research_questions: Optional[List[str]] = []

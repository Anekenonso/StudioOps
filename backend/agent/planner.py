from __future__ import annotations

import json
import os

from google import genai

from backend.agent.prompts import PLANNER_SYSTEM_PROMPT
from backend.models.brief import ProjectBrief
from backend.models.research import ResearchPlan, SearchTask


class ResearchPlanner:
    """Creates a focused research plan from the production brief."""

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        self.model = model or os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

    async def create_plan(self, brief: ProjectBrief) -> ResearchPlan:
        if self.api_key:
            try:
                client = genai.Client(api_key=self.api_key)
                prompt = PLANNER_SYSTEM_PROMPT.format(
                    title=brief.title,
                    description=brief.description,
                    format=brief.format or "Unknown",
                    genre=brief.genre or "Unknown",
                    target_audience=brief.target_audience or "Unknown",
                    geography=brief.geography or "Unknown",
                    budget_tier=brief.budget_tier or "Unknown",
                    production_stage=brief.production_stage or "Unknown",
                )
                response = client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config={
                        "response_mime_type": "application/json",
                        "response_schema": ResearchPlan,
                    },
                )
                payload = json.loads(response.text)
                return ResearchPlan.model_validate(payload)
            except Exception:
                pass

        return self._fallback_plan(brief)

    def _fallback_plan(self, brief: ProjectBrief) -> ResearchPlan:
        tasks = [
            SearchTask(
                category="comparables",
                question=f"What comparable projects are similar to '{brief.title}'?",
                query=f"{brief.title} {brief.genre or ''} comparable productions market research streaming".strip(),
                priority=1,
            ),
            SearchTask(
                category="audience",
                question=f"What audience signals matter for {brief.target_audience or 'the target audience'}?",
                query=f"{brief.genre or brief.title} audience insights {brief.geography or 'Africa'} streaming viewership".strip(),
                priority=1,
            ),
            SearchTask(
                category="market",
                question=f"What market and audience trends relate to {brief.geography or 'the region'}?",
                query=f"{brief.geography or 'African'} streaming market trends {brief.genre or 'series'}".strip(),
                priority=2,
            ),
            SearchTask(
                category="production",
                question="What production considerations or budget realities matter for this format?",
                query=f"{brief.genre or brief.title} production considerations budget {brief.budget_tier or 'mid-budget'}".strip(),
                priority=2,
            ),
            SearchTask(
                category="competition",
                question="What competitive signals or recent industry developments matter?",
                query=f"{brief.genre or brief.title} {brief.geography or 'global'} competition streaming release trends".strip(),
                priority=3,
            ),
        ]
        return ResearchPlan(tasks=tasks)

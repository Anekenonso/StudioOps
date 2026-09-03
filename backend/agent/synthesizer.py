from __future__ import annotations

import json
import os
from typing import Any

from google import genai

from backend.agent.prompts import SYNTHESIS_SYSTEM_PROMPT
from backend.models.brief import ProjectBrief
from backend.models.report import StudioOpsReport


class ReportSynthesizer:
    """Uses Gemini to produce a structured StudioOps report from validated evidence."""

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        self.model = model or os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

    async def synthesize(self, brief: ProjectBrief, evidence: list[dict[str, Any]]) -> StudioOpsReport:
        if self.api_key:
            try:
                client = genai.Client(api_key=self.api_key)
                evidence_text = "\n\n".join(
                    f"- {item.get('title', 'Untitled')} | {item.get('url', '')}\n  {item.get('snippet', '')}"
                    for item in evidence[:20]
                )
                prompt = SYNTHESIS_SYSTEM_PROMPT.format(
                    title=brief.title,
                    description=brief.description,
                    format=brief.format or "Unknown",
                    genre=brief.genre or "Unknown",
                    target_audience=brief.target_audience or "Unknown",
                    geography=brief.geography or "Unknown",
                    budget_tier=brief.budget_tier or "Unknown",
                    production_stage=brief.production_stage or "Unknown",
                    evidence_text=evidence_text or "No evidence was retrieved.",
                )
                response = client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config={
                        "response_mime_type": "application/json",
                        "response_schema": StudioOpsReport,
                    },
                )
                payload = json.loads(response.text)
                return StudioOpsReport.model_validate(payload)
            except Exception:
                pass

        return StudioOpsReport(
            executive_summary="Evidence was retrieved, but synthesis could not be completed from the configured model environment. The report is intentionally conservative and grounded only in available evidence.",
            key_opportunities=[],
            comparable_titles=[],
            market_signals=[],
            production_intelligence=[],
            risks=[],
            next_steps=["Validate the model configuration and retry synthesis.", "Collect more evidence if the brief is under-specified."],
            sources=[
                {
                    "title": item.get("title", "Untitled source"),
                    "url": item.get("url", ""),
                    "snippet": item.get("snippet", ""),
                    "source_type": item.get("source_type", "web"),
                    "relevance": float(item.get("relevance") or 0.0),
                }
                for item in evidence[:10]
            ],
        )

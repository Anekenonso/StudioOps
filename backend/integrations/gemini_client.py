"""Gemini adapter stub.

This adapter attempts to use the Google Cloud Gemini/Vertex AI SDK
when available and credentials are provided via environment variables.
For Phase 1 it falls back to lightweight local stubs that reuse the
existing `planner` and `synthesizer` implementations so the workflow
remains functional without live Google credentials.

When ready to enable real Gemini calls, install `google-cloud-aiplatform`
and ensure `GOOGLE_APPLICATION_CREDENTIALS`, `GOOGLE_CLOUD_PROJECT`, and
`GEMINI_MODEL` are set in the environment.
"""
from typing import Any, Dict, List, Optional
import os
import logging

try:
    import google.cloud.aiplatform as aiplatform  # type: ignore
    # Some versions expose TextGenerationModel at top-level
    try:
        from google.cloud.aiplatform import TextGenerationModel  # type: ignore
        _HAS_TG_MODEL = True
    except Exception:
        _HAS_TG_MODEL = False
    _GCP_AVAILABLE = True
except Exception:
    aiplatform = None
    _GCP_AVAILABLE = False
    _HAS_TG_MODEL = False

from backend.agent import planner as local_planner
from backend.agent.synthesizer import synthesize_report as local_synthesize
from backend.models.brief import ProjectBrief

logger = logging.getLogger(__name__)


class GeminiClient:
    def __init__(self, project: Optional[str] = None, location: Optional[str] = None, model: Optional[str] = None):
        self.project = project or os.getenv("GOOGLE_CLOUD_PROJECT")
        self.location = location or os.getenv("GOOGLE_CLOUD_LOCATION")
        self.model = model or os.getenv("GEMINI_MODEL")
        self.available = _GCP_AVAILABLE and bool(self.project and self.model)

    async def plan(self, brief: ProjectBrief) -> Dict[str, Any]:
        """Return a research plan. If Gemini/Vertex is available, this
        should call the model; otherwise return a local planner-derived plan.
        """
        if self.available and _HAS_TG_MODEL:
            # Attempt to call Vertex AI TextGenerationModel for planning
            try:
                prompt = (
                    f"Generate a JSON array of concise research queries for this production brief:\nTitle: {brief.title}\nGenre: {brief.genre}\nGeography: {brief.geography}\nDescription: {brief.description}\nReturn: {\"research_tasks\": [{\"id\": \"..\", \"query\": \"...\"}]}"
                )
                model = TextGenerationModel.from_pretrained(self.model)
                resp = model.predict(prompt, max_output_tokens=512)
                # Attempt to parse JSON from response
                import json

                text = resp.text if hasattr(resp, "text") else str(resp)
                try:
                    parsed = json.loads(text)
                    return parsed
                except Exception:
                    logger.warning("Gemini plan: failed to parse model output as JSON; falling back")
            except Exception as e:
                logger.warning(f"Gemini plan failed: {e}; falling back to local planner")
        else:
            if self.available and not _HAS_TG_MODEL:
                logger.info("Gemini SDK available but TextGenerationModel not found; falling back to local planner")
        # Fallback to local planner
        queries = local_planner.create_research_queries(brief)
        return {"research_tasks": [{"id": f"q{i}", "query": q} for i, q in enumerate(queries, start=1)]}

    async def synthesize(self, brief: ProjectBrief, evidence_groups: List[Dict[str, Any]]):
        """Synthesize a structured report. If Gemini is available use it,
        otherwise use the local synthesizer stub.
        """
        if self.available and _HAS_TG_MODEL:
            try:
                # Build a conservative synthesis prompt that asks for JSON output.
                import json

                evidence_text = "\n".join([f"- {g.get('query')}: {len(g.get('results', []))} results" for g in evidence_groups])
                prompt = (
                    f"Using the supplied evidence summaries, produce a JSON object with keys: executive_summary, comparable_titles (array), market_signals (array), production_intelligence (array), risks (array), next_steps (array), sources (array of {\"title\", \"url\"}).\\n"
                    f"Brief:\nTitle: {brief.title}\nGenre: {brief.genre}\nGeography: {brief.geography}\nDescription: {brief.description}\nEvidence summary:\n{evidence_text}\n"
                )
                model = TextGenerationModel.from_pretrained(self.model)
                resp = model.predict(prompt, max_output_tokens=1024)
                text = resp.text if hasattr(resp, "text") else str(resp)
                try:
                    parsed = json.loads(text)
                    return parsed
                except Exception:
                    logger.warning("Gemini synthesize: failed to parse JSON; falling back to local synthesizer")
            except Exception as e:
                logger.warning(f"Gemini synthesize failed: {e}; falling back to local synthesizer")

        # Fallback to local synthesizer
        report = local_synthesize(brief, evidence_groups)
        return report

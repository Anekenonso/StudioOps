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
    _GCP_AVAILABLE = True
except Exception:
    _GCP_AVAILABLE = False

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
        if self.available:
            # Real implementation would call Vertex/PaLM API to generate a structured plan.
            # Placeholder: not implemented in Phase 1.
            logger.info("Gemini available but not implemented: falling back to local planner")
        # Fallback to local planner
        queries = local_planner.create_research_queries(brief)
        return {"research_tasks": [{"id": f"q{i}", "query": q} for i, q in enumerate(queries, start=1)]}

    async def synthesize(self, brief: ProjectBrief, evidence_groups: List[Dict[str, Any]]):
        """Synthesize a structured report. If Gemini is available use it,
        otherwise use the local synthesizer stub.
        """
        if self.available:
            # Real implementation would prepare a synthesis prompt and call the model.
            logger.info("Gemini available but not implemented: falling back to local synthesizer")

        # Use local synthesizer to produce a conservative, evidence-backed report.
        report = local_synthesize(brief, evidence_groups)
        return report

from __future__ import annotations

from backend.agent.planner import ResearchPlanner
from backend.agent.synthesizer import ReportSynthesizer
from backend.models.brief import ProjectBrief
from backend.models.report import StudioOpsReport
from backend.services.evidence import EvidenceProcessor
from backend.services.validation import validate_report
from backend.tools.parallel_search import ParallelSearchClient


async def run_studioops(brief: ProjectBrief) -> StudioOpsReport:
    planner = ResearchPlanner()
    synthesizer = ReportSynthesizer()
    search_client = ParallelSearchClient()
    evidence_processor = EvidenceProcessor()

    research_plan = await planner.create_plan(brief)
    search_results = await search_client.search_many(research_plan.tasks)
    evidence = evidence_processor.process(search_results)
    report = await synthesizer.synthesize(brief, evidence)
    return validate_report(report)

from backend.models.brief import ProjectBrief
from backend.models.report import StudioOpsReport
from backend.models.research import Evidence, ResearchPlan, SearchTask


def test_project_brief_valid() -> None:
    brief = ProjectBrief(
        title="Untitled Nigerian Crime Thriller",
        description="A crime thriller series for a young African streaming audience.",
        format="Series",
        genre="Crime Thriller",
        target_audience="Young Adults",
        geography="Nigeria / Africa",
    )
    assert brief.title == "Untitled Nigerian Crime Thriller"


def test_report_schema_valid() -> None:
    report = StudioOpsReport(
        executive_summary="Summary",
        key_opportunities=["Opportunity"],
        comparable_titles=[{"title": "Example", "why_it_matters": "Test", "evidence_url": "https://example.com"}],
        market_signals=[{"signal": "Signal", "detail": "Detail", "evidence_url": "https://example.com"}],
        production_intelligence=[{"topic": "Topic", "detail": "Detail", "evidence_url": "https://example.com"}],
        risks=[],
        next_steps=["Next step"],
        sources=[{"title": "Source", "url": "https://example.com", "snippet": "Example", "source_type": "web", "relevance": 0.9}],
    )
    assert report.executive_summary == "Summary"


def test_research_plan_valid() -> None:
    plan = ResearchPlan(
        tasks=[
            SearchTask(category="comparables", question="Question", query="query", priority=1),
        ]
    )
    assert len(plan.tasks) == 1

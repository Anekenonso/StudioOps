from backend.agent.planner import create_research_queries
from backend.models.brief import ProjectBrief


def test_create_research_queries_basic():
    brief = ProjectBrief(
        title="Lagos After Dark",
        description="A crime thriller",
        genre="Crime Thriller",
        geography="Nigeria",
    )
    queries = create_research_queries(brief)
    assert isinstance(queries, list)
    assert any("Crime Thriller" in q or "crime thriller" in q.lower() for q in queries)

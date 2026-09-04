from typing import List
from backend.models.brief import ProjectBrief


def create_research_queries(brief: ProjectBrief) -> List[str]:
    """Generate a small set of focused search queries from the user brief.

    This is a lightweight planner stub for Phase 1. Later, replace with
    a Gemini-driven planner that returns structured research tasks.
    """
    title = brief.title or ""
    genre = brief.genre or ""
    geography = brief.geography or ""
    audience = brief.target_audience or ""

    queries = []

    # Comparable titles
    if genre and geography:
        queries.append(f"recent {genre} films and series in {geography}")
    elif genre:
        queries.append(f"recent {genre} films and series")
    else:
        queries.append(f"recent films and series similar to {title}")

    # Audience and market trends
    if genre and geography:
        queries.append(f"{genre} audience trends in {geography}")
    else:
        queries.append(f"audience trends for {genre or title}")

    # Production companies
    queries.append(f"production companies in {geography} that produce {genre}")

    # Distribution and platforms
    queries.append(f"distribution platforms and recent {genre} releases in {geography}")

    return queries

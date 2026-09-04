from fastapi import APIRouter
from backend.models.brief import ProjectBrief
from backend.tools.parallel_client import ParallelClient
from backend.agent.planner import create_research_queries
import os
import asyncio


router = APIRouter()


@router.post("/api/v1/research")
async def start_research(brief: ProjectBrief):
    """Accept a production brief, create queries, run Parallel searches,
    and return normalized evidence per query.
    """
    # Create simple research plan (queries)
    queries = create_research_queries(brief)

    # Instantiate Parallel client
    base_url = os.getenv("PARALLEL_BASE_URL")
    api_key = os.getenv("PARALLEL_API_KEY")
    try:
        client = ParallelClient(api_key=api_key, base_url=base_url)
    except RuntimeError as exc:
        return {"status": "error", "message": str(exc)}

    # Run searches concurrently
    async def run_query(q: str):
        try:
            results = await client.search(q)
            return {"query": q, "results": results}
        except Exception as e:
            return {"query": q, "error": str(e), "results": []}

    tasks = [run_query(q) for q in queries]
    done = await asyncio.gather(*tasks)

    return {
        "status": "completed",
        "project": {
            "title": brief.title,
            "format": brief.format,
            "genre": brief.genre,
            "geography": brief.geography,
        },
        "plan": {"queries": queries},
        "evidence": done,
    }

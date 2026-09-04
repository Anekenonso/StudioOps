from fastapi import APIRouter
from backend.models.brief import ProjectBrief
from backend.tools.parallel_client import ParallelClient
from backend.integrations.gemini_client import GeminiClient
import os
import asyncio


router = APIRouter()


@router.post("/api/v1/research")
async def start_research(brief: ProjectBrief):
    """Accept a production brief, create queries, run Parallel searches,
    and return normalized evidence per query.
    """
    # Use GeminiClient to create a research plan (falls back to local planner)
    gemini = GeminiClient()
    plan = await gemini.plan(brief)
    # plan expected shape: {"research_tasks": [{"id":..., "query": ...}, ...]}
    queries = [t.get("query") for t in plan.get("research_tasks", [])]

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

    # Use GeminiClient to synthesize the final report (falls back to local synthesizer)
    try:
        report_obj = await gemini.synthesize(brief, done)
        # If the synthesizer returned a Pydantic model, convert to dict
        report_data = report_obj.dict() if hasattr(report_obj, "dict") else report_obj
    except Exception as e:
        report_data = {"error": f"synthesis failed: {e}"}

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
        "report": report_data,
    }

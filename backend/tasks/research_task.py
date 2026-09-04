import asyncio
from typing import Dict, Any
from backend.models.brief import ProjectBrief
from backend.integrations.gemini_client import GeminiClient
from backend.tools.parallel_client import ParallelClient
from backend.tools.report_store import save_report_json, save_report_markdown
import os


def run_async(coro):
    try:
        return asyncio.get_event_loop().run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


def perform_research(brief_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Synchronous wrapper to perform the research flow and persist a report.

    Returns a dictionary with keys: status, report_path_json, report_path_md, report
    """
    brief = ProjectBrief(**brief_dict)
    gemini = GeminiClient()

    async def _flow():
        plan = await gemini.plan(brief)
        queries = [t.get("query") for t in plan.get("research_tasks", [])]

        base_url = os.getenv("PARALLEL_BASE_URL")
        api_key = os.getenv("PARALLEL_API_KEY")
        client = ParallelClient(api_key=api_key, base_url=base_url)

        async def run_query(q: str):
            try:
                results = await client.search(q)
                return {"query": q, "results": results}
            except Exception as e:
                return {"query": q, "error": str(e), "results": []}

        tasks = [run_query(q) for q in queries]
        done = await asyncio.gather(*tasks)

        report_obj = await gemini.synthesize(brief, done)
        report_data = report_obj.dict() if hasattr(report_obj, "dict") else report_obj

        wrapper = {
            "status": "completed",
            "project": {"title": brief.title, "format": brief.format, "genre": brief.genre, "geography": brief.geography},
            "plan": {"queries": queries},
            "evidence": done,
            "report": report_data,
        }
        return wrapper

    result = run_async(_flow())

    # persist report
    json_path = save_report_json(result)
    md_path = save_report_markdown(result)
    result_meta = {"report": result.get("report"), "report_path_json": json_path, "report_path_md": md_path}
    return result_meta

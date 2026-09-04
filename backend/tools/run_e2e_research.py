import os
import asyncio
import json

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

from backend.models.brief import ProjectBrief
from backend.api.routes import start_research


def sanitize(obj):
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if any(s in k.lower() for s in ("key", "token", "secret", "authorization")):
                out[k] = "REDACTED"
            else:
                out[k] = sanitize(v)
        return out
    if isinstance(obj, list):
        return [sanitize(i) for i in obj]
    return obj


async def main():
    brief = ProjectBrief(
        title="StudioOps research example",
        description="Investigate ResearchOps and studio management market signals",
        format="report",
        genre="business",
        geography="global",
        research_questions=["What are common ResearchOps practices?", "Who are competitors for StudioOps?"]
    )

    # Call route handler directly; pass background=False explicitly to avoid FastAPI Query default being truthy
    result = await start_research(brief, background=False)
    print(json.dumps(sanitize(result), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())

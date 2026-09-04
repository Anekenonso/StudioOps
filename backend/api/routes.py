from fastapi import APIRouter
from backend.models.brief import ProjectBrief

router = APIRouter()


@router.post("/api/v1/research")
async def start_research(brief: ProjectBrief):
    """Accept a production brief and start research (stub).

    Phase 1: validate input and return an accepted response. Later this
    will enqueue or orchestrate the planner/researcher.
    """
    return {
        "status": "accepted",
        "project": {
            "title": brief.title,
            "format": brief.format,
            "genre": brief.genre,
            "geography": brief.geography,
        },
        "message": "Phase 1: research request received (stub).",
    }

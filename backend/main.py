"""StudioOps FastAPI application."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Load local .env in development if present.
try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # pragma: no cover - optional dependency
    pass

# If a service account JSON is provided via env (CI/Cloud Run secret), write it
# to a file and point GOOGLE_APPLICATION_CREDENTIALS at it.
try:
    from backend.tools.setup_gcp_creds import bootstrap_service_account_from_env

    bootstrap_service_account_from_env()
except Exception:  # pragma: no cover - optional bootstrap
    pass

from backend.api.routes import router as api_router  # noqa: E402
from backend.integrations.gemini_client import GeminiClient  # noqa: E402
from backend.tools.parallel_client import ParallelClient, ParallelSearchError  # noqa: E402
from backend.tools.report_store import REPORT_DIR, ensure_dir  # noqa: E402

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("studioops")

@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Log which integrations are live, so a misconfigured deploy is obvious."""
    try:
        ParallelClient()
        logger.info("integration.parallel ready")
    except ParallelSearchError as exc:
        logger.warning("integration.parallel NOT ready: %s", exc)

    status = GeminiClient().status
    if status.configured:
        logger.info("integration.gemini ready mode=%s model=%s", status.mode, status.model)
    else:
        logger.warning("integration.gemini NOT ready: %s", status.detail)

    yield


app = FastAPI(
    title="StudioOps API",
    description="AI-powered production intelligence for film & entertainment.",
    version="1.0.0",
    lifespan=lifespan,
)

# The Next.js frontend is served from a different origin in both dev and prod.
_origins = [
    origin.strip()
    for origin in (os.getenv("CORS_ALLOW_ORIGINS") or "").split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins or ["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(api_router)

# Serve saved reports for download.
try:
    from fastapi.staticfiles import StaticFiles

    ensure_dir()
    app.mount("/reports", StaticFiles(directory=REPORT_DIR), name="reports")
except Exception as exc:  # pragma: no cover - non-fatal in constrained envs
    logger.warning("static.reports_mount_failed: %s", exc)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}

# StudioOps API — FastAPI on Cloud Run.
#
# Build from the repository root so the whole `backend/` package is in context:
#   docker build -f backend/Dockerfile -t studioops-api .
FROM python:3.12-slim AS base

# - PYTHONUNBUFFERED: logs reach Cloud Logging without buffering.
# - PIP_NO_CACHE_DIR: smaller image, no wheel cache we will never reuse.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Dependencies first, so a code-only change does not re-run pip.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Application code.
COPY backend ./backend

# Reports are written here at runtime. On Cloud Run this is the in-memory
# filesystem — fine for V1, since the report is streamed to the browser anyway.
RUN mkdir -p outputs/reports

# Run as a non-root user.
RUN useradd --create-home --uid 10001 appuser \
    && chown -R appuser:appuser /app
USER appuser

# Cloud Run provides $PORT (default 8080). Uvicorn must bind to it on 0.0.0.0.
ENV PORT=8080
EXPOSE 8080

# Shell form so $PORT expands. One worker: the workflow is async and the run
# store is in-process, so multiple workers would not share run state.
CMD exec uvicorn backend.main:app --host 0.0.0.0 --port ${PORT} --workers 1

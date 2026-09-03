# StudioOps

StudioOps is a deterministic AI production intelligence workflow for media and entertainment teams. It converts a project brief into a research plan, retrieves evidence from Parallel, validates relevance, and synthesizes a production intelligence report with Gemini.

## Architecture

- Backend: FastAPI + Pydantic
- Agent: Google GenAI / Vertex AI
- Research: Parallel Search API
- Frontend: Next.js + TypeScript + Tailwind

## Quick start

1. Copy `.env.example` to `.env` and set the required values.
2. Install backend dependencies.
3. Start the API with `uvicorn backend.main:app --reload`.
4. Run the frontend from the `frontend` directory.

## Core workflow

Intake -> Plan -> Search -> Collect -> Validate -> Synthesize -> Report

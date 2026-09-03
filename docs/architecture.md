# StudioOps Architecture

## Overview

StudioOps is a deterministic production intelligence agent for media and entertainment teams. It begins with a brief, creates a research plan, searches the web through Parallel, normalizes evidence, and synthesizes a decision-support report with Gemini.

## Workflow

1. Intake brief from the UI.
2. Planner creates 4-8 focused research tasks.
3. Parallel Search API retrieves relevant web evidence.
4. Evidence processor deduplicates and normalizes sources.
5. Gemini synthesizes the final report with structure enforced by Pydantic models.
6. Report is returned to the frontend with source provenance.

## Key constraints

- No fabricated citations.
- All external claims must be supported by evidence.
- Structured outputs are validated through Pydantic.
- Server-side secrets must remain on the backend.

# StudioOps — Phase 1 Scaffold

This commit scaffolds Phase 1 of StudioOps: a minimal FastAPI backend,
Pydantic models, and a stubbed `ParallelClient` adapter.

Quick start

1. Create a virtual environment and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
```

2. Run the API server:

```bash
uvicorn backend.main:app --reload --port 8000
```

3. Health check:

```bash
curl http://localhost:8000/health
```

Next steps (Phase 2): implement the official `ParallelClient` calls,
add the Gemini planner/synthesizer, and build the frontend input form.

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

Real Parallel & Gemini setup

- To enable real Parallel calls, set these env vars in production or
	locally (see `.env.example`): `PARALLEL_API_KEY` and `PARALLEL_BASE_URL`.
	The `ParallelClient` uses a POST /search endpoint by default; update
	`PARALLEL_BASE_URL` if your Parallel contract differs.

- To enable real Gemini/Vertex calls, install the official SDK and set
	these environment variables:

```
pip install google-cloud-aiplatform
```

Set in your environment:

```
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1
GEMINI_MODEL=projects/your-project/locations/us-central1/models/your-model-id
```

The `GeminiClient` will attempt to use `TextGenerationModel` from the
`google-cloud-aiplatform` package when available, and falls back to the
local planner/synthesizer stubs if not configured.


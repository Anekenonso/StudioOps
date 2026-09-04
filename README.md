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

Secrets & key rotation

If a secret (API key or credential) was accidentally committed, rotate
it immediately and avoid keeping secrets in the repository. Recommended
steps:

1. Create a local `.env` from `.env.example` and add your real secrets
	there. Do NOT commit `.env`.

```bash
cp .env.example .env
# Edit .env and set PARALLEL_API_KEY and other values
```

2. Add the secret to your deployment/CI provider instead of committing
	it. For GitHub Actions, go to repository Settings → Secrets → Actions
	and add `PARALLEL_API_KEY` and any Google Cloud secrets.

3. Rotate the exposed key at the provider (Parallel) console.

4. (Optional) If the secret was pushed to a remote and you need to
	remove it from history, use `git-filter-repo` or BFG to rewrite
	history, then force-push and notify collaborators. This is invasive
	— rotate the key first.

Notes:
- `.env` is included in `.gitignore` by default in this project.
- `./.env.example` has been sanitized to remove any real keys.



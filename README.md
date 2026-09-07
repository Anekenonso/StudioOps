# StudioOps

**Production intelligence for film & television.** Describe a project in plain
language and StudioOps returns a structured, evidence-backed Studio Brief —
comparable titles, market signals, audience intelligence, competitive landscape,
opportunities, and risks — with every claim traced to a live web source you can
open.

Built for **Agentic Cinema: The Blockbuster Hackathon** (Parallel partner track).

---

## 1. What StudioOps is

StudioOps is an agentic research assistant for producers, development execs, and
financiers. It turns an open-ended creative brief into the kind of grounded
market intelligence a studio analyst would spend a day assembling — in under a
minute, with citations.

## 2. The problem

Development and greenlight decisions ride on scattered, fast-moving information:
what comparable titles did at market, who is commissioning in a territory, where
audiences are moving, which incentives apply, what could sink a production. A
producer either spends hours stitching this together from trade press and
databases, or decides on instinct. Generic chatbots don't help — they
hallucinate figures, invent comps, and cite sources that don't exist.

## 3. The solution

A fixed agentic pipeline that reasons, retrieves, and synthesizes — and refuses
to fabricate:

```
INTAKE → PLAN → SEARCH → COLLECT → VALIDATE → SYNTHESIZE → REPORT
```

- **Gemini plans** the research: it decomposes the brief into targeted,
  category-tagged web queries.
- **Parallel searches** the live web for each query and returns real pages with
  excerpts.
- **Gemini synthesizes** the retrieved evidence into a Studio Brief, citing only
  the source ids it was actually given.
- Anything the search didn't support is listed honestly under *What We Could Not
  Confirm* rather than filled in.

When Gemini is not configured, the brief is still produced — grouped straight
from the retrieved sources and clearly labelled `generated_by: fallback`, so
degraded output is never passed off as model analysis.

## 4. Architecture

```
┌──────────────────────────┐         ┌───────────────────────────────────────┐
│  Next.js 14 frontend      │  HTTP   │  FastAPI backend                        │
│  (App Router, TypeScript) │ ───────▶│                                         │
│                           │  SSE    │   /api/v1/research(/async)              │
│  • Research input          │◀─────── │   /api/v1/research/{id}/events (SSE)    │
│  • Live progress (real     │         │   /api/v1/research/{id}                 │
│    stage + query events)   │         │   /api/v1/config   /reports/*           │
│  • Studio Brief + sources  │         └───────┬───────────────┬────────────────┘
└──────────────────────────┘                 │               │
                                    ┌─────────▼───────┐ ┌─────▼──────────────┐
                                    │  Agent workflow  │ │  Run store (in-mem)│
                                    │  plan→search→…   │ │  pub/sub + replay  │
                                    └───┬──────────┬───┘ └────────────────────┘
                                        │          │
                            ┌───────────▼──┐   ┌───▼────────────────┐
                            │ Gemini client │   │ Parallel client     │
                            │ (google-genai)│   │ (/v1beta/search)    │
                            │ plan+synthesize│  │ live web retrieval  │
                            └───────────────┘   └─────────────────────┘
```

The workflow emits progress events at every stage; the API relays them over SSE
with a polling fallback, so the frontend timeline reflects **real** backend
activity, never a simulation.

## 5. Technology stack

| Layer      | Choice |
|------------|--------|
| Frontend   | Next.js 14 (App Router), TypeScript (strict), Tailwind CSS 3.4 |
| Backend    | Python 3.12, FastAPI, Pydantic v2, Uvicorn |
| Reasoning  | Gemini via the `google-genai` SDK (Vertex AI or Developer API) |
| Web search | Parallel Search API (`POST /v1beta/search`) |
| Streaming  | Server-Sent Events (in-process pub/sub, replay-on-subscribe) |
| Deploy     | Docker, Google Cloud Run, Secret Manager |
| Tests      | pytest, pytest-asyncio, httpx MockTransport |

## 6. Why Parallel is essential

The product is only trustworthy because its claims are grounded in the *live*
web at query time. Parallel is what makes that real: for each planned query it
returns actual pages with the excerpts the model cites from. Without Parallel
there is no evidence, no citations, and no defensible brief — just another model
guessing. Parallel materially enables the core value: **every figure and comp
links back to a page a producer can open and verify.**

## 7. How Gemini is used

Gemini does the reasoning at two points:

1. **Planning** — decomposes the brief into a set of targeted, category-tagged
   search queries (comparables, market, audience, competition, production,
   distribution, industry news), with a short rationale.
2. **Synthesis** — reads the retrieved evidence and produces the structured
   Studio Brief, constrained by a response schema and instructed to cite only
   the `S1..Sn` source ids it was given. Invalid citations are dropped and
   uncited claims discarded, so the output cannot fabricate a source.

Both paths degrade gracefully: if Gemini is unconfigured or a call fails, a
deterministic, film-aware fallback runs and the brief is labelled accordingly.

## 8. How Google Cloud Agent Builder is used

StudioOps runs on Google Cloud: Gemini is accessed through **Vertex AI**
(`GOOGLE_GENAI_USE_VERTEXAI=true` with a project and service-account
credentials), and the service is deployed on **Cloud Run** with credentials
supplied by **Secret Manager**. The agent workflow — decompose → invoke tools →
process results → produce an actionable artifact — is the agent-development layer
this build contributes.

> **Note:** binding the workflow to a managed Agent Builder / Agent Engine app
> is wired at deployment time, when the GCP project and credentials are
> provisioned. See [docs/gcp_integration.md](docs/gcp_integration.md) and
> [docs/deployment.md](docs/deployment.md).

## 9. Local setup

**Prerequisites:** Python 3.12+, Node.js 20+.

### Backend

```bash
python -m venv .venv
source .venv/bin/activate         # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env              # fill in keys when you have them
uvicorn backend.main:app --reload --port 8000
```

Health check: `curl http://localhost:8000/health` → `{"status":"ok"}`
Integration status: `curl http://localhost:8000/api/v1/config`

### Frontend

```bash
cd frontend
npm install
npm run dev                       # http://localhost:3000
```

In local dev the frontend proxies `/api` and `/reports` to the backend via
`next.config.mjs` (`BACKEND_ORIGIN`, default `http://127.0.0.1:8000`), so
everything runs from one origin with no CORS setup.

StudioOps runs **without any keys** — it will produce a fallback brief that is
clearly labelled. Add keys to make the research live.

## 10. Environment variables

Nothing is hard-coded; every integration is credential-driven. Copy
`.env.example` to `.env` for local use, and supply the same values via Secret
Manager in production.

### Backend

| Variable | Required | Purpose |
|----------|----------|---------|
| `PARALLEL_API_KEY` | for live search | Parallel Search API key (sent as `x-api-key`) |
| `PARALLEL_BASE_URL` | no | Override the Parallel base URL (default `https://api.parallel.ai`) |
| `GOOGLE_GENAI_USE_VERTEXAI` | for Vertex | `true` to use Vertex AI instead of the Developer API |
| `GOOGLE_CLOUD_PROJECT` | for Vertex | GCP project id |
| `GOOGLE_CLOUD_LOCATION` | no | Vertex region (default `us-central1`) |
| `GOOGLE_APPLICATION_CREDENTIALS` | for Vertex | Path to the service-account JSON |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | alt. for Vertex | Full SA JSON as a string; written to disk and wired automatically at startup |
| `GEMINI_API_KEY` / `GOOGLE_API_KEY` | for Developer API | Gemini Developer API key |
| `GEMINI_MODEL` | no | Model id (default `gemini-2.5-flash`) |
| `CORS_ALLOW_ORIGINS` | prod | Comma-separated allowed origins (default `*`) |
| `LOG_LEVEL` | no | Logging level (default `INFO`) |
| `PORT` | no | Bind port (Cloud Run injects this; default `8080`) |

### Frontend

| Variable | When | Purpose |
|----------|------|---------|
| `BACKEND_ORIGIN` | same-origin deploy | Backend the Next server proxies `/api` and `/reports` to |
| `NEXT_PUBLIC_API_BASE_URL` | split deploy | Public backend URL the browser calls directly (build-time) |

> **Secrets are never committed and never reach the browser.** `.env` and
> service-account files are git-ignored; API keys stay server-side. Use Secret
> Manager in production and rotate any key that is ever exposed.

## 11. Deployment

Both services containerize and run on Cloud Run. Full walkthrough — build, push,
Secret Manager wiring, and both same-origin and split-origin topologies — is in
**[docs/deployment.md](docs/deployment.md)**.

```bash
# Backend image (build from repo root)
docker build -f backend/Dockerfile -t studioops-api .

# Frontend image
docker build -f frontend/Dockerfile -t studioops-web ./frontend
```

## 12. Demo instructions

1. Start the backend and frontend (see Local setup), open http://localhost:3000.
2. Click an example pill — e.g. **Nigerian crime thriller** — or write your own
   brief, and press **Start Research →**.
3. Watch the live run: the four stages advance and each planned query appears in
   the *Live web research* panel with its real result count as it returns.
4. The **Studio Brief** opens automatically: executive summary, comparables,
   market signals, audience and competitive intelligence, opportunities, risks,
   next steps, an honest *What We Could Not Confirm* section, and the full
   **Sources** list. Every citation chip links to the page it came from.
5. **Download brief** exports the Markdown a producer can forward to a financier;
   JSON is also available. *How this brief was researched* expands the full plan
   and per-query trail.

The 30–60 second story: idea in → agent plans → live web searched → evidenced
brief out, fully cited.

## 13. Example production brief

**Input:**

> We're developing a Nigerian crime thriller set in Lagos. Research the current
> market, comparable films, audience trends, potential locations, distribution
> opportunities, and relevant production companies.

**Output (shape):** a Studio Brief titled *Lagos After Dark* with —

- an **executive summary** of the Nollywood crime opportunity,
- **comparable titles** with year/genre/market where the evidence stated them,
- **market signals** (e.g. streamer commissioning activity) with any figure the
  source actually gave and a trend indicator,
- **audience** and **competitive** intelligence,
- **production opportunities** and severity-rated **risks** with recommended
  actions,
- **next steps**, an honest list of **evidence gaps**, and a numbered **sources**
  list — each claim above carrying `[S1] [S2]` chips that open the source.

Every element is either backed by a retrieved source or explicitly flagged as
unconfirmed.

## 14. Testing

```bash
# From the repo root, with the venv active:
python -m pytest -q
```

The backend suite (pytest + pytest-asyncio, `httpx.MockTransport` for the
external APIs, `TestClient.stream()` for SSE) covers the Parallel and Gemini
clients, the planner/synthesizer including the anti-fabrication citation guard,
the evidence service, the workflow and run store, the API routes, the report
store, and the prompt contract.

Frontend type safety:

```bash
cd frontend
npm run typecheck     # tsc --noEmit
npm run build         # production build
```

---

### Security notes

- Never commit `PARALLEL_API_KEY`, Gemini keys, or service-account JSON. `.env`
  and credential files are git-ignored; only `.env.example` is tracked.
- API keys are used server-side only and are never sent to the browser.
- Raw stack traces and credentials are never surfaced to users; the API returns
  generic messages and logs details server-side.
- StudioOps never fabricates statistics, people, companies, quotes, URLs, or
  citations. Unsupported findings are reported as gaps.

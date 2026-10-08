# DeployMate AI

An AI implementation copilot for forward-deployed engineers. Give it a customer brief, an OpenAPI spec and sample data, and it produces requirements, open questions, a field mapping, an architecture, an implementation plan, a test plan, a risk register and a customer handoff document. Every claim is marked as a **fact**, an **assumption** or **unknown**, so nothing invented reaches the customer looking like a fact.

## Run it

**Everything in Docker** (PostgreSQL with pgvector, the API, the built frontend):

```bash
docker compose up --build        # http://localhost:8080
```

**Local development:**

```bash
python -m venv .venv && .venv/Scripts/activate      # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.api.main:app --port 8000 --reload   # SQLite by default

cd frontend && npm install && npm run dev            # http://localhost:5173
```

In the app: **New Customer → Load demo customer** (or paste your own brief and attach a JSON/YAML OpenAPI spec and a JSON/CSV sample) → **Create customer** → **Run pipeline**. Press **Ctrl K** anywhere for the command palette.

## How the agents get their answers

Each of the seven agents tries three sources in order:

1. **Live:** a free hosted model through any OpenAI-compatible endpoint (default: OpenRouter), when `LLM_API_KEY` is set. Output is validated against the agent's Pydantic schema; invalid output falls through.
2. **Recorded:** curated outputs for the built-in demo customer only. A customer whose inputs differ in any way never sees them.
3. **Offline:** rule-based agents (`backend/agents/heuristics.py`) that work for any customer with no key.

Whatever the source, systems and endpoints come only from the supplied inputs, never from a model. The critic then checks everything against the inputs.

| Variable | Purpose |
|---|---|
| `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL` | Free model access; empty key means offline agents |
| `DATABASE_URL` | SQLite by default; Postgres in compose |
| `POSTGRES_PASSWORD` | Compose database password (a local-only default is used if unset) |
| `CORS_ORIGINS` | Origins allowed to call the API directly |

## Architecture

```
brief + spec + sample
  └─► Requirements ─► Clarification ─► Integration ─► Architecture ─► Validation ─► Critic ─► Handoff
                     (LangGraph; agents share one Pydantic PipelineState)
```

| Path | What it holds |
|---|---|
| `backend/schemas/models.py` | Shared state. A `fact` without a `source` fails validation |
| `backend/integrations/parsers.py` | OpenAPI (JSON/YAML, `$ref`-aware) and sample (JSON/CSV) parsing |
| `backend/integrations/patterns.py` | Integration-pattern library with a vector index: pgvector cosine search on Postgres, in-process on SQLite. Holds no customer data |
| `backend/agents/` | The seven agents, the fallback chain and the offline heuristics |
| `backend/api/` | FastAPI. Every query is scoped by `customer_id`; pipeline progress streams as server-sent events; an append-only `decision_log` table keeps every decision across runs; the handoff needs explicit human approval |
| `backend/evaluation/` | 40 synthetic cases and the metrics below |
| `frontend/` | React, TypeScript, Tailwind v4 with the PRD design tokens. Four lazy-loaded React Three Fiber scenes (system graph, pipeline in depth with GSAP camera moves, layered architecture with security-boundary volumes, field-mapping columns). Each scene has a list view and a static 2D fallback under `prefers-reduced-motion` |
| `infrastructure/` | Dockerfiles and the nginx config |

## Tests and evaluation

```bash
python -m pytest -q
python -m backend.evaluation.run_eval     # writes generated/eval_report.json; also on the Evaluation page
```

The evaluation scores the offline agents on 40 synthetic cases (10 integration domains × 4 brief variants):

| Metric | Score |
|---|---|
| Requirement extraction precision / recall | 100% / 100% |
| Missing-question recall | 100% |
| Mapping accuracy | 100% |
| Architecture validity | 100% |
| Test-case coverage | 100% |
| Pattern retrieval, top-1 | 47.5% |
| Critic accuracy on planted violations | 100% |
| Human reviewer score | not measured |

Read these with care: the synthetic cases were written alongside the offline agents, so the 100% scores are optimistic for real briefs. Pattern retrieval is the honest weak spot. Briefs that do not say how data should flow are genuinely ambiguous, and the decision log flags those as weak matches.

CI runs the tests and the evaluation (failing on guardrail regressions), builds the frontend, then starts the full compose stack and smoke-tests it through nginx.

## Not done yet

- **Cloud deploy.** The compose stack is ready for any container host, but nothing has been deployed: that needs your cloud account.
- **21st.dev components.** The 21st.dev MCP server was not connected, so the UI uses hand-built primitives re-themed to the PRD tokens (the PRD's fallback in section 10.4). They can be swapped for catalog components once `API_KEY_21ST` is set.
- **Live-model quality.** The free-model path is implemented and schema-validated, but it has not been evaluated against a real key.

# DeployMate AI

An AI implementation copilot for forward-deployed engineers. It turns a customer brief, an OpenAPI spec and sample data into requirements, open questions, a data mapping, an architecture, an implementation plan, a test plan, a risk register and a customer handoff document. A 3D system graph fills in as each agent stage completes.

This repository is the **vertical demo slice** of the PRD (`PRD.2.md`): one fictional customer (Northwind Outfitters, order platform to fulfillment system), every layer working end to end.

## Run it

```bash
# backend (Python 3.12+)
python -m venv .venv
.venv/Scripts/activate        # Windows; use .venv/bin/activate on macOS/Linux
pip install -r requirements.txt
uvicorn backend.api.main:app --port 8000

# frontend (Node 22)
cd frontend
npm install
npm run dev                   # http://localhost:5173
```

In the app: **New Customer → Load demo customer → Next → Next → Create customer**, then **Run pipeline** on Discovery. Every other page fills in from that run.

## LLM: free model, offline by default

The agents call any OpenAI-compatible endpoint. The default is a free model on OpenRouter.

| Variable | Default |
|---|---|
| `LLM_API_KEY` | empty, which replays cached outputs from `examples/demo_customer/cache/` |
| `LLM_BASE_URL` | `https://openrouter.ai/api/v1` |
| `LLM_MODEL` | `meta-llama/llama-3.3-70b-instruct:free` |

Copy `.env.example` to `.env` and set the variables in your shell. If a live call fails, the agent falls back to the cache, so the demo always runs. The sidebar shows which mode is active.

## How it works

```
brief ─► Requirements ─► Clarification ─► Integration ─► Architecture ─► Validation ─► Critic ─► Handoff
                     (LangGraph, shared Pydantic PipelineState)
```

- `backend/schemas/models.py` holds the shared state. Every claim carries `provenance: fact | assumption | unknown`, and a `fact` without a `source` fails validation.
- `backend/integrations/parsers.py` parses the OpenAPI spec and sample JSON deterministically. Only endpoints found there become facts.
- `backend/agents/stages.py` has the seven agents. The critic is rule-based: it flags invented endpoints, unsourced mapping facts, broken task dependencies and untested requirements.
- `backend/api/` is FastAPI with SQLite storage. Every read and write is scoped by `customer_id`, `POST /customers/{id}/run` streams stage progress as server-sent events, and the handoff needs `POST /customers/{id}/handoff/approve` before it is marked approved.
- Every agent appends to a decision log, which is shown on the Handoff page.
- `frontend/` is Vite, React, TypeScript and Tailwind v4, with the PRD design tokens in `src/index.css`. The 3D scene is React Three Fiber, lazy-loaded. With `prefers-reduced-motion` it switches to a static 2D diagram, and a list view is available as well.

## Tests and evaluation

```bash
python -m pytest -q
python -m backend.evaluation.run_eval   # writes generated/eval_report.json
```

## Not in this slice

These are the next sub-projects: the pipeline, architecture and mapping 3D scenes, the 30–50 case evaluation set, Postgres with pgvector, Docker and cloud deploy, and installing 21st.dev catalog components (the UI uses hand-built primitives that can be swapped for catalog components later, as PRD 10.4 allows).

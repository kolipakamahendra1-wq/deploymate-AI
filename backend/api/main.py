from __future__ import annotations

import json
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, StreamingResponse
from pydantic import BaseModel

from ..agents.graph import STAGE_NAMES, run_pipeline
from ..agents.llm import live_enabled, model_name, provider
from ..integrations.parsers import load_openapi, load_sample
from ..integrations.patterns import PATTERNS
from ..schemas.models import PipelineState
from . import store

ROOT = Path(__file__).resolve().parents[2]
DEMO = ROOT / "examples" / "demo_customer"
EVAL_REPORT = ROOT / "generated" / "eval_report.json"

app = FastAPI(title="DeployMate AI")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173").split(","),
    allow_methods=["*"], allow_headers=["*"],
)

SECTIONS = {
    "requirements": "requirements", "questions": "questions", "systems": "systems",
    "endpoints": "endpoints", "mapping": "mappings", "architecture": "architecture",
    "plan": "plan", "risks": "risks", "tests": "tests", "handoff": "handoff",
    "decisions": "decisions", "critic": "critic_notes", "patterns": "patterns",
}


class NewCustomer(BaseModel):
    name: str
    brief: str
    openapi: dict | str | None = None  # dict, or JSON / YAML text
    sample: dict | list | str | None = None  # JSON data, or JSON / CSV text


def _get(cid: str) -> PipelineState:
    state = store.load(cid)
    if not state:
        raise HTTPException(404, "customer not found")
    return state


def _demo() -> dict:
    return {
        "name": "Northwind Outfitters",
        "brief": (DEMO / "brief.txt").read_text(encoding="utf-8").strip(),
        "openapi": json.loads((DEMO / "order_platform.openapi.json").read_text(encoding="utf-8")),
        "sample": json.loads((DEMO / "fulfillment_sample.json").read_text(encoding="utf-8")),
    }


@app.get("/health")
def health():
    return {"ok": True, "llm": "live" if live_enabled() else "offline", "provider": provider(),
            "model": model_name(), "stages": STAGE_NAMES}


@app.get("/demo")
def demo_input():
    return _demo()


@app.post("/customers")
def create(body: NewCustomer):
    if not body.name.strip() or not body.brief.strip():
        raise HTTPException(422, "name and brief are required")
    try:
        openapi, sample = load_openapi(body.openapi), load_sample(body.sample)
    except (ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(422, f"could not parse attachment: {exc}") from exc
    demo = _demo()
    # Recorded outputs apply only to the exact demo inputs, never to a real customer.
    is_demo = body.brief.strip() == demo["brief"] and openapi == demo["openapi"] and sample == demo["sample"]
    state = PipelineState(customer_id="", brief=body.brief.strip(), openapi=openapi, sample=sample,
                          fixture="demo_customer" if is_demo else None)
    return {"id": store.create_customer(body.name.strip(), state)}


@app.get("/customers")
def customers():
    return store.list_customers()


@app.get("/customers/{cid}")
def get_customer(cid: str):
    s = _get(cid)
    return {"id": cid, "completed_stages": s.completed_stages, "stages": STAGE_NAMES,
            "brief": s.brief, "has_spec": s.openapi is not None, "has_sample": s.sample is not None,
            "recorded_demo": s.fixture is not None}


@app.post("/customers/{cid}/run")
def run(cid: str):
    prev = _get(cid)
    # Each run starts from the customer's inputs only.
    state = PipelineState(customer_id=cid, brief=prev.brief, openapi=prev.openapi,
                          sample=prev.sample, fixture=prev.fixture)
    run_no = store.next_run(cid)

    def events():
        try:
            for stage, st in run_pipeline(state):
                store.save(st, run=run_no)
                yield f"data: {json.dumps({'stage': stage, 'done': st.completed_stages})}\n\n"
            yield 'data: {"finished": true}\n\n'
        except Exception as exc:  # noqa: BLE001 - surface any agent failure to the UI
            yield f"data: {json.dumps({'error': str(exc)})}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")


@app.get("/customers/{cid}/handoff.md", response_class=PlainTextResponse)
def handoff_md(cid: str):
    return _get(cid).handoff.markdown


@app.get("/customers/{cid}/decision-log")
def decision_log(cid: str):
    _get(cid)
    return store.decision_log(cid)


@app.post("/customers/{cid}/handoff/approve")
def approve(cid: str):
    s = _get(cid)
    if "handoff" not in s.completed_stages:
        raise HTTPException(409, "run the pipeline first")
    s.handoff.approved = True
    store.save(s)
    return s.handoff


@app.get("/customers/{cid}/{section}")
def section(cid: str, section: str):
    if section not in SECTIONS:
        raise HTTPException(404, "unknown section")
    return getattr(_get(cid), SECTIONS[section])


@app.get("/patterns")
def patterns():
    return [{k: p[k] for k in ("id", "name", "summary")} for p in PATTERNS]


@app.get("/evaluation")
def evaluation():
    if not EVAL_REPORT.exists():
        raise HTTPException(404, "no evaluation report yet; POST /evaluation/run")
    return json.loads(EVAL_REPORT.read_text(encoding="utf-8"))


@app.post("/evaluation/run")
def evaluation_run():
    from ..evaluation.run_eval import main as run_eval

    return run_eval(write=True, quiet=True)

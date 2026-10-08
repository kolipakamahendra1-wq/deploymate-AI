from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, StreamingResponse
from pydantic import BaseModel

from ..agents.graph import STAGE_NAMES, run_pipeline
from ..agents.llm import live_enabled
from ..schemas.models import PipelineState
from . import store

DEMO = Path(__file__).resolve().parents[2] / "examples" / "demo_customer"

app = FastAPI(title="DeployMate AI")
app.add_middleware(
    CORSMiddleware, allow_origins=["http://localhost:5173"], allow_methods=["*"], allow_headers=["*"]
)

SECTIONS = {
    "requirements": "requirements", "questions": "questions", "systems": "systems",
    "endpoints": "endpoints", "mapping": "mappings", "architecture": "architecture",
    "plan": "plan", "risks": "risks", "tests": "tests", "handoff": "handoff",
    "decisions": "decisions", "critic": "critic_notes",
}


class NewCustomer(BaseModel):
    name: str
    brief: str
    openapi: dict | None = None
    sample: dict | list | None = None


def _get(cid: str) -> PipelineState:
    state = store.load(cid)
    if not state:
        raise HTTPException(404, "customer not found")
    return state


@app.get("/health")
def health():
    return {"ok": True, "llm": "live" if live_enabled() else "cache", "stages": STAGE_NAMES}


@app.get("/demo")
def demo_input():
    return {
        "name": "Northwind Outfitters",
        "brief": (DEMO / "brief.txt").read_text(encoding="utf-8").strip(),
        "openapi": json.loads((DEMO / "order_platform.openapi.json").read_text(encoding="utf-8")),
        "sample": json.loads((DEMO / "fulfillment_sample.json").read_text(encoding="utf-8")),
    }


@app.post("/customers")
def create(body: NewCustomer):
    state = PipelineState(customer_id="", brief=body.brief, openapi=body.openapi, sample=body.sample)
    return {"id": store.create_customer(body.name, state)}


@app.get("/customers")
def customers():
    return store.list_customers()


@app.get("/customers/{cid}")
def get_customer(cid: str):
    s = _get(cid)
    return {"id": cid, "completed_stages": s.completed_stages, "stages": STAGE_NAMES}


@app.post("/customers/{cid}/run")
def run(cid: str):
    state = _get(cid)

    def events():
        try:
            for stage, st in run_pipeline(state):
                store.save(st)
                yield f"data: {json.dumps({'stage': stage, 'done': st.completed_stages})}\n\n"
            yield 'data: {"finished": true}\n\n'
        except Exception as exc:  # noqa: BLE001
            yield f"data: {json.dumps({'error': str(exc)})}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")


@app.get("/customers/{cid}/handoff.md", response_class=PlainTextResponse)
def handoff_md(cid: str):
    return _get(cid).handoff.markdown


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

import json
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

os.environ.pop("LLM_API_KEY", None)
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from backend.agents.graph import run_pipeline  # noqa: E402
from backend.agents.stages import critic_agent  # noqa: E402
from backend.api import store  # noqa: E402
from backend.api.main import app  # noqa: E402
from backend.schemas.models import Endpoint, PipelineState, Provenance, Requirement  # noqa: E402

DEMO = Path(__file__).resolve().parents[1] / "examples" / "demo_customer"


def demo_state():
    return PipelineState(
        customer_id="t",
        brief=(DEMO / "brief.txt").read_text(encoding="utf-8"),
        openapi=json.loads((DEMO / "order_platform.openapi.json").read_text(encoding="utf-8")),
        sample=json.loads((DEMO / "fulfillment_sample.json").read_text(encoding="utf-8")),
    )


def test_fact_requires_source():
    with pytest.raises(ValueError):
        Requirement(id="R", text="x", kind="functional", provenance=Provenance.fact)


def test_pipeline_runs_offline_and_produces_artifacts():
    final = None
    for _, final in run_pipeline(demo_state()):
        pass
    assert len(final.completed_stages) == 7
    assert final.requirements and final.questions and final.mappings
    assert final.architecture.mermaid.startswith("flowchart")
    assert final.handoff.requires_human_review and not final.handoff.approved
    assert any(not s.confirmed for s in final.systems)
    assert len(final.decisions) >= 7
    assert not [n for n in final.critic_notes if n.severity == "error"]


def test_critic_catches_invented_endpoint():
    s = demo_state()
    s.endpoints = [Endpoint(system_id="order", method="POST", path="/refunds",
                            provenance=Provenance.fact, source="openapi:POST /refunds")]
    notes = critic_agent(s)["critic_notes"]
    assert any("Invented endpoint" in n.message for n in notes)


def test_api_end_to_end_and_isolation():
    store.reset_engine()
    c = TestClient(app)
    demo = c.get("/demo").json()
    a = c.post("/customers", json=demo).json()["id"]
    b = c.post("/customers", json=demo).json()["id"]
    c.post(f"/customers/{a}/run")
    assert len(c.get(f"/customers/{a}/requirements").json()) > 0
    assert c.get(f"/customers/{b}/requirements").json() == []
    assert c.get("/customers/nope/requirements").status_code == 404
    assert c.post(f"/customers/{b}/handoff/approve").status_code == 409
    assert c.post(f"/customers/{a}/handoff/approve").json()["approved"] is True

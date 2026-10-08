import json
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

os.environ.pop("LLM_API_KEY", None)
os.environ.pop("LLM_PROVIDER", None)
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from backend.agents import heuristics as h  # noqa: E402
from backend.agents.graph import run_pipeline  # noqa: E402
from backend.agents.stages import critic_agent  # noqa: E402
from backend.api import store  # noqa: E402
from backend.api.main import app  # noqa: E402
from backend.integrations.parsers import load_openapi, load_sample, parse_openapi  # noqa: E402
from backend.integrations.patterns import search  # noqa: E402
from backend.schemas.models import Endpoint, PipelineState, Provenance, Requirement, Task  # noqa: E402

DEMO = Path(__file__).resolve().parents[1] / "examples" / "demo_customer"


def demo_state(fixture=None):
    return PipelineState(
        customer_id="t",
        brief=(DEMO / "brief.txt").read_text(encoding="utf-8"),
        openapi=json.loads((DEMO / "order_platform.openapi.json").read_text(encoding="utf-8")),
        sample=json.loads((DEMO / "fulfillment_sample.json").read_text(encoding="utf-8")),
        fixture=fixture,
    )


def final(state):
    out = state
    for _, out in run_pipeline(state):
        pass
    return out


@pytest.fixture()
def client():
    store.reset_engine()
    return TestClient(app)


# ---------------------------------------------------------------- guardrails

def test_fact_requires_source():
    with pytest.raises(ValueError):
        Requirement(id="R", text="x", kind="functional", provenance=Provenance.fact)


@pytest.mark.parametrize("fixture", [None, "demo_customer"])
def test_pipeline_produces_all_artifacts(fixture):
    st = final(demo_state(fixture))
    assert len(st.completed_stages) == 7
    assert st.requirements and st.questions and st.mappings and st.plan and st.tests
    assert st.architecture.mermaid.startswith("flowchart")
    assert st.handoff.requires_human_review and not st.handoff.approved
    assert [s.name for s in st.systems] == ["Order Platform", "Fulfillment System"]
    assert not st.systems[1].confirmed  # only a sample exists for fulfillment
    assert not [n for n in st.critic_notes if n.severity == "error"]


def test_offline_agents_never_mark_unsupported_claims_as_fact():
    st = final(demo_state())
    fields = set(parse_openapi(st.openapi)["fields"]) | set(st.sample)
    for m in st.mappings:
        if m.provenance == Provenance.fact:
            assert m.source_field == m.target_field or {m.source_field, m.target_field} <= fields
    assert all(e.source.startswith("openapi:") for e in st.endpoints)


def test_critic_catches_invented_endpoint_and_cycle():
    s = final(demo_state())
    bad = s.model_copy(update={
        "endpoints": [Endpoint(system_id="x", method="POST", path="/refunds", provenance=Provenance.fact,
                               source="openapi:POST /refunds")],
        "plan": s.plan + [Task(id="A", title="a", depends_on=["B"]), Task(id="B", title="b", depends_on=["A"])],
    })
    msgs = [n.message for n in critic_agent(bad)["critic_notes"]]
    assert any("Invented endpoint" in m for m in msgs)
    assert any("cycle" in m for m in msgs)


# ---------------------------------------------------------------- parsing and heuristics

def test_yaml_openapi_and_csv_sample():
    spec = load_openapi("openapi: 3.0.0\ninfo: {title: Acme CRM}\npaths:\n  /contacts: {get: {}}\n"
                        "components:\n  schemas:\n    Contact:\n      properties: {email: {}, phone: {}}\n")
    assert parse_openapi(spec)["fields"] == ["email", "phone"]
    assert load_sample("email_address,tel\na@b.c,123\n") == [{"email_address": "a@b.c", "tel": "123"}]
    with pytest.raises(ValueError):
        load_openapi("just: yaml")


def test_field_mapping_uses_synonyms():
    assert h.field_score("customer_email", "recipient_email") >= 0.9
    assert h.field_score("qty", "quantity") >= 0.9
    assert h.field_score("currency", "ship_to") < 0.35


def test_system_detection():
    assert h.detect_system_names("Sync our Shopify store with the NetSuite ERP.") == ["Shopify Store", "NetSuite ERP"]
    # "the ledger" is an accounting concept here, not a third system
    assert h.detect_system_names("Sync our CRM with our billing system so sales are booked in the ledger.") == ["CRM", "Billing System"]


def test_pattern_retrieval():
    assert search("A legacy system drops a CSV file on SFTP every night")[0]["id"] == "file-drop"
    assert search("nightly batch load into the data warehouse for reporting")[0]["id"] == "batch-etl"


# ---------------------------------------------------------------- API

def test_new_customer_never_gets_demo_recordings(client):
    demo = client.get("/demo").json()
    other = {**demo, "name": "Other Co", "brief": "We need to connect our CRM to our billing system."}
    cid = client.post("/customers", json=other).json()["id"]
    assert client.get(f"/customers/{cid}").json()["recorded_demo"] is False
    client.post(f"/customers/{cid}/run")
    log = client.get(f"/customers/{cid}/decision-log").json()
    assert all("(recorded)" not in d["decision"] for d in log)
    assert {s["name"] for s in client.get(f"/customers/{cid}/systems").json()} == {"CRM", "Billing System"}


def test_api_end_to_end_isolation_and_audit(client):
    demo = client.get("/demo").json()
    a = client.post("/customers", json=demo).json()["id"]
    b = client.post("/customers", json=demo).json()["id"]
    assert client.get(f"/customers/{a}").json()["recorded_demo"] is True
    client.post(f"/customers/{a}/run")
    client.post(f"/customers/{a}/run")  # a re-run starts from the inputs again
    assert client.get(f"/customers/{a}").json()["completed_stages"].count("handoff") == 1
    assert len(client.get(f"/customers/{a}/requirements").json()) > 0
    assert client.get(f"/customers/{b}/requirements").json() == []
    log = client.get(f"/customers/{a}/decision-log").json()
    assert {d["run"] for d in log} == {1, 2}
    assert client.get(f"/customers/{b}/decision-log").json() == []
    assert client.get("/customers/nope/requirements").status_code == 404
    assert client.post(f"/customers/{b}/handoff/approve").status_code == 409
    assert client.post(f"/customers/{a}/handoff/approve").json()["approved"] is True


def test_rejects_bad_attachment(client):
    r = client.post("/customers", json={"name": "X", "brief": "We need a sync.", "openapi": "not: openapi"})
    assert r.status_code == 422

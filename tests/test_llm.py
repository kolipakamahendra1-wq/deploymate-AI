import json

import httpx
import pytest

from backend.agents import llm
from backend.agents.stages import RequirementsOut
from backend.schemas.models import Provenance, Requirement


class FakeResponse:
    def __init__(self, payload: dict, status: int = 200):
        self._payload, self.status_code = payload, status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("boom", request=httpx.Request("POST", "http://x"), response=None)

    def json(self):
        return self._payload


@pytest.fixture()
def ollama(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("OLLAMA_MODEL", "test-model")
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    calls = []

    def fake_post(url, json=None, **_):
        calls.append((url, json))
        content = {"requirements": [
            {"id": "R1", "text": "Sync orders", "kind": "functional", "provenance": "fact", "source": "brief"},
            {"id": "R2", "text": "Guessed SLA", "kind": "non-functional", "provenance": "fact"},  # no source
        ]}
        return FakeResponse({"message": {"content": __import__("json").dumps(content)}})

    monkeypatch.setattr(llm.httpx, "post", fake_post)
    return calls


def offline():
    return RequirementsOut(requirements=[Requirement(id="X", text="offline", kind="functional")])


def test_ollama_sends_schema_as_format_and_downgrades_unsourced_facts(ollama):
    out, mode = llm.run_agent("requirements", "sys", "user", RequirementsOut, None, offline)
    url, body = ollama[0]
    assert url.endswith("/api/chat") and body["model"] == "test-model" and body["stream"] is False
    assert body["format"]["title"] == "RequirementsOut"
    assert mode == "live (test-model)"
    assert out.requirements[0].provenance == Provenance.fact
    assert out.requirements[1].provenance == Provenance.assumption  # guardrail applied to model output


def test_live_failure_falls_back_and_says_why(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "ollama")

    def down(*_, **__):
        raise httpx.ConnectError("refused")

    monkeypatch.setattr(llm.httpx, "post", down)
    out, mode = llm.run_agent("requirements", "s", "u", RequirementsOut, None, offline)
    assert out.requirements[0].id == "X" and mode == "offline; live call failed: ConnectError"
    out, mode = llm.run_agent("requirements", "s", "u", RequirementsOut, "demo_customer", offline)
    assert mode.startswith("recorded") and out.requirements[0].id == "R1"


def test_provider_selection(monkeypatch):
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    assert llm.provider() is None
    monkeypatch.setenv("LLM_API_KEY", "k")
    assert llm.provider() == "openai"
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    assert llm.provider() == "ollama" and llm.model_name() == "qwen2.5:3b"


def test_sanitize_never_upgrades():
    data = {"a": [{"provenance": "assumption"}, {"provenance": "fact", "source": "brief"}, {"provenance": "fact"}]}
    assert [x["provenance"] for x in llm._sanitize(data)["a"]] == ["assumption", "fact", "assumption"]
    assert json.dumps(data)  # input untouched

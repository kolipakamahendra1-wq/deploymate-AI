"""LLM access with a three-step fallback chain.

1. live: a free model. LLM_PROVIDER selects it:
     ollama  - a local or self-hosted Ollama server (default model qwen2.5:3b).
               Uses Ollama's structured outputs: the agent's JSON Schema is
               passed as `format`, so generation is constrained to the schema.
     openai  - any OpenAI-compatible endpoint (for example OpenRouter).
   Output is then validated against the agent's Pydantic schema.
2. recorded: the demo customer's recorded outputs, used only for a state
   whose `fixture` names them. Never used for other customers.
3. offline: the rule-based heuristic agent.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Callable, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "examples"

M = TypeVar("M", bound=BaseModel)


def provider() -> str | None:
    """The configured live provider, or None for offline-only operation."""
    p = os.getenv("LLM_PROVIDER", "").strip().lower()
    if p in ("ollama", "openai"):
        return p
    if os.getenv("LLM_API_KEY"):  # backwards compatible: a key alone means an OpenAI-compatible endpoint
        return "openai"
    return None


def live_enabled() -> bool:
    return provider() is not None


def model_name() -> str | None:
    p = provider()
    if p == "ollama":
        return os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
    if p == "openai":
        return os.getenv("LLM_MODEL", "meta-llama/llama-3.3-70b-instruct:free")
    return None


def _timeout() -> float:
    # CPU-only Ollama hosts can take minutes on the first call while the model loads.
    return float(os.getenv("LLM_TIMEOUT", "600" if provider() == "ollama" else "120"))


def _extract_json(text: str) -> dict:
    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        raise ValueError("no JSON object in model output")
    return json.loads(match.group(0))


def _sanitize(node: Any) -> Any:
    """Enforce the guardrail on model output: an unsourced 'fact' becomes an 'assumption'.

    Claims are only ever downgraded, never upgraded.
    """
    if isinstance(node, dict):
        out = {k: _sanitize(v) for k, v in node.items()}
        if out.get("provenance") == "fact" and not out.get("source"):
            out["provenance"] = "assumption"
        return out
    if isinstance(node, list):
        return [_sanitize(v) for v in node]
    return node


def _ollama(system: str, user: str, schema: type[BaseModel]) -> dict:
    resp = httpx.post(
        os.getenv("OLLAMA_URL", "http://localhost:11434").rstrip("/") + "/api/chat",
        json={
            "model": model_name(),
            "stream": False,
            "format": schema.model_json_schema(),
            "options": {"temperature": 0, "num_ctx": int(os.getenv("OLLAMA_NUM_CTX", "8192"))},
            "keep_alive": os.getenv("OLLAMA_KEEP_ALIVE", "5m"),
            "messages": [
                {"role": "system", "content": f"{system}\nReply with JSON matching the given schema."},
                {"role": "user", "content": user},
            ],
        },
        timeout=_timeout(),
    )
    resp.raise_for_status()
    return json.loads(resp.json()["message"]["content"])


def _openai(system: str, user: str, schema: type[BaseModel]) -> dict:
    headers = {"Authorization": f"Bearer {os.environ['LLM_API_KEY']}"} if os.getenv("LLM_API_KEY") else {}
    resp = httpx.post(
        os.getenv("LLM_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/") + "/chat/completions",
        headers=headers,
        json={
            "model": model_name(),
            "temperature": 0,
            "messages": [
                {"role": "system", "content": (
                    f"{system}\nReply with one JSON object only, matching this JSON Schema:\n"
                    f"{json.dumps(schema.model_json_schema())}")},
                {"role": "user", "content": user},
            ],
        },
        timeout=_timeout(),
    )
    resp.raise_for_status()
    return _extract_json(resp.json()["choices"][0]["message"]["content"])


def run_agent(
    agent: str, system: str, user: str, schema: type[M], fixture: str | None,
    offline: Callable[[], M], accept: Callable[[M], str | None] | None = None,
) -> tuple[M, str]:
    """Return (validated output, mode). Mode is 'live (<model>)', 'recorded' or 'offline'.

    `accept` checks a live answer beyond its schema and returns a reason to reject it.
    When a live answer fails or is rejected, the mode says why, so the decision log
    records the fallback.
    """
    note = ""
    p = provider()
    if p:
        try:
            raw = (_ollama if p == "ollama" else _openai)(system, user, schema)
            out = schema.model_validate(_sanitize(raw))
            problem = accept(out) if accept else None
            if not problem:
                return out, f"live ({model_name()})"
            note = f"; live answer rejected: {problem}"
        except (httpx.HTTPError, ValueError, ValidationError, KeyError) as exc:
            note = f"; live call failed: {type(exc).__name__}"
    if fixture:
        path = FIXTURES / fixture / "cache" / f"{agent}.json"
        if path.exists():
            return schema.model_validate_json(path.read_text(encoding="utf-8")), "recorded" + note
    return offline(), "offline" + note

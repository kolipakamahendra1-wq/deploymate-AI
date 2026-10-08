"""LLM access with a three-step fallback chain.

1. live: a free hosted model via any OpenAI-compatible endpoint (default
   OpenRouter), when LLM_API_KEY is set. Output is validated against the
   agent's Pydantic schema.
2. recorded: the demo customer's recorded outputs, used only for a state
   whose `fixture` names them. Never used for other customers.
3. offline: the rule-based heuristic agent.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Callable, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "examples"
DEFAULT_MODEL = "meta-llama/llama-3.3-70b-instruct:free"

M = TypeVar("M", bound=BaseModel)


def live_enabled() -> bool:
    return bool(os.getenv("LLM_API_KEY"))


def _extract_json(text: str) -> dict:
    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        raise ValueError("no JSON object in model output")
    return json.loads(match.group(0))


def _live(system: str, user: str, schema: type[BaseModel]) -> dict:
    resp = httpx.post(
        os.getenv("LLM_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/") + "/chat/completions",
        headers={"Authorization": f"Bearer {os.environ['LLM_API_KEY']}"},
        json={
            "model": os.getenv("LLM_MODEL", DEFAULT_MODEL),
            "temperature": 0,
            "messages": [
                {"role": "system", "content": (
                    f"{system}\nReply with one JSON object only, matching this JSON Schema:\n"
                    f"{json.dumps(schema.model_json_schema())}")},
                {"role": "user", "content": user},
            ],
        },
        timeout=90,
    )
    resp.raise_for_status()
    return _extract_json(resp.json()["choices"][0]["message"]["content"])


def run_agent(
    agent: str, system: str, user: str, schema: type[M], fixture: str | None,
    offline: Callable[[], M],
) -> tuple[M, str]:
    """Return (validated output, mode) where mode is live, recorded or offline."""
    if live_enabled():
        try:
            return schema.model_validate(_live(system, user, schema)), "live"
        except (httpx.HTTPError, ValueError, ValidationError, KeyError):
            pass  # degrade to the next source
    if fixture:
        path = FIXTURES / fixture / "cache" / f"{agent}.json"
        if path.exists():
            return schema.model_validate_json(path.read_text(encoding="utf-8")), "recorded"
    return offline(), "offline"

"""LLM access: free hosted model when LLM_API_KEY is set, else offline cache replay.

The provider is any OpenAI-compatible endpoint (default: OpenRouter with a free
model), configured through LLM_BASE_URL / LLM_MODEL. Any live failure falls
back to the cached fixture so the demo always runs.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = Path(os.getenv("DEMO_CACHE_DIR", ROOT / "examples" / "demo_customer" / "cache"))
DEFAULT_MODEL = "meta-llama/llama-3.3-70b-instruct:free"


def live_enabled() -> bool:
    return bool(os.getenv("LLM_API_KEY"))


def _extract_json(text: str) -> dict:
    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        raise ValueError("no JSON object in model output")
    return json.loads(match.group(0))


def complete_json(agent: str, system: str, user: str) -> tuple[dict, str]:
    """Return (payload, mode) where mode is 'live' or 'cache'."""
    if live_enabled():
        try:
            resp = httpx.post(
                os.getenv("LLM_BASE_URL", "https://openrouter.ai/api/v1") + "/chat/completions",
                headers={"Authorization": f"Bearer {os.environ['LLM_API_KEY']}"},
                json={
                    "model": os.getenv("LLM_MODEL", DEFAULT_MODEL),
                    "messages": [
                        {"role": "system", "content": system + "\nReply with a single JSON object only."},
                        {"role": "user", "content": user},
                    ],
                },
                timeout=60,
            )
            resp.raise_for_status()
            return _extract_json(resp.json()["choices"][0]["message"]["content"]), "live"
        except Exception:  # noqa: BLE001 - any failure degrades to the cache
            pass
    path = CACHE_DIR / f"{agent}.json"
    if not path.exists():
        raise RuntimeError(f"No LLM key set and no cached output for agent '{agent}'")
    return json.loads(path.read_text(encoding="utf-8")), "cache"

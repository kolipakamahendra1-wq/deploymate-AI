"""Built-in library of integration patterns and a vector index over it.

The index stores pattern embeddings in PostgreSQL with pgvector when available
(cosine distance via the `<=>` operator) and falls back to an in-process cosine
search on SQLite. It only ever holds this shared library, never customer data,
so retrieval cannot leak one customer's material into another's run.
"""
from __future__ import annotations

import hashlib
import math
import re

from sqlalchemy import text

from .. import db

DIM = 256

PATTERNS = [
    {"id": "webhook-queue", "shape": "event", "name": "Webhook + queue",
     "summary": "Source pushes events to a receiver; a queue absorbs spikes; an adapter writes to the target with retries.",
     "keywords": "webhook event push paid order created real time spike promotion queue retry notify immediately"},
    {"id": "polling-sync", "shape": "poll", "name": "Scheduled polling sync",
     "summary": "Integration polls the source API for changes since a watermark and syncs them to the target.",
     "keywords": "poll polled polling no webhooks watermark updated_at list endpoint pull periodically"},
    {"id": "batch-etl", "shape": "batch", "name": "Nightly batch ETL",
     "summary": "A scheduler extracts a batch, stages it, transforms and loads it into the target, with replay.",
     "keywords": "nightly batch daily hourly report warehouse load export bulk etl analytics schedule"},
    {"id": "file-drop", "shape": "file", "name": "File drop over SFTP",
     "summary": "Source exports CSV files to SFTP; a watcher validates and loads each file.",
     "keywords": "csv file export sftp ftp upload spreadsheet legacy flat file drop folder"},
    {"id": "cdc", "shape": "event", "name": "Change data capture",
     "summary": "Database changes are captured from the log and streamed to consumers.",
     "keywords": "database replication change data capture cdc table row stream debezium log"},
    {"id": "api-gateway", "shape": "event", "name": "API facade",
     "summary": "A thin API in front of a legacy system exposes a stable, secured contract to new clients.",
     "keywords": "legacy expose api facade gateway mobile app partner secure modernize wrap"},
    {"id": "saga", "shape": "event", "name": "Saga with compensation",
     "summary": "Multi-step updates across systems with compensating actions when a step fails.",
     "keywords": "payment refund inventory reserve multiple systems consistency rollback compensate transaction"},
    {"id": "crm-sync", "shape": "poll", "name": "Bidirectional CRM sync",
     "summary": "Two systems both edit shared records; conflict rules decide which change wins.",
     "keywords": "crm salesforce hubspot contacts accounts both directions bidirectional conflict duplicate"},
]


_STOP = set("a an and are as at be by for from in into is it of on or our so that the their them they this to we with when which while each all".split())


def _stem(w: str) -> str:
    for suf in ("ing", "ed", "es", "s"):
        if len(w) > 4 and w.endswith(suf):
            return w[: -len(suf)]
    return w


def embed(text_: str) -> list[float]:
    """Deterministic hashing embedding over stemmed content words and bigrams."""
    words = [_stem(w) for w in re.findall(r"[a-z0-9]+", text_.lower()) if w not in _STOP]
    vec = [0.0] * DIM
    for tok in words + [a + "_" + b for a, b in zip(words, words[1:])]:
        h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
        vec[h % DIM] += 1.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def _ensure_table() -> None:
    e = db.engine()
    with e.begin() as conn:
        if db.is_postgres(e):
            conn.execute(text(f"CREATE TABLE IF NOT EXISTS pattern_index (id text PRIMARY KEY, embedding vector({DIM}))"))
            for p in PATTERNS:
                conn.execute(
                    text("INSERT INTO pattern_index (id, embedding) VALUES (:id, CAST(:v AS vector)) "
                         "ON CONFLICT (id) DO UPDATE SET embedding = EXCLUDED.embedding"),
                    {"id": p["id"], "v": str(embed(p["name"] + " " + p["summary"] + " " + p["keywords"]))},
                )


_ready = False


def search(query: str, k: int = 3) -> list[dict]:
    """Return the k most similar patterns with a cosine similarity score."""
    global _ready
    q = embed(query)
    if db.is_postgres():
        if not _ready:
            _ensure_table()
            _ready = True
        with db.engine().connect() as conn:
            rows = conn.execute(
                text("SELECT id, 1 - (embedding <=> CAST(:q AS vector)) AS score FROM pattern_index "
                     "ORDER BY embedding <=> CAST(:q AS vector) LIMIT :k"),
                {"q": str(q), "k": k},
            ).all()
        by_id = {p["id"]: p for p in PATTERNS}
        return [{**by_id[r.id], "score": round(float(r.score), 3)} for r in rows]
    scored = []
    for p in PATTERNS:
        v = embed(p["name"] + " " + p["summary"] + " " + p["keywords"])
        scored.append({**p, "score": round(sum(a * b for a, b in zip(q, v)), 3)})
    return sorted(scored, key=lambda p: -p["score"])[:k]


def reset() -> None:
    global _ready
    _ready = False

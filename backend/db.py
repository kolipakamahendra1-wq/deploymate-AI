"""Database engine shared by the API store and the pattern index.

DATABASE_URL selects the backend: SQLite by default, PostgreSQL (with the
pgvector extension) in docker compose.
"""
from __future__ import annotations

import os

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.pool import StaticPool

_engine: Engine | None = None


def engine() -> Engine:
    global _engine
    if _engine is None:
        url = os.getenv("DATABASE_URL", "sqlite:///deploymate.db")
        kwargs: dict = {}
        if url.startswith("sqlite"):
            kwargs["connect_args"] = {"check_same_thread": False}
            if ":memory:" in url:
                kwargs["poolclass"] = StaticPool
        else:
            kwargs["pool_pre_ping"] = True
        _engine = create_engine(url, **kwargs)
        if is_postgres(_engine):
            with _engine.begin() as conn:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    return _engine


def is_postgres(e: Engine | None = None) -> bool:
    return (e or engine()).dialect.name == "postgresql"


def reset_engine() -> None:
    global _engine
    if _engine is not None:
        _engine.dispose()
    _engine = None

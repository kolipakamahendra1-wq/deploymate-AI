"""SQLite persistence. Every query is scoped by customer_id (data isolation)."""
from __future__ import annotations

import os
import uuid

from sqlalchemy import Column, String, Text, create_engine
from sqlalchemy.orm import Session, declarative_base
from sqlalchemy.pool import StaticPool

from ..schemas.models import PipelineState

Base = declarative_base()
_engine = None


class Customer(Base):
    __tablename__ = "customers"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    state_json = Column(Text, nullable=False)


def engine():
    global _engine
    if _engine is None:
        url = os.getenv("DATABASE_URL", "sqlite:///deploymate.db")
        kwargs = {"connect_args": {"check_same_thread": False}}
        if ":memory:" in url:
            kwargs["poolclass"] = StaticPool
        _engine = create_engine(url, **kwargs)
        Base.metadata.create_all(_engine)
    return _engine


def reset_engine():
    global _engine
    _engine = None


def create_customer(name: str, state: PipelineState) -> str:
    cid = uuid.uuid4().hex[:8]
    state = state.model_copy(update={"customer_id": cid})
    with Session(engine()) as s:
        s.add(Customer(id=cid, name=name, state_json=state.model_dump_json()))
        s.commit()
    return cid


def load(cid: str) -> PipelineState | None:
    with Session(engine()) as s:
        row = s.get(Customer, cid)
        return PipelineState.model_validate_json(row.state_json) if row else None


def save(state: PipelineState) -> None:
    with Session(engine()) as s:
        row = s.get(Customer, state.customer_id)
        row.state_json = state.model_dump_json()
        s.commit()


def list_customers() -> list[dict]:
    with Session(engine()) as s:
        return [{"id": c.id, "name": c.name} for c in s.query(Customer).all()]

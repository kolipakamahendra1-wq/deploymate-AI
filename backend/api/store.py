"""Persistence. Every query is scoped by customer_id (data isolation).

Decisions are also written to an append-only `decision_log` table so the audit
trail survives later re-runs that replace the pipeline state.
"""
from __future__ import annotations

import uuid

from sqlalchemy import Column, Integer, String, Text, func, select
from sqlalchemy.orm import Session, declarative_base

from .. import db
from ..schemas.models import PipelineState

Base = declarative_base()
_created = False


class Customer(Base):
    __tablename__ = "customers"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    state_json = Column(Text, nullable=False)


class DecisionLog(Base):
    __tablename__ = "decision_log"
    seq = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(String, index=True, nullable=False)
    run = Column(Integer, nullable=False)
    agent = Column(String, nullable=False)
    decision = Column(Text, nullable=False)
    rationale = Column(Text, default="")
    at = Column(String, nullable=False)


def engine():
    global _created
    e = db.engine()
    if not _created:
        Base.metadata.create_all(e)
        _created = True
    return e


def reset_engine():
    global _created
    _created = False
    db.reset_engine()


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


def save(state: PipelineState, run: int | None = None) -> None:
    """Persist state; when `run` is given, append decisions not yet logged for it."""
    with Session(engine()) as s:
        row = s.get(Customer, state.customer_id)
        row.state_json = state.model_dump_json()
        if run is not None:
            logged = s.scalar(select(func.count()).select_from(DecisionLog)
                              .where(DecisionLog.customer_id == state.customer_id, DecisionLog.run == run)) or 0
            for d in state.decisions[logged:]:
                s.add(DecisionLog(customer_id=state.customer_id, run=run, agent=d.agent,
                                  decision=d.decision, rationale=d.rationale, at=d.at))
        s.commit()


def next_run(cid: str) -> int:
    with Session(engine()) as s:
        return (s.scalar(select(func.max(DecisionLog.run)).where(DecisionLog.customer_id == cid)) or 0) + 1


def decision_log(cid: str) -> list[dict]:
    with Session(engine()) as s:
        rows = s.scalars(select(DecisionLog).where(DecisionLog.customer_id == cid).order_by(DecisionLog.seq))
        return [{"run": r.run, "agent": r.agent, "decision": r.decision, "rationale": r.rationale, "at": r.at}
                for r in rows]


def list_customers() -> list[dict]:
    with Session(engine()) as s:
        return [{"id": c.id, "name": c.name} for c in s.query(Customer).order_by(Customer.name).all()]

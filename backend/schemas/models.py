"""Shared structured state for the DeployMate pipeline.

Every claim carries a provenance (fact / assumption / unknown). A `fact`
must cite a source, which is how the "never invent customer APIs" guardrail
is enforced in code rather than in prompts.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class Provenance(str, Enum):
    fact = "fact"
    assumption = "assumption"
    unknown = "unknown"


class Claim(BaseModel):
    provenance: Provenance = Provenance.unknown
    source: str | None = None  # e.g. "openapi:POST /orders", "brief", "sample:fulfillment.json"

    @model_validator(mode="after")
    def _fact_needs_source(self):
        if self.provenance == Provenance.fact and not self.source:
            raise ValueError("a fact must cite a source")
        return self


class Requirement(Claim):
    id: str
    text: str
    kind: Literal["functional", "non-functional"]


class Question(BaseModel):
    id: str
    text: str
    category: Literal["auth", "throughput", "sla", "data-ownership", "failure", "other"]
    priority: Literal["high", "medium", "low"] = "medium"


class System(Claim):
    id: str
    name: str
    role: str = ""
    confirmed: bool = False  # hollow wireframe until confirmed


class Endpoint(Claim):
    system_id: str
    method: str
    path: str


class FieldMapping(Claim):
    source_field: str
    target_field: str
    confidence: float = Field(ge=0, le=1)
    transform: str = ""


class ArchComponent(BaseModel):
    id: str
    name: str
    layer: Literal["client", "api", "integration", "data"]
    description: str = ""


class ArchFlow(BaseModel):
    source: str
    target: str
    label: str = ""


class Architecture(BaseModel):
    components: list[ArchComponent] = []
    flows: list[ArchFlow] = []
    security_boundaries: list[str] = []
    mermaid: str = ""


class Task(BaseModel):
    id: str
    title: str
    depends_on: list[str] = []
    estimate_days: float = 1


class TestCase(BaseModel):
    id: str
    title: str
    covers: list[str] = []  # requirement ids
    expected: str = ""


class Risk(BaseModel):
    id: str
    title: str
    severity: Literal["high", "medium", "low"]
    mitigation: str = ""


class Decision(BaseModel):
    agent: str
    decision: str
    rationale: str = ""
    at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class CriticNote(BaseModel):
    severity: Literal["error", "warning"]
    message: str


class Handoff(BaseModel):
    markdown: str = ""
    requires_human_review: bool = True
    approved: bool = False


class PipelineState(BaseModel):
    customer_id: str
    brief: str
    openapi: dict | None = None
    sample: dict | list | None = None
    requirements: list[Requirement] = []
    questions: list[Question] = []
    systems: list[System] = []
    endpoints: list[Endpoint] = []
    mappings: list[FieldMapping] = []
    architecture: Architecture = Architecture()
    plan: list[Task] = []
    tests: list[TestCase] = []
    risks: list[Risk] = []
    critic_notes: list[CriticNote] = []
    handoff: Handoff = Handoff()
    decisions: list[Decision] = []
    completed_stages: list[str] = []

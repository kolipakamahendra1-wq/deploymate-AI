"""The seven pipeline agents. Each takes PipelineState and returns state updates."""
from __future__ import annotations

from ..integrations.parsers import parse_openapi, parse_sample
from ..schemas.models import (
    Architecture, CriticNote, Decision, Endpoint, FieldMapping, Handoff,
    PipelineState, Provenance, Question, Requirement, Risk, System, Task, TestCase,
)
from .llm import complete_json

GUARD = (
    "Never invent customer APIs. Mark anything not in the supplied material as "
    "provenance 'unknown' or 'assumption'. A 'fact' must cite a source."
)


def _decisions(state: PipelineState, payload: dict, agent: str, mode: str) -> list[Decision]:
    new = [Decision(**d) for d in payload.get("decisions", [])]
    new.append(Decision(agent=agent, decision=f"Stage completed ({mode})"))
    return state.decisions + new


def _done(state: PipelineState, name: str) -> list[str]:
    return state.completed_stages + [name]


def requirements_agent(state: PipelineState) -> dict:
    payload, mode = complete_json("requirements", f"Extract requirements. {GUARD}", state.brief)
    return {
        "requirements": [Requirement(**r) for r in payload["requirements"]],
        "decisions": _decisions(state, payload, "requirements", mode),
        "completed_stages": _done(state, "requirements"),
    }


def clarification_agent(state: PipelineState) -> dict:
    ctx = "\n".join(r.text for r in state.requirements)
    payload, mode = complete_json(
        "clarification", "Detect ambiguities: auth, throughput, SLA, ownership, failure.", ctx
    )
    return {
        "questions": [Question(**q) for q in payload["questions"]],
        "decisions": _decisions(state, payload, "clarification", mode),
        "completed_stages": _done(state, "clarification"),
    }


def integration_agent(state: PipelineState) -> dict:
    spec = parse_openapi(state.openapi)
    sample_fields = parse_sample(state.sample)
    systems = [
        System(id="order", name="Order Platform", role="source", confirmed=True,
               provenance=Provenance.fact, source="openapi:order-platform"),
        # Only a sample exists for fulfillment, so it stays unconfirmed (hollow in 3D).
        System(id="fulfillment", name="Fulfillment System", role="target", confirmed=False,
               provenance=Provenance.unknown),
    ]
    endpoints = [
        Endpoint(system_id="order", method=m, path=p, provenance=Provenance.fact, source=f"openapi:{m} {p}")
        for m, p in spec["endpoints"]
    ]
    payload, mode = complete_json(
        "integration", f"Map order fields to fulfillment fields. {GUARD}",
        f"order fields: {spec['fields']}\nfulfillment fields: {sample_fields}",
    )
    return {
        "systems": systems,
        "endpoints": endpoints,
        "mappings": [FieldMapping(**m) for m in payload["mappings"]],
        "decisions": _decisions(state, payload, "integration", mode),
        "completed_stages": _done(state, "integration"),
    }


def to_mermaid(arch: Architecture) -> str:
    lines = ["flowchart LR"]
    for c in arch.components:
        lines.append(f'  {c.id}["{c.name} ({c.layer})"]')
    for f in arch.flows:
        lines.append(f"  {f.source} -->|{f.label}| {f.target}")
    return "\n".join(lines)


def architecture_agent(state: PipelineState) -> dict:
    payload, mode = complete_json(
        "architecture", f"Design architecture and plan. {GUARD}",
        "\n".join(r.text for r in state.requirements),
    )
    arch = Architecture(**payload["architecture"])
    arch.mermaid = to_mermaid(arch)
    return {
        "architecture": arch,
        "plan": [Task(**t) for t in payload["plan"]],
        "decisions": _decisions(state, payload, "architecture", mode),
        "completed_stages": _done(state, "architecture"),
    }


def validation_agent(state: PipelineState) -> dict:
    payload, mode = complete_json(
        "validation", "Write test cases and risks.", "\n".join(r.text for r in state.requirements)
    )
    return {
        "tests": [TestCase(**t) for t in payload["tests"]],
        "risks": [Risk(**r) for r in payload["risks"]],
        "decisions": _decisions(state, payload, "validation", mode),
        "completed_stages": _done(state, "validation"),
    }


def critic_agent(state: PipelineState) -> dict:
    """Deterministic guardrail checks: invented APIs, unsourced facts, coverage gaps."""
    notes: list[CriticNote] = []
    spec = parse_openapi(state.openapi)
    known = {f"openapi:{m} {p}" for m, p in spec["endpoints"]}
    known_fields = set(spec["fields"]) | set(parse_sample(state.sample))
    for e in state.endpoints:
        if e.provenance == Provenance.fact and e.source not in known:
            notes.append(CriticNote(severity="error", message=f"Invented endpoint {e.method} {e.path}"))
    for m in state.mappings:
        if m.provenance == Provenance.fact and not {m.source_field, m.target_field} <= known_fields:
            notes.append(CriticNote(
                severity="error",
                message=f"Mapping {m.source_field}->{m.target_field} marked fact but field not in inputs"))
    covered = {rid for t in state.tests for rid in t.covers}
    for r in state.requirements:
        if r.provenance != Provenance.unknown and r.id not in covered:
            notes.append(CriticNote(severity="warning", message=f"Requirement {r.id} has no test"))
    ids = {t.id for t in state.plan}
    for t in state.plan:
        for dep in t.depends_on:
            if dep not in ids:
                notes.append(CriticNote(severity="error", message=f"Task {t.id} depends on missing {dep}"))
    return {
        "critic_notes": notes,
        "decisions": state.decisions + [Decision(agent="critic", decision=f"{len(notes)} issues found")],
        "completed_stages": _done(state, "critic"),
    }


def handoff_agent(state: PipelineState) -> dict:
    out = ["# Technical Proposal: Order Platform to Fulfillment Integration", ""]
    out += ["> DRAFT. Requires human review before any external commitment.", "", "## Requirements"]
    out += [f"- [{r.provenance.value}] {r.id}: {r.text}" for r in state.requirements]
    out += ["", "## Open questions"] + [f"- ({q.priority}) {q.text}" for q in state.questions]
    out += ["", "## Data mapping"] + [
        f"- `{m.source_field}` -> `{m.target_field}` ({m.confidence:.0%}, {m.provenance.value})"
        for m in state.mappings
    ]
    out += ["", "## Architecture", "```mermaid", state.architecture.mermaid, "```", "", "## Implementation plan"]
    out += [f"- {t.id} {t.title} (deps: {', '.join(t.depends_on) or 'none'})" for t in state.plan]
    out += ["", "## Test plan"] + [f"- {t.id} {t.title}" for t in state.tests]
    out += ["", "## Risks"] + [f"- ({r.severity}) {r.title}: {r.mitigation}" for r in state.risks]
    if state.critic_notes:
        out += ["", "## Critic findings"] + [f"- {n.severity}: {n.message}" for n in state.critic_notes]
    return {
        "handoff": Handoff(markdown="\n".join(out)),
        "decisions": state.decisions + [
            Decision(agent="handoff", decision="Generated handoff package (pending human approval)")],
        "completed_stages": _done(state, "handoff"),
    }

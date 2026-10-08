"""The seven pipeline agents. Each takes PipelineState and returns state updates."""
from __future__ import annotations

from pydantic import BaseModel

from ..integrations.parsers import parse_openapi, parse_sample
from ..integrations.patterns import search as search_patterns
from ..schemas.models import (
    Architecture, CriticNote, Decision, Endpoint, FieldMapping, Handoff, PatternRef,
    PipelineState, Provenance, Question, Requirement, Risk, Task, TestCase,
)
from . import heuristics as h
from .llm import run_agent

GUARD = (
    "Never invent customer APIs or fields. Anything not in the supplied brief, spec or "
    "sample must have provenance 'unknown' or 'assumption'. A 'fact' must cite a source."
)


class RequirementsOut(BaseModel):
    requirements: list[Requirement]
    decisions: list[Decision] = []


class ClarificationOut(BaseModel):
    questions: list[Question]
    decisions: list[Decision] = []


class IntegrationOut(BaseModel):
    mappings: list[FieldMapping]
    decisions: list[Decision] = []


class ArchitectureOut(BaseModel):
    architecture: Architecture
    plan: list[Task]
    decisions: list[Decision] = []


class ValidationOut(BaseModel):
    tests: list[TestCase]
    risks: list[Risk]
    decisions: list[Decision] = []


def _log(state: PipelineState, out: BaseModel, agent: str, mode: str, extra: list[Decision] = ()) -> list[Decision]:
    stamped = [d.model_copy(update={"agent": agent}) for d in getattr(out, "decisions", [])]
    return state.decisions + stamped + list(extra) + [Decision(agent=agent, decision=f"Stage completed ({mode})")]


def _done(state: PipelineState, name: str) -> list[str]:
    return state.completed_stages + [name]


def _context(state: PipelineState) -> str:
    spec = parse_openapi(state.openapi)
    return (f"Brief:\n{state.brief}\n\nSpec title: {spec['title']}\nEndpoints: {spec['endpoints']}\n"
            f"Spec fields: {spec['fields']}\nSample fields: {parse_sample(state.sample)}")


def requirements_agent(state: PipelineState) -> dict:
    systems = h.build_systems(state)
    out, mode = run_agent(
        "requirements", f"Extract functional and non-functional requirements. {GUARD}", _context(state),
        RequirementsOut, state.fixture,
        lambda: RequirementsOut(requirements=h.extract_requirements(state, systems), decisions=[
            Decision(agent="requirements", decision="Extracted requirements from need statements and NFR cues",
                     rationale="Systems without a spec get an 'unknown' API-contract requirement")]),
    )
    return {"requirements": out.requirements, "decisions": _log(state, out, "requirements", mode),
            "completed_stages": _done(state, "requirements")}


def clarification_agent(state: PipelineState) -> dict:
    systems = h.build_systems(state)
    out, mode = run_agent(
        "clarification",
        "List the questions the customer must answer: auth, throughput, SLA, data ownership, failure behaviour.",
        _context(state), ClarificationOut, state.fixture,
        lambda: ClarificationOut(questions=h.detect_questions(state, systems), decisions=[
            Decision(agent="clarification", decision="Checked brief and materials for each gap category",
                     rationale="A question is raised only when the material does not already answer it")]),
    )
    return {"questions": out.questions, "decisions": _log(state, out, "clarification", mode),
            "completed_stages": _done(state, "clarification")}


def integration_agent(state: PipelineState) -> dict:
    # Systems and endpoints are never model output: they come only from the inputs.
    spec = parse_openapi(state.openapi)
    systems = h.build_systems(state)
    owner = next((s for s in systems if s.confirmed), None)
    endpoints = [
        Endpoint(system_id=owner.id, method=m, path=p, provenance=Provenance.fact, source=f"openapi:{m} {p}")
        for m, p in spec["endpoints"]
    ] if owner else []
    out, mode = run_agent(
        "integration", f"Map source fields to target fields. {GUARD}", _context(state),
        IntegrationOut, state.fixture,
        lambda: IntegrationOut(mappings=h.map_fields(state), decisions=[
            Decision(agent="integration", decision="Mapped fields by name, synonyms and similarity",
                     rationale="Only exact semantic matches are facts; the rest are assumptions to confirm")]),
    )
    return {"systems": systems, "endpoints": endpoints, "mappings": out.mappings,
            "decisions": _log(state, out, "integration", mode),
            "completed_stages": _done(state, "integration")}


def _mid(cid: str) -> str:
    """Mermaid node ids cannot contain dashes."""
    return "n_" + cid.replace("-", "_")


def to_mermaid(arch: Architecture) -> str:
    lines = ["flowchart LR"]
    for c in arch.components:
        lines.append(f'  {_mid(c.id)}["{c.name}"]')
    comp_ids = {c.id for c in arch.components}
    for i, b in enumerate(arch.security_boundaries):
        lines.append(f'  subgraph B{i}["{b.name}"]')
        lines += [f"    {_mid(cid)}" for cid in b.components if cid in comp_ids]
        lines.append("  end")
    for f in arch.flows:
        lines.append(f"  {_mid(f.source)} -->|{f.label}| {_mid(f.target)}")
    return "\n".join(lines)


def architecture_agent(state: PipelineState) -> dict:
    hits = search_patterns(state.brief, k=3)
    patterns = [PatternRef(id=p["id"], name=p["name"], summary=p["summary"], score=p["score"]) for p in hits]
    shape = hits[0]["shape"] if hits else "event"

    def offline() -> ArchitectureOut:
        arch = h.build_architecture(state.model_copy(update={"systems": state.systems}), shape)
        plan = h.build_plan(state.model_copy(update={"architecture": arch}))
        return ArchitectureOut(architecture=arch, plan=plan)

    out, mode = run_agent(
        "architecture", f"Design the integration architecture and an implementation plan. {GUARD}",
        _context(state) + f"\nSuggested pattern: {hits[0]['name'] if hits else 'none'}",
        ArchitectureOut, state.fixture, offline,
    )
    arch = out.architecture
    arch.mermaid = to_mermaid(arch)
    weak = not patterns or patterns[0].score < 0.3
    cite = Decision(
        agent="architecture",
        decision=f"Closest pattern: {patterns[0].name} (similarity {patterns[0].score:.2f})" if patterns else "No pattern matched",
        rationale=("Weak match: the brief does not say how data should flow, so confirm the delivery mode. " if weak else "")
        + (patterns[0].summary if patterns else ""),
    )
    return {"architecture": arch, "plan": out.plan, "patterns": patterns,
            "decisions": _log(state, out, "architecture", mode, [cite]),
            "completed_stages": _done(state, "architecture")}


def validation_agent(state: PipelineState) -> dict:
    out, mode = run_agent(
        "validation", "Write test cases that cover every requirement, and a risk register.",
        _context(state) + "\nRequirements:\n" + "\n".join(f"{r.id}: {r.text}" for r in state.requirements),
        ValidationOut, state.fixture,
        lambda: ValidationOut(tests=h.build_tests(state), risks=h.build_risks(state)),
    )
    return {"tests": out.tests, "risks": out.risks, "decisions": _log(state, out, "validation", mode),
            "completed_stages": _done(state, "validation")}


def _has_cycle(plan: list[Task]) -> bool:
    deps = {t.id: t.depends_on for t in plan}
    state: dict[str, int] = {}

    def visit(n: str) -> bool:
        if state.get(n) == 1:
            return True
        if state.get(n) == 2 or n not in deps:
            return False
        state[n] = 1
        if any(visit(d) for d in deps[n]):
            return True
        state[n] = 2
        return False

    return any(visit(t) for t in deps)


def critic_agent(state: PipelineState) -> dict:
    """Deterministic guardrail checks over everything the other agents produced."""
    notes: list[CriticNote] = []
    spec = parse_openapi(state.openapi)
    known = {f"openapi:{m} {p}" for m, p in spec["endpoints"]}
    known_fields = set(spec["fields"]) | set(parse_sample(state.sample))
    for e in state.endpoints:
        if e.provenance == Provenance.fact and e.source not in known:
            notes.append(CriticNote(severity="error", message=f"Invented endpoint {e.method} {e.path}"))
    seen_targets: set[str] = set()
    for m in state.mappings:
        if m.provenance == Provenance.fact and not {m.source_field, m.target_field} <= known_fields:
            notes.append(CriticNote(severity="error",
                                    message=f"Mapping {m.source_field}->{m.target_field} marked fact but field not in inputs"))
        if m.target_field != "?" and m.target_field in seen_targets:
            notes.append(CriticNote(severity="warning", message=f"Target field {m.target_field} mapped twice"))
        seen_targets.add(m.target_field)
    covered = {rid for t in state.tests for rid in t.covers}
    for r in state.requirements:
        if r.provenance != Provenance.unknown and r.id not in covered:
            notes.append(CriticNote(severity="warning", message=f"Requirement {r.id} has no test"))
    ids = {t.id for t in state.plan}
    for t in state.plan:
        for dep in t.depends_on:
            if dep not in ids:
                notes.append(CriticNote(severity="error", message=f"Task {t.id} depends on missing {dep}"))
    if _has_cycle(state.plan):
        notes.append(CriticNote(severity="error", message="Implementation plan has a dependency cycle"))
    comp_ids = {c.id for c in state.architecture.components}
    for f in state.architecture.flows:
        if f.source not in comp_ids or f.target not in comp_ids:
            notes.append(CriticNote(severity="error", message=f"Flow {f.source}->{f.target} references a missing component"))
    names = {c.name.lower() for c in state.architecture.components}
    for s in state.systems:
        if s.name.lower() not in names:
            notes.append(CriticNote(severity="warning", message=f"System {s.name} is not in the architecture"))
    return {
        "critic_notes": notes,
        "decisions": state.decisions + [Decision(agent="critic", decision=f"{len(notes)} issues found",
                                                 rationale="Rule-based checks: provenance, coverage, plan and architecture validity")],
        "completed_stages": _done(state, "critic"),
    }


def handoff_agent(state: PipelineState) -> dict:
    title = " to ".join(s.name for s in state.systems[:2]) or "Integration"
    out = [f"# Technical Proposal: {title} Integration", ""]
    out += ["> DRAFT. Requires human review before any external commitment.",
            "> Legend: [fact] stated in customer material, [assumption] inferred, [unknown] must be confirmed.", ""]
    out += ["## Requirements"] + [f"- [{r.provenance.value}] {r.id}: {r.text}" for r in state.requirements]
    out += ["", "## Open questions"] + [f"- ({q.priority}) {q.text}" for q in state.questions]
    out += ["", "## Systems"] + [
        f"- {s.name} ({s.role}): {'API documented' if s.confirmed else 'API contract unknown'}" for s in state.systems]
    out += ["", "## Data mapping"] + [
        f"- `{m.source_field}` -> `{m.target_field}` ({m.confidence:.0%}, {m.provenance.value})" for m in state.mappings]
    if state.patterns:
        out += ["", "## Reference pattern", f"{state.patterns[0].name}: {state.patterns[0].summary}"]
    out += ["", "## Architecture", "```mermaid", state.architecture.mermaid, "```", ""]
    out += ["Security boundaries:"] + [f"- {b.name}: {', '.join(b.components)}" for b in state.architecture.security_boundaries]
    out += ["", "## Implementation plan"]
    out += [f"- {t.id} {t.title} ({t.estimate_days:g}d; after {', '.join(t.depends_on) or 'none'})" for t in state.plan]
    out += ["", "## Test plan"] + [f"- {t.id} {t.title}: {t.expected}" for t in state.tests]
    out += ["", "## Risks"] + [f"- ({r.severity}) {r.title}: {r.mitigation}" for r in state.risks]
    if state.critic_notes:
        out += ["", "## Critic findings"] + [f"- {n.severity}: {n.message}" for n in state.critic_notes]
    out += ["", "## Integration checklist", "- [ ] Open questions answered", "- [ ] API credentials issued",
            "- [ ] Mapping signed off by customer", "- [ ] Test plan agreed", "- [ ] Human approval recorded"]
    return {
        "handoff": Handoff(markdown="\n".join(out)),
        "decisions": state.decisions + [
            Decision(agent="handoff", decision="Generated handoff package (pending human approval)")],
        "completed_stages": _done(state, "handoff"),
    }

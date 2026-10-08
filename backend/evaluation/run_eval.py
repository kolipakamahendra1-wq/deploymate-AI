"""Small evaluation suite for the demo slice (PRD section 13, reduced to 5 cases).

Each case plants (or does not plant) a guardrail violation in the demo run and
checks whether the critic catches it. We also score the demo run against a
gold set of missing-question categories.

Run: python -m backend.evaluation.run_eval
"""
from __future__ import annotations

import json
from pathlib import Path

from ..agents.graph import run_pipeline
from ..agents.stages import critic_agent
from ..schemas.models import Endpoint, FieldMapping, PipelineState, Provenance, Task

DEMO = Path(__file__).resolve().parents[2] / "examples" / "demo_customer"
GOLD_QUESTION_CATEGORIES = {"auth", "throughput", "sla", "data-ownership", "failure"}


def _demo_final() -> PipelineState:
    state = PipelineState(
        customer_id="eval",
        brief=(DEMO / "brief.txt").read_text(encoding="utf-8"),
        openapi=json.loads((DEMO / "order_platform.openapi.json").read_text(encoding="utf-8")),
        sample=json.loads((DEMO / "fulfillment_sample.json").read_text(encoding="utf-8")),
    )
    final = state
    for _, final in run_pipeline(state):
        pass
    return final


def _cases(base: PipelineState) -> list[tuple[str, PipelineState, bool]]:
    """(name, mutated state, violation expected)."""
    invented = base.model_copy(update={"endpoints": base.endpoints + [
        Endpoint(system_id="fulfillment", method="POST", path="/shipments",
                 provenance=Provenance.fact, source="openapi:POST /shipments")]})
    bad_map = base.model_copy(update={"mappings": base.mappings + [
        FieldMapping(source_field="loyalty_tier", target_field="priority", confidence=0.9,
                     provenance=Provenance.fact, source="guess")]})
    bad_dep = base.model_copy(update={"plan": base.plan + [
        Task(id="T9", title="Go live", depends_on=["T42"])]})
    untested = base.model_copy(update={"tests": [t for t in base.tests if "R2" not in t.covers]})
    return [
        ("clean demo run", base, False),
        ("invented fulfillment endpoint", invented, True),
        ("mapping fact on unknown field", bad_map, True),
        ("task depends on missing task", bad_dep, True),
        ("requirement without a test", untested, True),
    ]


def main() -> dict:
    base = _demo_final()
    rows = []
    for name, state, expected in _cases(base):
        found = bool(critic_agent(state)["critic_notes"])
        rows.append({"case": name, "expected_violation": expected, "flagged": found, "correct": found == expected})
    asked = {q.category for q in base.questions}
    report = {
        "critic_accuracy": sum(r["correct"] for r in rows) / len(rows),
        "missing_question_recall": len(asked & GOLD_QUESTION_CATEGORIES) / len(GOLD_QUESTION_CATEGORIES),
        "cases": rows,
    }
    out = Path(__file__).resolve().parents[2] / "generated" / "eval_report.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return report


if __name__ == "__main__":
    main()

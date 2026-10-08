"""Evaluation suite (PRD section 13).

Runs the full pipeline on 40 synthetic cases and measures:
  requirement extraction precision and recall, missing-question recall,
  mapping accuracy, architecture validity, test-case coverage and pattern
  retrieval accuracy, plus critic accuracy on planted guardrail violations.
The human reviewer score cannot be computed automatically and is reported as
null rather than estimated.

Cases run with the LLM disabled, so the numbers describe the offline agents.

Run: python -m backend.evaluation.run_eval
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from statistics import mean

from ..agents.graph import run_pipeline
from ..agents.stages import critic_agent
from ..schemas.models import Endpoint, FieldMapping, PipelineState, Provenance, Task
from .cases import Case, build_cases

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "generated" / "eval_report.json"
STRUCTURAL = ("missing", "cycle", "not in the architecture")


def _words(s: str) -> set[str]:
    return {w for w in re.findall(r"[a-z]+", s.lower()) if len(w) > 2 and w not in {"our", "the", "and", "are"}}


def _matches(text: str, gold: str) -> bool:
    g = _words(gold)
    return bool(g) and len(_words(text) & g) / len(g) >= 0.6


def _run(case: Case) -> PipelineState:
    state = PipelineState(customer_id=case.id, brief=case.brief, openapi=case.openapi, sample=case.sample)
    for _, state in run_pipeline(state):
        pass
    return state


def score_case(case: Case) -> dict:
    st = _run(case)
    extracted = [r for r in st.requirements if r.kind == "functional" and r.provenance == Provenance.fact]
    tp = [r for r in extracted if any(_matches(r.text, g) for g in case.gold_requirements)]
    found_gold = [g for g in case.gold_requirements if any(_matches(r.text, g) for r in extracted)]
    asked = {q.category for q in st.questions}
    mapped = {m.source_field: (None if m.target_field == "?" else m.target_field) for m in st.mappings}
    correct_maps = sum(mapped.get(src) == tgt for src, tgt in case.gold_mapping.items())
    structural = [n for n in st.critic_notes if any(k in n.message for k in STRUCTURAL)]
    known = [r for r in st.requirements if r.provenance != Provenance.unknown]
    covered = {rid for t in st.tests for rid in t.covers}
    return {
        "case": case.id,
        "name": case.name,
        "requirement_precision": len(tp) / len(extracted) if extracted else 0.0,
        "requirement_recall": len(found_gold) / len(case.gold_requirements),
        "missing_question_recall": len(asked & case.gold_questions) / len(case.gold_questions),
        "mapping_accuracy": correct_maps / len(case.gold_mapping),
        "architecture_valid": 1.0 if not structural and st.architecture.components else 0.0,
        "test_coverage": sum(r.id in covered for r in known) / len(known) if known else 1.0,
        "pattern_top1": 1.0 if st.patterns and st.patterns[0].id == case.gold_pattern else 0.0,
        "systems_detected": [s.name for s in st.systems],
    }


def critic_cases(base: PipelineState) -> list[dict]:
    """Planted violations: the critic should flag each mutated state and not the clean one."""
    planted = [
        ("clean run", base, False),
        ("invented endpoint", base.model_copy(update={"endpoints": base.endpoints + [
            Endpoint(system_id="x", method="POST", path="/refunds", provenance=Provenance.fact,
                     source="openapi:POST /refunds")]}), True),
        ("fact mapping on unknown field", base.model_copy(update={"mappings": base.mappings + [
            FieldMapping(source_field="loyalty_tier", target_field="priority", confidence=0.9,
                         provenance=Provenance.fact, source="guess")]}), True),
        ("missing task dependency", base.model_copy(update={"plan": base.plan + [
            Task(id="T99", title="Go live", depends_on=["T42"])]}), True),
        ("dependency cycle", base.model_copy(update={"plan": base.plan + [
            Task(id="TA", title="a", depends_on=["TB"]), Task(id="TB", title="b", depends_on=["TA"])]}), True),
        ("requirement without a test", base.model_copy(update={"tests": []}), True),
    ]
    rows = []
    for name, st, expected in planted:
        flagged = bool(critic_agent(st)["critic_notes"])
        rows.append({"case": name, "expected_violation": expected, "flagged": flagged, "correct": flagged == expected})
    return rows


METRICS = ["requirement_precision", "requirement_recall", "missing_question_recall", "mapping_accuracy",
           "architecture_valid", "test_coverage", "pattern_top1"]


def main(write: bool = True, quiet: bool = False, live: bool = False, limit: int | None = None) -> dict:
    """Score the offline agents (default), or the configured live model with live=True."""
    from ..agents.llm import live_enabled, model_name

    if live and not live_enabled():
        raise SystemExit("--live needs LLM_PROVIDER (or LLM_API_KEY) to be set")
    saved = {} if live else {k: os.environ.pop(k) for k in ("LLM_API_KEY", "LLM_PROVIDER") if k in os.environ}
    try:
        cases = build_cases()
        if limit:  # spread the sample across domains
            cases = cases[:: max(1, len(cases) // limit)][:limit]
        rows = []
        for c in cases:
            rows.append(score_case(c))
            if not quiet and live:
                print(f"  {c.id} done", flush=True)
        critic = critic_cases(_run(build_cases()[0])) if not live else []
    finally:
        os.environ.update(saved)
    report = {
        "mode": f"live model ({model_name()})" if live else "offline agents",
        "cases": len(rows),
        "summary": {m: round(mean(r[m] for r in rows), 3) for m in METRICS},
        "critic_accuracy": round(mean(r["correct"] for r in critic), 3) if critic else None,
        "human_reviewer_score": None,
        "notes": "Synthetic cases were written alongside the offline agents, so scores are optimistic "
                 "for real briefs. Human reviewer score requires people and is not estimated.",
        "per_case": rows,
        "critic_cases": critic,
    }
    if write:
        REPORT.parent.mkdir(exist_ok=True)
        path = REPORT.with_name("eval_report_live.json") if live else REPORT
        path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    if not quiet:
        print(json.dumps({k: report[k] for k in ("cases", "summary", "critic_accuracy")}, indent=2))
    return report


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--live", action="store_true", help="score the configured LLM instead of the offline agents")
    ap.add_argument("--limit", type=int, help="number of cases to sample (live runs are slow)")
    args = ap.parse_args()
    main(live=args.live, limit=args.limit)

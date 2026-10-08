from __future__ import annotations

from typing import Iterator

from langgraph.graph import END, START, StateGraph

from ..schemas.models import PipelineState
from . import stages

ORDER = [
    ("requirements", stages.requirements_agent),
    ("clarification", stages.clarification_agent),
    ("integration", stages.integration_agent),
    ("architecture", stages.architecture_agent),
    ("validation", stages.validation_agent),
    ("critic", stages.critic_agent),
    ("handoff", stages.handoff_agent),
]
STAGE_NAMES = [n for n, _ in ORDER]


def build_graph():
    g = StateGraph(PipelineState)
    for name, fn in ORDER:
        g.add_node(name, fn)
    g.add_edge(START, ORDER[0][0])
    for (a, _), (b, _) in zip(ORDER, ORDER[1:]):
        g.add_edge(a, b)
    g.add_edge(ORDER[-1][0], END)
    return g.compile()


def run_pipeline(state: PipelineState) -> Iterator[tuple[str, PipelineState]]:
    """Yield (stage, full state) after each agent finishes."""
    current = state
    for update in build_graph().stream(state, stream_mode="updates"):
        for stage, delta in update.items():
            current = current.model_copy(update=delta)
            yield stage, current

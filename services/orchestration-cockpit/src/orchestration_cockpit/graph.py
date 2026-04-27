from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from orchestration_cockpit.nodes import (
    finalize_node,
    intake_node,
    make_specialized_invoke_node,
    ordinary_placeholder_node,
    route_edge,
    route_node,
    specialized_prepare_node,
)
from orchestration_cockpit.state import CockpitState


def build_graph():
    builder = StateGraph(CockpitState)
    builder.add_node("intake", intake_node)
    builder.add_node("route", route_node)
    builder.add_node("ordinary_placeholder", ordinary_placeholder_node)
    builder.add_node("specialized_prepare", specialized_prepare_node)
    builder.add_node("specialized_invoke", make_specialized_invoke_node())
    builder.add_node("finalize", finalize_node)
    builder.add_edge(START, "intake")
    builder.add_edge("intake", "route")
    builder.add_conditional_edges(
        "route",
        route_edge,
        {
            "ordinary_placeholder": "ordinary_placeholder",
            "specialized_prepare": "specialized_prepare",
            "finalize": "finalize",
        },
    )
    builder.add_edge("ordinary_placeholder", "finalize")
    builder.add_edge("specialized_prepare", "specialized_invoke")
    builder.add_edge("specialized_invoke", "finalize")
    builder.add_edge("finalize", END)
    return builder.compile()


graph = build_graph()

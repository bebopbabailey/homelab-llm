from __future__ import annotations

from typing import Annotated, Any

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class CockpitState(TypedDict, total=False):
    messages: Annotated[list[AnyMessage], add_messages]
    thread_id: str
    run_id: str
    started_at: str
    mission_mode: str
    route_decision: str
    route_reason: str
    fixture_id: str
    node_sequence: list[str]
    adapter_request_id: str
    specialized_payload: dict[str, Any]
    specialized_result: dict[str, Any]
    final_text: str
    error: str

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from typing import Any, Mapping

from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from orchestration_cockpit.graph import build_graph
from orchestration_cockpit.nodes import (
    build_specialized_payload,
    finalize_node,
    intake_node,
    make_specialized_invoke_node,
    ordinary_placeholder_node,
    route_edge,
    route_node,
    specialized_prepare_node,
)
from orchestration_cockpit.observability import adapter_telemetry_path, run_ledger_path
from orchestration_cockpit.routing import decide_route
from orchestration_cockpit.state import CockpitState

TEST_CONFIG = {"configurable": {"thread_id": "test-thread"}}


def build_test_graph(fake_runner):
    builder = StateGraph(CockpitState)
    builder.add_node("intake", intake_node)
    builder.add_node("route", route_node)
    builder.add_node("ordinary_placeholder", ordinary_placeholder_node)
    builder.add_node("specialized_prepare", specialized_prepare_node)
    builder.add_node("specialized_invoke", make_specialized_invoke_node(fake_runner))
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
    return builder.compile(checkpointer=InMemorySaver())


class RoutingTests(unittest.TestCase):
    def test_decide_route_specialized(self) -> None:
        decision = decide_route("/specialized S02 explain the runtime")
        self.assertEqual(decision.route_decision, "specialized-runtime")
        self.assertEqual(decision.fixture_id, "S02")

    def test_decide_route_invalid_specialized(self) -> None:
        decision = decide_route("/specialized TOOL explain the runtime")
        self.assertEqual(decision.route_decision, "out-of-scope")

    def test_decide_route_ordinary(self) -> None:
        decision = decide_route("hello there")
        self.assertEqual(decision.route_decision, "ordinary-placeholder")


class GraphTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.original_artifact_dir = os.environ.get("ORCHESTRATION_COCKPIT_ARTIFACT_DIR")
        os.environ["ORCHESTRATION_COCKPIT_ARTIFACT_DIR"] = self.tempdir.name

    def tearDown(self) -> None:
        if self.original_artifact_dir is None:
            os.environ.pop("ORCHESTRATION_COCKPIT_ARTIFACT_DIR", None)
        else:
            os.environ["ORCHESTRATION_COCKPIT_ARTIFACT_DIR"] = self.original_artifact_dir
        self.tempdir.cleanup()

    def test_graph_builds(self) -> None:
        self.assertIsNotNone(build_graph())

    def test_ordinary_path_returns_placeholder_and_writes_ledger(self) -> None:
        graph = build_test_graph(lambda payload: {"choices": []})
        result = graph.invoke({"messages": [HumanMessage(content="hello")]}, config=TEST_CONFIG)
        contents = [message.content for message in result["messages"]]
        self.assertIn("Intake: mission received", contents)
        self.assertIn("Route: ordinary-placeholder", contents)
        self.assertIn("Ordinary: deterministic placeholder path selected", contents)
        self.assertIn("Ordinary placeholder path", contents[-1])
        self.assertEqual(
            result["node_sequence"],
            ["intake", "route", "ordinary_placeholder", "finalize"],
        )
        ledger = _load_jsonl(run_ledger_path())
        self.assertEqual(ledger[0]["thread_id"], "test-thread")
        self.assertEqual(ledger[0]["route_decision"], "ordinary-placeholder")
        self.assertEqual(
            ledger[0]["node_sequence"],
            ["intake", "route", "ordinary_placeholder", "finalize"],
        )

    def test_specialized_path_invokes_runner_and_records_correlation(self) -> None:
        captured: dict[str, Any] = {}

        def fake_runner(payload: Mapping[str, Any]):
            captured.update(payload)
            return {
                "choices": [
                    {
                        "message": {
                            "content": "deterministic specialized reply"
                        }
                    }
                ]
            }

        graph = build_test_graph(fake_runner)
        result = graph.invoke(
            {
                "messages": [
                    HumanMessage(content="/specialized S02 explain the repeated-prefix runtime path briefly")
                ]
            },
            config=TEST_CONFIG,
        )
        self.assertEqual(captured["stream"], False)
        self.assertEqual(captured["temperature"], 0)
        self.assertEqual(captured["top_p"], 1)
        self.assertEqual(len(captured["messages"]), 2)
        contents = [message.content for message in result["messages"]]
        self.assertIn("Route: specialized-runtime (fixture S02)", contents)
        self.assertIn("Prepare: specialized payload built for fixture S02", contents)
        self.assertTrue(any(content.startswith("Invoke: omlx-runtime request adapter-") for content in contents))
        self.assertIn("deterministic specialized reply", contents[-1])
        self.assertEqual(
            result["node_sequence"],
            ["intake", "route", "specialized_prepare", "specialized_invoke", "finalize"],
        )
        self.assertTrue(result["adapter_request_id"].startswith("adapter-"))
        ledger = _load_jsonl(run_ledger_path())
        telemetry = _load_jsonl(adapter_telemetry_path())
        self.assertEqual(ledger[0]["adapter_request_id"], result["adapter_request_id"])
        self.assertEqual(telemetry[0]["request_id"], result["adapter_request_id"])
        self.assertEqual(telemetry[0]["fixture_id"], "S02")

    def test_out_of_scope_specialized_request_does_not_invoke_runner(self) -> None:
        called = False

        def fake_runner(payload: Mapping[str, Any]):
            nonlocal called
            called = True
            return {"choices": []}

        graph = build_test_graph(fake_runner)
        result = graph.invoke(
            {
                "messages": [
                    HumanMessage(content="/specialized TOOL please run tools")
                ]
            },
            config=TEST_CONFIG,
        )
        self.assertFalse(called)
        self.assertIn("Out of scope:", result["messages"][-1].content)
        self.assertEqual(result["node_sequence"], ["intake", "route", "finalize"])
        self.assertFalse(Path(adapter_telemetry_path()).exists())


class PayloadTests(unittest.TestCase):
    def test_specialized_payload_matches_frozen_contract(self) -> None:
        payload = build_specialized_payload(
            fixture_id="S02",
            mission_text="explain the runtime briefly",
            model="Qwen3-4B-Instruct-2507-4bit",
        )
        self.assertEqual(
            set(payload.keys()),
            {"model", "messages", "temperature", "top_p", "max_tokens", "stream"},
        )
        self.assertEqual(payload["stream"], False)
        self.assertEqual(payload["temperature"], 0)
        self.assertEqual(payload["top_p"], 1)
        self.assertEqual(payload["messages"][0]["role"], "system")
        self.assertEqual(payload["messages"][1]["role"], "user")


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


if __name__ == "__main__":
    unittest.main()

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
    build_pi_command,
    build_specialized_payload,
    finalize_node,
    intake_node,
    make_pi_invoke_node,
    make_specialized_invoke_node,
    ordinary_placeholder_node,
    pi_prepare_node,
    route_edge,
    route_node,
    specialized_prepare_node,
)
from orchestration_cockpit.observability import adapter_telemetry_path, run_ledger_path
from orchestration_cockpit.routing import decide_route
from orchestration_cockpit.state import CockpitState

TEST_CONFIG = {"configurable": {"thread_id": "test-thread"}}


def build_test_graph(fake_runner, fake_pi_runner=None):
    builder = StateGraph(CockpitState)
    builder.add_node("intake", intake_node)
    builder.add_node("route", route_node)
    builder.add_node("ordinary_placeholder", ordinary_placeholder_node)
    builder.add_node("specialized_prepare", specialized_prepare_node)
    builder.add_node("specialized_invoke", make_specialized_invoke_node(fake_runner))
    builder.add_node("pi_prepare", pi_prepare_node)
    builder.add_node("pi_invoke", make_pi_invoke_node(fake_pi_runner or _fake_pi_runner))
    builder.add_node("finalize", finalize_node)
    builder.add_edge(START, "intake")
    builder.add_edge("intake", "route")
    builder.add_conditional_edges(
        "route",
        route_edge,
        {
            "ordinary_placeholder": "ordinary_placeholder",
            "specialized_prepare": "specialized_prepare",
            "pi_prepare": "pi_prepare",
            "finalize": "finalize",
        },
    )
    builder.add_edge("ordinary_placeholder", "finalize")
    builder.add_edge("specialized_prepare", "specialized_invoke")
    builder.add_edge("specialized_invoke", "finalize")
    builder.add_edge("pi_prepare", "pi_invoke")
    builder.add_edge("pi_invoke", "finalize")
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

    def test_decide_route_pi_scratch_run(self) -> None:
        decision = decide_route("/pi --temperature 0.1 --max-tokens 2048 Fix the tests")
        self.assertEqual(decision.route_decision, "pi-scratch-run")
        self.assertEqual(decision.mission_mode, "pi")
        self.assertEqual(decision.mission_text, "Fix the tests")
        self.assertEqual(decision.pi_temperature, 0.1)
        self.assertEqual(decision.pi_max_tokens, 2048)

    def test_decide_route_pi_invalid_knob(self) -> None:
        decision = decide_route("/pi --max-tokens 10 Fix the tests")
        self.assertEqual(decision.route_decision, "out-of-scope")


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

    def test_pi_path_invokes_runner_and_records_artifact_pointers(self) -> None:
        captured: dict[str, Any] = {}

        def fake_pi_runner(command, timeout_seconds):
            captured["command"] = list(command)
            captured["timeout_seconds"] = timeout_seconds
            manifest = {
                "run_dir": "/tmp/pi-run",
                "scratch_repo": "/tmp/pi-run/scratch-repo",
                "artifacts": "/tmp/pi-run/artifacts",
                "pi_returncode": 0,
                "final_test_returncode": 0,
                "success": True,
            }
            return {
                "returncode": 0,
                "stdout": json.dumps(manifest),
                "stderr": "",
                "manifest": manifest,
                "timed_out": False,
            }

        graph = build_test_graph(lambda payload: {"choices": []}, fake_pi_runner)
        result = graph.invoke(
            {"messages": [HumanMessage(content="/pi --temperature 0.1 Fix the failing Python unittest suite.")]},
            config=TEST_CONFIG,
        )

        self.assertEqual(captured["timeout_seconds"], 900)
        self.assertIn("--task", captured["command"])
        self.assertIn("Fix the failing Python unittest suite.", captured["command"])
        self.assertIn("--temperature", captured["command"])
        contents = [message.content for message in result["messages"]]
        self.assertIn("Route: pi-scratch-run", contents)
        self.assertIn("Prepare: Pi scratch-run command built", contents)
        self.assertIn("Invoke: Pi scratch run succeeded", contents)
        self.assertIn("Pi scratch run succeeded.", contents[-1])
        self.assertIn("Final diff: /tmp/pi-run/artifacts/final-diff.patch", contents[-1])
        self.assertEqual(
            result["node_sequence"],
            ["intake", "route", "pi_prepare", "pi_invoke", "finalize"],
        )
        self.assertTrue(result["pi_result"]["manifest"]["success"])
        ledger = _load_jsonl(run_ledger_path())
        self.assertEqual(ledger[0]["route_decision"], "pi-scratch-run")
        self.assertEqual(ledger[0]["pi_run_dir"], "/tmp/pi-run")
        self.assertTrue(ledger[0]["pi_success"])

    def test_pi_failure_summarizes_without_adapter_telemetry(self) -> None:
        def fake_pi_runner(command, timeout_seconds):
            return {
                "returncode": 1,
                "stdout": "",
                "stderr": "sidecar health check failed",
                "manifest": {},
                "timed_out": False,
            }

        graph = build_test_graph(lambda payload: {"choices": []}, fake_pi_runner)
        result = graph.invoke(
            {"messages": [HumanMessage(content="/pi Fix the failing Python unittest suite.")]},
            config=TEST_CONFIG,
        )

        self.assertIn("Pi scratch run failed before manifest output.", result["messages"][-1].content)
        self.assertIn("sidecar health check failed", result["messages"][-1].content)
        ledger = _load_jsonl(run_ledger_path())
        self.assertEqual(ledger[0]["status"], "failed")
        self.assertFalse(Path(adapter_telemetry_path()).exists())

    def test_same_thread_turns_reset_run_context_and_do_not_leak_adapter_correlation(self) -> None:
        def fake_runner(payload: Mapping[str, Any]):
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

        first = graph.invoke(
            {
                "messages": [
                    HumanMessage(content="/specialized S02 explain the repeated-prefix runtime path briefly")
                ]
            },
            config=TEST_CONFIG,
        )
        second = graph.invoke(
            {"messages": [HumanMessage(content="/specialized TOOL please run tools")]},
            config=TEST_CONFIG,
        )

        self.assertNotEqual(first["run_id"], second["run_id"])
        self.assertEqual(
            first["node_sequence"],
            ["intake", "route", "specialized_prepare", "specialized_invoke", "finalize"],
        )
        self.assertEqual(second["node_sequence"], ["intake", "route", "finalize"])
        self.assertEqual(second.get("adapter_request_id", ""), "")
        self.assertEqual(second["route_decision"], "out-of-scope")

        ledger = _load_jsonl(run_ledger_path())
        self.assertEqual(len(ledger), 2)
        self.assertEqual(ledger[0]["adapter_request_id"], first["adapter_request_id"])
        self.assertEqual(ledger[1]["adapter_request_id"], "")
        self.assertEqual(ledger[1]["node_sequence"], ["intake", "route", "finalize"])


class PayloadTests(unittest.TestCase):
    def test_pi_command_uses_argument_list(self) -> None:
        command = build_pi_command(
            task="Fix tests; do not escape",
            run_id="cockpit-run-123",
            temperature=0.2,
            max_tokens=4096,
        )
        self.assertEqual(command[0], "python3")
        self.assertIn("--run-id", command)
        self.assertIn("cockpit-run-123", command)
        self.assertIn("Fix tests; do not escape", command)
        self.assertIn("--max-tokens", command)

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


def _fake_pi_runner(command, timeout_seconds):
    return {
        "returncode": 2,
        "stdout": "",
        "stderr": "fake pi runner was not configured",
        "manifest": {},
        "timed_out": False,
    }


if __name__ == "__main__":
    unittest.main()

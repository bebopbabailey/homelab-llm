import json
import os
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from omlx_runtime_client import (
    OmlxRuntimeClient,
    OmlxRuntimeClientError,
    OmlxRuntimeResponse,
    append_jsonl_record,
    build_failure_record,
    build_success_record,
)

from orchestration_cockpit.observability import (
    adapter_telemetry_path,
    append_node_sequence,
    append_run_ledger_record,
    build_run_ledger_record,
    elapsed_seconds,
    new_adapter_request_id,
    new_run_id,
    now_utc,
    payload_manifest_hash,
    resolve_thread_id,
)
from orchestration_cockpit.routing import RouteDecision, decide_route
from orchestration_cockpit.state import CockpitState

REPO_ROOT = Path(__file__).resolve().parents[4]
FIXTURE_SPECS_PATH = REPO_ROOT / "services" / "omlx-runtime" / "fixtures" / "phase3_fixture_specs.json"


class SpecializedInvoker(Protocol):
    def __call__(self, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        ...


def intake_node(
    state: CockpitState,
    config: RunnableConfig | None = None,
) -> dict[str, Any]:
    return {
        "thread_id": resolve_thread_id(state, config),
        "run_id": new_run_id(),
        "started_at": now_utc(),
        "mission_mode": "ordinary",
        "route_decision": "",
        "route_reason": "",
        "fixture_id": "",
        "node_sequence": ["intake"],
        "adapter_request_id": "",
        "specialized_payload": {},
        "specialized_result": {},
        "final_text": "",
        "error": "",
        "messages": [AIMessage(content="Intake: mission received")],
    }


def route_node(state: CockpitState) -> dict[str, Any]:
    latest_text = _latest_human_text(state)
    decision = decide_route(latest_text)
    return {
        "mission_mode": decision.mission_mode,
        "route_decision": decision.route_decision,
        "route_reason": decision.route_reason,
        "fixture_id": decision.fixture_id or "",
        "node_sequence": append_node_sequence(state, "route"),
        "messages": [AIMessage(content=_render_route_message(decision))],
    }


def ordinary_placeholder_node(state: CockpitState) -> dict[str, Any]:
    latest_text = _latest_human_text(state)
    final_text = (
        "Ordinary placeholder path: phase 4 keeps commodity model calls out of scope. "
        f"Received ordinary mission text: {latest_text or '[empty]'}"
    )
    return {
        "final_text": final_text,
        "node_sequence": append_node_sequence(state, "ordinary_placeholder"),
        "messages": [AIMessage(content="Ordinary: deterministic placeholder path selected")],
    }


def specialized_prepare_node(state: CockpitState) -> dict[str, Any]:
    fixture_id = state.get("fixture_id") or ""
    decision = decide_route(_latest_human_text(state))
    node_sequence = append_node_sequence(state, "specialized_prepare")
    if decision.route_decision != "specialized-runtime":
        return {
            "error": decision.route_reason,
            "node_sequence": node_sequence,
        }
    payload = build_specialized_payload(
        fixture_id=fixture_id,
        mission_text=decision.mission_text,
        model=os.environ.get("OMLX_RUNTIME_MODEL", "Qwen3-4B-Instruct-2507-4bit"),
    )
    return {
        "specialized_payload": payload,
        "node_sequence": node_sequence,
        "messages": [AIMessage(content=f"Prepare: specialized payload built for fixture {fixture_id}")],
    }


def make_specialized_invoke_node(
    invoker: SpecializedInvoker | None = None,
) -> Callable[[CockpitState], dict[str, Any]]:
    def specialized_invoke_node(state: CockpitState) -> dict[str, Any]:
        payload = state.get("specialized_payload")
        node_sequence = append_node_sequence(state, "specialized_invoke")
        request_id = state.get("adapter_request_id") or new_adapter_request_id()
        if not isinstance(payload, Mapping):
            return {
                "adapter_request_id": request_id,
                "node_sequence": node_sequence,
                "error": "specialized payload was not prepared",
            }

        try:
            if invoker is not None:
                body = dict(invoker(payload))
                _record_adapter_success(
                    request_id=request_id,
                    state=state,
                    payload=payload,
                    body=body,
                    response=None,
                )
            else:
                response = default_specialized_client().chat_completions(payload)
                body = response.body
                _record_adapter_success(
                    request_id=request_id,
                    state=state,
                    payload=payload,
                    body=body,
                    response=response,
                )
        except OmlxRuntimeClientError as exc:
            _record_adapter_failure(
                request_id=request_id,
                state=state,
                payload=payload,
                failure_class=exc.failure_class,
                error_message=str(exc),
            )
            return {
                "adapter_request_id": request_id,
                "node_sequence": node_sequence,
                "messages": [AIMessage(content=f"Invoke: omlx-runtime request {request_id} failed")],
                "error": f"{exc.failure_class}: {exc}",
            }
        except Exception as exc:  # pragma: no cover - defensive local surfacing
            _record_adapter_failure(
                request_id=request_id,
                state=state,
                payload=payload,
                failure_class="specialized_runtime_error",
                error_message=str(exc),
            )
            return {
                "adapter_request_id": request_id,
                "node_sequence": node_sequence,
                "messages": [AIMessage(content=f"Invoke: omlx-runtime request {request_id} failed")],
                "error": f"specialized_runtime_error: {exc}",
            }

        return {
            "adapter_request_id": request_id,
            "node_sequence": node_sequence,
            "messages": [AIMessage(content=f"Invoke: omlx-runtime request {request_id} sent")],
            "specialized_result": body,
        }

    return specialized_invoke_node


def finalize_node(state: CockpitState) -> dict[str, Any]:
    route_decision = state.get("route_decision")
    node_sequence = append_node_sequence(state, "finalize")
    if route_decision == "ordinary-placeholder":
        final_text = state.get("final_text") or "Ordinary placeholder path completed."
        status = "completed"
    elif route_decision == "specialized-runtime":
        if state.get("error"):
            final_text = f"Specialized runtime failed: {state['error']}"
            status = "failed"
        else:
            final_text = _summarize_specialized_result(state.get("specialized_result"))
            status = "completed"
    else:
        reason = state.get("route_reason") or state.get("error") or "request is out of scope"
        final_text = f"Out of scope: {reason}"
        status = "out-of-scope"

    finished_at = now_utc()
    append_run_ledger_record(
        build_run_ledger_record(
            state=state,
            node_sequence=node_sequence,
            status=status,
            finished_at=finished_at,
            latency_seconds=elapsed_seconds(state.get("started_at"), finished_at),
        )
    )
    return {
        "final_text": final_text,
        "node_sequence": node_sequence,
        "messages": [AIMessage(content=final_text)],
    }


def route_edge(state: CockpitState) -> str:
    decision = state.get("route_decision")
    if decision == "ordinary-placeholder":
        return "ordinary_placeholder"
    if decision == "specialized-runtime":
        return "specialized_prepare"
    return "finalize"


def build_specialized_payload(*, fixture_id: str, mission_text: str, model: str) -> dict[str, Any]:
    spec = load_fixture_spec(fixture_id)
    system_template = spec["system_template"]
    shared_block = spec["shared_block"]
    suffix_template = spec["suffix_template"]
    fixture = spec["fixture"]
    helper_index = int(fixture_id[-1]) if fixture_id[-1].isdigit() else 1
    shared = "".join(
        shared_block.format(index=index) for index in range(int(fixture["shared_block_repetitions"]))
    )
    suffix = "".join(
        suffix_template.format(variant=fixture_id, helper_index=helper_index)
        for _ in range(int(fixture["variant_suffix_repetitions"]))
    )
    user_content = f"{shared}{suffix}OPERATOR MISSION: {mission_text}\n"
    return {
        "model": model,
        "messages": [
            {"role": "system", "content": system_template},
            {"role": "user", "content": user_content},
        ],
        "temperature": 0,
        "top_p": 1,
        "max_tokens": int(fixture["max_tokens"]),
        "stream": False,
    }


def load_fixture_spec(fixture_id: str) -> dict[str, Any]:
    data = json.loads(FIXTURE_SPECS_PATH.read_text(encoding="utf-8"))
    fixture = next((item for item in data["fixtures"] if item["id"] == fixture_id), None)
    if fixture is None:
        raise ValueError(f"unknown fixture id: {fixture_id}")
    return {
        "system_template": data["system_template"],
        "shared_block": data["shared_block"],
        "suffix_template": data["suffix_template"],
        "fixture": fixture,
    }


def default_specialized_client() -> OmlxRuntimeClient:
    base_url = os.environ.get("OMLX_RUNTIME_BASE_URL", "http://127.0.0.1:8129")
    bearer_token = os.environ.get("OMLX_RUNTIME_BEARER_TOKEN", "")
    if not bearer_token:
        raise RuntimeError("OMLX_RUNTIME_BEARER_TOKEN is required for specialized missions")
    timeout_seconds = float(os.environ.get("OMLX_RUNTIME_TIMEOUT_SECONDS", "120"))
    return OmlxRuntimeClient(
        base_url=base_url,
        bearer_token=bearer_token,
        timeout_seconds=timeout_seconds,
    )


def _latest_human_text(state: CockpitState) -> str:
    messages = state.get("messages", [])
    for message in reversed(messages):
        if isinstance(message, HumanMessage):
            content = message.content
            if isinstance(content, str):
                return content
            return str(content)
    return ""


def _render_route_message(decision: RouteDecision) -> str:
    if decision.route_decision == "specialized-runtime":
        return f"Route: specialized-runtime (fixture {decision.fixture_id})"
    if decision.route_decision == "ordinary-placeholder":
        return "Route: ordinary-placeholder"
    return f"Route: out-of-scope ({decision.route_reason})"


def _summarize_specialized_result(result: Any) -> str:
    if not isinstance(result, Mapping):
        return "Specialized runtime completed, but the response body was not a JSON object."
    choices = result.get("choices")
    if isinstance(choices, list) and choices:
        first = choices[0]
        if isinstance(first, Mapping):
            message = first.get("message")
            if isinstance(message, Mapping):
                content = message.get("content")
                if isinstance(content, str) and content.strip():
                    return f"Specialized runtime completed: {content.strip()}"
    return f"Specialized runtime completed with response shape: {json.dumps(result, sort_keys=True)[:400]}"


def _record_adapter_success(
    *,
    request_id: str,
    state: CockpitState,
    payload: Mapping[str, Any],
    body: Mapping[str, Any],
    response: OmlxRuntimeResponse | None,
) -> None:
    encoded_body = json.dumps(dict(body), sort_keys=True, separators=(",", ":")).encode("utf-8")
    append_jsonl_record(
        adapter_telemetry_path(),
        build_success_record(
            request_id=request_id,
            fixture_id=state.get("fixture_id", ""),
            manifest_hash=payload_manifest_hash(payload),
            concurrency_class="graph-serial",
            target_model=str(payload.get("model", "")),
            endpoint=os.environ.get("OMLX_RUNTIME_BASE_URL", "http://127.0.0.1:8129"),
            status_code=response.status_code if response is not None else 200,
            latency_seconds=response.elapsed_seconds if response is not None else 0.0,
            request_bytes=response.request_bytes if response is not None else len(json.dumps(dict(payload)).encode("utf-8")),
            response_bytes=response.response_bytes if response is not None else len(encoded_body),
        ),
    )


def _record_adapter_failure(
    *,
    request_id: str,
    state: CockpitState,
    payload: Mapping[str, Any],
    failure_class: str,
    error_message: str,
) -> None:
    append_jsonl_record(
        adapter_telemetry_path(),
        build_failure_record(
            request_id=request_id,
            fixture_id=state.get("fixture_id", ""),
            manifest_hash=payload_manifest_hash(payload),
            concurrency_class="graph-serial",
            target_model=str(payload.get("model", "")),
            endpoint=os.environ.get("OMLX_RUNTIME_BASE_URL", "http://127.0.0.1:8129"),
            failure_class=failure_class,
            error_message=error_message,
        ),
    )

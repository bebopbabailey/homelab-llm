#!/usr/bin/env python3
"""Authoritative OpenCode -> GPT-OSS 20B constrained-contract pilot shim.

The shim accepts the smallest observed OpenCode one-shot ingress surface,
translates exact allowlisted prompts into exact `/v1/responses` backend payloads,
records raw evidence, and returns a caller-visible JSON summary as streamed text.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from itertools import count
from pathlib import Path
from typing import Any
from urllib import error, request


PLAIN_PROMPT = "Reply with exactly: pilot-plain-ok"
NOOP_PROMPT = "Use the noop tool exactly once, then stop."
SET_OK_PROMPT = "Use the set_ok tool exactly once with ok=true, then stop."

PUBLIC_MODEL_ID = "test"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def json_dumps(data: Any) -> str:
    return json.dumps(data, ensure_ascii=True, separators=(",", ":"), sort_keys=True)


def normalize_prompt(raw: str) -> str:
    text = raw.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in {"'", '"'}:
        text = text[1:-1].strip()
    return text


def socket_listening(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def process_alive(pidfile: Path | None) -> bool | None:
    if pidfile is None or not pidfile.exists():
        return None
    try:
        pid = int(pidfile.read_text().strip())
    except (ValueError, OSError):
        return None
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def studio_utility() -> Path:
    return repo_root() / "platform" / "ops" / "scripts" / "studio_run_utility.sh"


def studio_json(studio_host: str, command: str) -> dict[str, Any]:
    proc = subprocess.run(
        [str(studio_utility()), "--host", studio_host, "--", command],
        text=True,
        capture_output=True,
    )
    stdout = proc.stdout.strip()
    if proc.returncode != 0:
        return {"ok": False, "error": proc.stderr.strip() or stdout or f"returncode={proc.returncode}"}
    try:
        return {"ok": True, "result": json.loads(stdout.splitlines()[-1]) if stdout else None}
    except json.JSONDecodeError:
        return {"ok": False, "error": f"invalid json: {stdout}"}


def remote_process_alive(studio_host: str, pidfile: str | None) -> bool | None:
    if pidfile is None:
        return None
    command = (
        "python3 -c "
        + json.dumps(
            (
                "import json, os, sys; pidfile=sys.argv[1]; "
                "alive=None; "
                "path_exists=os.path.exists(pidfile); "
                "pid=None; "
                "if path_exists:\n"
                "    try:\n"
                "        pid=int(open(pidfile).read().strip())\n"
                "        os.kill(pid,0)\n"
                "        alive=True\n"
                "    except OSError:\n"
                "        alive=False\n"
                "    except Exception:\n"
                "        alive=None\n"
                "print(json.dumps({'alive': alive, 'pid': pid, 'pidfile': pidfile}))"
            )
        )
        + " "
        + json.dumps(pidfile)
    )
    result = studio_json(studio_host, command)
    if not result["ok"] or result["result"] is None:
        return None
    return result["result"].get("alive")


def remote_port_listening(studio_host: str, port: int) -> bool | None:
    command = (
        "python3 -c "
        + json.dumps(
            (
                "import json, socket, sys; "
                "port=int(sys.argv[1]); s=socket.socket(); s.settimeout(1.0); "
                "ok=True\n"
                "try:\n"
                "    s.connect(('127.0.0.1', port))\n"
                "except OSError:\n"
                "    ok=False\n"
                "finally:\n"
                "    s.close()\n"
                "print(json.dumps({'listening': ok, 'port': port}))"
            )
        )
        + f" {port}"
    )
    result = studio_json(studio_host, command)
    if not result["ok"] or result["result"] is None:
        return None
    return result["result"].get("listening")


def scenario_definition(prompt: str) -> dict[str, Any] | None:
    if prompt == PLAIN_PROMPT:
        return {"scenario_id": "plain", "tool": None, "expected_args": None, "store": False}
    if prompt == NOOP_PROMPT:
        return {
            "scenario_id": "noop",
            "tool": {
                "type": "function",
                "name": "noop",
                "description": "noop",
                "parameters": {"type": "object", "properties": {}},
            },
            "expected_args": {},
            "store": True,
        }
    if prompt == SET_OK_PROMPT:
        return {
            "scenario_id": "set_ok",
            "tool": {
                "type": "function",
                "name": "set_ok",
                "description": "set ok",
                "parameters": {
                    "type": "object",
                    "properties": {"ok": {"type": "boolean"}},
                    "required": ["ok"],
                    "additionalProperties": False,
                },
            },
            "expected_args": {"ok": True},
            "store": True,
        }
    return None


def build_backend_payload(served_model: str, scenario: dict[str, Any], prompt: str) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": served_model,
        "input": prompt,
        "temperature": 0.0,
    }
    if scenario["tool"] is not None:
        payload.update(
            {
                "tools": [scenario["tool"]],
                "tool_choice": "auto",
                "store": True,
            }
        )
    else:
        payload["store"] = False
    return payload


def followup_payload(served_model: str, previous_response_id: str, call_id: str) -> dict[str, Any]:
    return {
        "model": served_model,
        "previous_response_id": previous_response_id,
        "input": [
            {
                "type": "function_call_output",
                "call_id": call_id,
                "output": "{\"ok\":true}",
            }
        ],
    }


def http_json(
    method: str,
    url: str,
    payload: dict[str, Any] | None = None,
    timeout: float = 120.0,
    studio_host: str | None = None,
) -> dict[str, Any]:
    if studio_host is not None:
        payload_json = None if payload is None else json.dumps(payload)
        payload_b64 = "-" if payload_json is None else base64.b64encode(payload_json.encode("utf-8")).decode("ascii")
        remote_code = """import base64, json, sys, urllib.request, urllib.error
method = sys.argv[2]
url = sys.argv[3]
payload_b64 = sys.argv[4]
timeout = float(sys.argv[5])
data = None if payload_b64 == "-" else base64.b64decode(payload_b64.encode("ascii"))
req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method=method)
try:
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8", "replace")
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = None
        result = {"http_status": resp.getcode(), "raw_body": raw, "parsed_json": parsed, "transport_error": None}
except urllib.error.HTTPError as exc:
    raw = exc.read().decode("utf-8", "replace")
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = None
    result = {"http_status": exc.code, "raw_body": raw, "parsed_json": parsed, "transport_error": None}
except Exception as exc:
    result = {"http_status": None, "raw_body": None, "parsed_json": None, "transport_error": {"type": type(exc).__name__, "message": str(exc)}}
print(json.dumps(result))"""
        remote_code_b64 = base64.b64encode(remote_code.encode("utf-8")).decode("ascii")
        result = studio_json(
            studio_host,
            " ".join(
                [
                    "/usr/bin/python3",
                    "-c",
                    json.dumps("import base64,sys; exec(base64.b64decode(sys.argv[1]).decode('utf-8'))"),
                    json.dumps(remote_code_b64),
                    json.dumps(method),
                    json.dumps(url),
                    json.dumps(payload_b64),
                    json.dumps(str(timeout)),
                ]
            ),
        )
        if result["ok"]:
            return result["result"]
        return {"http_status": None, "raw_body": None, "parsed_json": None, "transport_error": {"type": "RemoteCommandError", "message": result["error"]}}

    body = None if payload is None else json.dumps(payload).encode("utf-8")
    req = request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method=method,
    )
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", "replace")
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                parsed = None
            return {"http_status": resp.getcode(), "raw_body": raw, "parsed_json": parsed, "transport_error": None}
    except error.HTTPError as exc:
        raw = exc.read().decode("utf-8", "replace")
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = None
        return {"http_status": exc.code, "raw_body": raw, "parsed_json": parsed, "transport_error": None}
    except Exception as exc:  # pragma: no cover - integration error path
        return {
            "http_status": None,
            "raw_body": None,
            "parsed_json": None,
            "transport_error": {"type": type(exc).__name__, "message": str(exc)},
        }


def extract_callable(resp_json: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(resp_json, dict):
        return {
            "callable_exists": False,
            "callable_type": None,
            "callable_name": None,
            "callable_args_raw": None,
            "callable_args_parsed": None,
            "call_id": None,
            "response_id": None,
        }
    output = resp_json.get("output")
    callable_item = None
    if isinstance(output, list):
        for item in output:
            if isinstance(item, dict) and item.get("type") in {"function_call", "mcp_call"}:
                callable_item = item
                break
    args_raw = None
    args_parsed = None
    if isinstance(callable_item, dict):
        args_raw = callable_item.get("arguments")
        if isinstance(args_raw, str):
            try:
                args_parsed = json.loads(args_raw)
            except json.JSONDecodeError:
                args_parsed = None
    return {
        "callable_exists": callable_item is not None,
        "callable_type": None if callable_item is None else callable_item.get("type"),
        "callable_name": None if callable_item is None else callable_item.get("name"),
        "callable_args_raw": args_raw,
        "callable_args_parsed": args_parsed,
        "call_id": None if callable_item is None else callable_item.get("call_id"),
        "response_id": resp_json.get("id"),
    }


def score_initial(
    initial: dict[str, Any],
    scenario: dict[str, Any],
) -> dict[str, Any]:
    parsed = initial["parsed_json"]
    callable_info = extract_callable(parsed)
    expected_args = scenario["expected_args"]
    shape_success = bool(
        initial["http_status"] == 200
        and isinstance(parsed, dict)
        and callable_info["callable_exists"]
        and callable_info["callable_args_parsed"] is not None
    )
    broad_semantic_success = bool(
        shape_success
        and callable_info["callable_type"] in {"function_call", "mcp_call"}
        and callable_info["callable_name"] == scenario["tool"]["name"]
        and callable_info["callable_args_parsed"] == expected_args
    )
    strict_protocol_clean_success = bool(
        shape_success
        and callable_info["callable_type"] == "function_call"
        and callable_info["callable_name"] == scenario["tool"]["name"]
        and callable_info["callable_args_parsed"] == expected_args
    )
    reasoning_only_no_call = bool(initial["http_status"] == 200 and isinstance(parsed, dict) and not callable_info["callable_exists"])
    protocol_shape_drift = bool(callable_info["callable_exists"] and not strict_protocol_clean_success)
    return {
        **callable_info,
        "shape_success": shape_success,
        "broad_semantic_success": broad_semantic_success,
        "strict_protocol_clean_success": strict_protocol_clean_success,
        "reasoning_only_no_call": reasoning_only_no_call,
        "protocol_shape_drift": protocol_shape_drift,
    }


def score_followup(resp: dict[str, Any]) -> dict[str, Any]:
    parsed = resp["parsed_json"]
    output = parsed.get("output") if isinstance(parsed, dict) else None
    next_callable = None
    if isinstance(output, list):
        for item in output:
            if isinstance(item, dict) and item.get("type") in {"function_call", "mcp_call"}:
                next_callable = item
                break
    follow_up_shape_success = bool(resp["http_status"] == 200 and isinstance(parsed, dict) and isinstance(output, list))
    follow_up_semantic_success = bool(follow_up_shape_success and next_callable is None)
    return {
        "follow_up_shape_success": follow_up_shape_success,
        "follow_up_semantic_success": follow_up_semantic_success,
        "another_tool_call_requested": next_callable is not None,
    }


def backend_attempt(
    *,
    backend_base: str,
    served_model: str,
    scenario: dict[str, Any],
    prompt: str,
    payload: dict[str, Any],
    studio_host: str | None,
) -> dict[str, Any]:
    initial = http_json("POST", f"{backend_base}/responses", payload=payload, studio_host=studio_host)
    record: dict[str, Any] = {
        "initial": initial,
        "initial_score": {},
        "retrieval": None,
        "retrieval_success": False,
        "followup": None,
        "followup_score": None,
    }
    if scenario["tool"] is None:
        record["initial_score"] = {
            "response_id": None if not isinstance(initial["parsed_json"], dict) else initial["parsed_json"].get("id"),
            "shape_success": initial["http_status"] == 200 and isinstance(initial["parsed_json"], dict),
            "broad_semantic_success": None,
            "strict_protocol_clean_success": None,
            "reasoning_only_no_call": None,
            "protocol_shape_drift": None,
            "callable_exists": False,
            "callable_type": None,
            "callable_name": None,
            "callable_args_raw": None,
            "callable_args_parsed": None,
            "call_id": None,
        }
        return record

    record["initial_score"] = score_initial(initial, scenario)
    response_id = record["initial_score"]["response_id"]
    call_id = record["initial_score"]["call_id"]

    if response_id:
        retrieval = http_json("GET", f"{backend_base}/responses/{response_id}", studio_host=studio_host)
        record["retrieval"] = retrieval
        record["retrieval_success"] = bool(
            retrieval["http_status"] == 200
            and isinstance(retrieval["parsed_json"], dict)
            and retrieval["parsed_json"].get("id") == response_id
        )

    if record["retrieval_success"] and call_id and record["initial_score"]["callable_type"] == "function_call":
        followup = http_json(
            "POST",
            f"{backend_base}/responses",
            payload=followup_payload(served_model, response_id, call_id),
            studio_host=studio_host,
        )
        record["followup"] = followup
        record["followup_score"] = score_followup(followup)

    return record


def classify_trial(primary: dict[str, Any], direct: dict[str, Any], scenario_id: str) -> str:
    if scenario_id == "plain":
        if primary["initial"]["http_status"] == 200 and direct["initial"]["http_status"] == 200:
            return "caller_and_direct_both_clean"
        if primary["initial"]["http_status"] == 200 and direct["initial"]["http_status"] != 200:
            return "caller_path_clean_direct_failed"
        if primary["initial"]["http_status"] != 200 and direct["initial"]["http_status"] == 200:
            return "direct_clean_caller_path_failed"
        return "both_failed_backend_or_runtime"

    p = primary["initial_score"]
    d = direct["initial_score"]
    if p["strict_protocol_clean_success"] and d["strict_protocol_clean_success"]:
        if primary["retrieval_success"] and direct["retrieval_success"]:
            return "caller_and_direct_both_clean"
        return "store_or_retrieval_confound"
    if d["strict_protocol_clean_success"] and not p["strict_protocol_clean_success"]:
        return "direct_clean_caller_path_failed"
    if p["strict_protocol_clean_success"] and not d["strict_protocol_clean_success"]:
        return "caller_path_clean_direct_failed"
    if p["protocol_shape_drift"] or d["protocol_shape_drift"]:
        return "normalized_payload_mutated_and_failed"
    if primary["retrieval_success"] != direct["retrieval_success"]:
        return "store_or_retrieval_confound"
    return "both_failed_backend_or_runtime"


def caller_summary(
    trial_id: str,
    scenario_id: str,
    prompt: str,
    primary: dict[str, Any],
    direct: dict[str, Any],
    classification: str,
) -> dict[str, Any]:
    if scenario_id == "plain":
        return {
            "trial_id": trial_id,
            "scenario_id": scenario_id,
            "prompt": prompt,
            "classification": classification,
            "caller_path_http_status": primary["initial"]["http_status"],
            "direct_http_status": direct["initial"]["http_status"],
            "caller_path_text": (
                primary["initial"]["parsed_json"].get("output_text")
                if isinstance(primary["initial"]["parsed_json"], dict)
                else None
            ),
            "direct_text": (
                direct["initial"]["parsed_json"].get("output_text")
                if isinstance(direct["initial"]["parsed_json"], dict)
                else None
            ),
        }
    p = primary["initial_score"]
    d = direct["initial_score"]
    return {
        "trial_id": trial_id,
        "scenario_id": scenario_id,
        "prompt": prompt,
        "classification": classification,
        "caller_path": {
            "http_status": primary["initial"]["http_status"],
            "response_id": p["response_id"],
            "call_id": p["call_id"],
            "strict_protocol_clean_success": p["strict_protocol_clean_success"],
            "broad_semantic_success": p["broad_semantic_success"],
            "reasoning_only_no_call": p["reasoning_only_no_call"],
            "protocol_shape_drift": p["protocol_shape_drift"],
            "retrieval_success": primary["retrieval_success"],
            "follow_up_semantic_success": None
            if primary["followup_score"] is None
            else primary["followup_score"]["follow_up_semantic_success"],
        },
        "direct_control": {
            "http_status": direct["initial"]["http_status"],
            "response_id": d["response_id"],
            "call_id": d["call_id"],
            "strict_protocol_clean_success": d["strict_protocol_clean_success"],
            "broad_semantic_success": d["broad_semantic_success"],
            "reasoning_only_no_call": d["reasoning_only_no_call"],
            "protocol_shape_drift": d["protocol_shape_drift"],
            "retrieval_success": direct["retrieval_success"],
            "follow_up_semantic_success": None
            if direct["followup_score"] is None
            else direct["followup_score"]["follow_up_semantic_success"],
        },
    }


@dataclass
class ServerState:
    backend_base: str
    served_model: str
    artifact_dir: Path
    backend_host: str
    backend_port: int
    backend_pidfile: Path | None
    backend_pidfile_remote: str | None
    studio_host: str | None
    trial_counter: Any


class PilotHandler(BaseHTTPRequestHandler):
    server_version = "OpenCodeGPTOSS20BPilot/1.0"
    protocol_version = "HTTP/1.1"

    @property
    def state(self) -> ServerState:
        return self.server.state  # type: ignore[attr-defined]

    def log_message(self, *_args: Any) -> None:
        return

    def _send_json(self, code: int, obj: dict[str, Any]) -> None:
        body = json.dumps(obj, ensure_ascii=True).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)
        self.close_connection = True

    def _send_sse_text(self, text: str) -> None:
        def chunk(obj: dict[str, Any]) -> bytes:
            return f"data: {json_dumps(obj)}\n\n".encode("utf-8")

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.end_headers()

        chunks = [
            {
                "id": "chatcmpl-pilot",
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": PUBLIC_MODEL_ID,
                "choices": [{"index": 0, "delta": {"role": "assistant"}, "finish_reason": None}],
            },
            {
                "id": "chatcmpl-pilot",
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": PUBLIC_MODEL_ID,
                "choices": [{"index": 0, "delta": {"content": text}, "finish_reason": None}],
            },
            {
                "id": "chatcmpl-pilot",
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": PUBLIC_MODEL_ID,
                "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
            },
        ]
        for obj in chunks:
            self.wfile.write(chunk(obj))
            self.wfile.flush()
        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()
        self.close_connection = True

    def do_GET(self) -> None:
        if self.path == "/v1/models":
            self._send_json(
                200,
                {"object": "list", "data": [{"id": PUBLIC_MODEL_ID, "object": "model", "created": 0, "owned_by": "pilot"}]},
            )
            return
        self._send_json(404, {"error": "unsupported path", "path": self.path})

    def do_POST(self) -> None:
        if self.path != "/v1/chat/completions":
            self._send_json(404, {"error": "unsupported path", "path": self.path})
            return
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._send_json(400, {"error": "invalid content length"})
            return
        raw = self.rfile.read(content_length).decode("utf-8", "replace")
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            self._send_json(400, {"error": "invalid json"})
            return

        messages = payload.get("messages")
        if not isinstance(messages, list) or not messages:
            self._send_json(400, {"error": "unsupported request shape", "detail": "messages[] required"})
            return
        user_messages = [m for m in messages if isinstance(m, dict) and m.get("role") == "user" and isinstance(m.get("content"), str)]
        if not user_messages:
            self._send_json(400, {"error": "unsupported request shape", "detail": "final user content required"})
            return
        prompt = normalize_prompt(user_messages[-1]["content"])
        scenario = scenario_definition(prompt)
        if scenario is None:
            self._send_json(400, {"error": "unsupported pilot scenario", "prompt": prompt})
            return

        trial_id = f"trial-{next(self.state.trial_counter):03d}-{scenario['scenario_id']}"
        normalized_payload = build_backend_payload(self.state.served_model, scenario, prompt)
        primary = backend_attempt(
            backend_base=self.state.backend_base,
            served_model=self.state.served_model,
            scenario=scenario,
            prompt=prompt,
            payload=normalized_payload,
            studio_host=self.state.studio_host,
        )
        direct = backend_attempt(
            backend_base=self.state.backend_base,
            served_model=self.state.served_model,
            scenario=scenario,
            prompt=prompt,
            payload=normalized_payload,
            studio_host=self.state.studio_host,
        )
        classification = classify_trial(primary, direct, scenario["scenario_id"])
        summary = caller_summary(trial_id, scenario["scenario_id"], prompt, primary, direct, classification)

        trial_record = {
            "trial_id": trial_id,
            "utc_timestamp": utc_now(),
            "scenario_id": scenario["scenario_id"],
            "caller_payload": payload,
            "normalized_backend_payload": normalized_payload,
            "primary_backend_attempt": primary,
            "direct_backend_control": direct,
            "classification": classification,
            "caller_visible_interpreted_result": summary,
            "backend_process_alive": (
                remote_process_alive(self.state.studio_host, self.state.backend_pidfile_remote)
                if self.state.studio_host
                else process_alive(self.state.backend_pidfile)
            ),
            "backend_port_listening": (
                remote_port_listening(self.state.studio_host, self.state.backend_port)
                if self.state.studio_host
                else socket_listening(self.state.backend_host, self.state.backend_port)
            ),
        }
        artifact_path = self.state.artifact_dir / f"{trial_id}.json"
        artifact_path.write_text(json.dumps(trial_record, indent=2, ensure_ascii=True) + "\n")

        self._send_sse_text(json.dumps(summary, sort_keys=True))


def serve(args: argparse.Namespace) -> int:
    artifact_dir = Path(args.artifact_dir).resolve()
    artifact_dir.mkdir(parents=True, exist_ok=True)
    state = ServerState(
        backend_base=args.backend_base.rstrip("/"),
        served_model=args.served_model,
        artifact_dir=artifact_dir,
        backend_host=args.backend_host,
        backend_port=args.backend_port,
        backend_pidfile=None if args.backend_pidfile is None or args.studio_host else Path(args.backend_pidfile),
        backend_pidfile_remote=args.backend_pidfile if args.studio_host else None,
        studio_host=args.studio_host,
        trial_counter=count(1),
    )
    httpd = ThreadingHTTPServer((args.host, args.port), PilotHandler)
    httpd.state = state  # type: ignore[attr-defined]
    print(json.dumps({"listening": f"http://{args.host}:{args.port}", "artifact_dir": str(artifact_dir)}), flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        return 0
    finally:
        httpd.server_close()
    return 0


def replay(args: argparse.Namespace) -> int:
    payload_path = Path(args.payload_json)
    payload = json.loads(payload_path.read_text())
    result = http_json("POST", f"{args.backend_base.rstrip('/')}/responses", payload=payload)
    sys.stdout.write(json.dumps(result, indent=2, ensure_ascii=True) + "\n")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)

    serve_parser = sub.add_parser("serve")
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, required=True)
    serve_parser.add_argument("--backend-base", required=True)
    serve_parser.add_argument("--served-model", required=True)
    serve_parser.add_argument("--artifact-dir", required=True)
    serve_parser.add_argument("--backend-host", default="127.0.0.1")
    serve_parser.add_argument("--backend-port", type=int, required=True)
    serve_parser.add_argument("--backend-pidfile")
    serve_parser.add_argument("--studio-host")
    serve_parser.set_defaults(func=serve)

    replay_parser = sub.add_parser("replay")
    replay_parser.add_argument("--backend-base", required=True)
    replay_parser.add_argument("--payload-json", required=True)
    replay_parser.set_defaults(func=replay)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

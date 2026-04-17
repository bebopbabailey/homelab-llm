#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import platform
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


QWEN_AGENT_INSTALL_SPEC = "qwen-agent==0.0.34"
QWEN_AGENT_IMPORT_HINT = [
    QWEN_AGENT_INSTALL_SPEC,
    "numpy",
    "soundfile",
    "python-dateutil",
    "pebble",
    "multiprocess",
    "timeout_decorator",
    "scipy",
    "sympy",
]

RAW_MARKUP_PATTERNS = (
    "<tool_call>",
    "</tool_call>",
    "<tool_response>",
    "</tool_response>",
    "✿FUNCTION✿",
    "✿ARGS✿",
    "✿RESULT✿",
)


@dataclass(frozen=True)
class FunctionSpec:
    name: str
    description: str
    parameters: dict[str, Any]
    execute: Callable[[dict[str, Any]], str]

    def as_qwen_function(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }


@dataclass(frozen=True)
class ProbeCase:
    name: str
    prompt: str
    functions: list[FunctionSpec]
    expected_function_name: str


def parse_bool_arg(value: str) -> bool:
    lowered = value.strip().lower()
    if lowered in {"1", "true", "yes", "on"}:
        return True
    if lowered in {"0", "false", "no", "off"}:
        return False
    raise argparse.ArgumentTypeError(f"invalid boolean value: {value}")


def contains_raw_tool_markup(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return any(token in value for token in RAW_MARKUP_PATTERNS)
    if isinstance(value, dict):
        return any(contains_raw_tool_markup(v) for v in value.values())
    if isinstance(value, list):
        return any(contains_raw_tool_markup(v) for v in value)
    return False


def normalize_jsonable(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, dict):
        return {str(k): normalize_jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [normalize_jsonable(v) for v in value]
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        return normalize_jsonable(model_dump())
    if hasattr(value, "__dict__"):
        return normalize_jsonable(vars(value))
    return repr(value)


def parse_json_arguments(raw: str) -> tuple[dict[str, Any] | None, str | None]:
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        return None, str(exc)
    if not isinstance(parsed, dict):
        return None, "arguments are not a JSON object"
    return parsed, None


def schema_validate_arguments(schema: dict[str, Any], arguments: dict[str, Any]) -> tuple[bool, str | None]:
    if schema.get("type") != "object":
        return False, "schema type is not object"
    properties = schema.get("properties", {})
    required = schema.get("required", [])
    additional_allowed = schema.get("additionalProperties", True)
    for key in required:
        if key not in arguments:
            return False, f"missing required key: {key}"
    if not additional_allowed:
        extras = set(arguments) - set(properties)
        if extras:
            return False, f"unexpected keys: {sorted(extras)}"
    for key, value in arguments.items():
        spec = properties.get(key)
        if not spec:
            continue
        expected_type = spec.get("type")
        if expected_type == "string" and not isinstance(value, str):
            return False, f"{key} is not a string"
    return True, None


def _object_schema(properties: dict[str, Any], required: list[str]) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": properties,
        "required": required,
        "additionalProperties": False,
    }


def _virtual_files() -> dict[str, str]:
    return {
        "main.py": 'print("hello from main")\n',
        "src/app.py": "def add(a, b):\n    return a + b\n",
    }


def _virtual_symbols() -> dict[str, str]:
    return {
        "ToolRunner": "class ToolRunner:\n    def run(self, tool_name, args):\n        ...\n",
        "Adder": "def add(a, b):\n    return a + b\n",
    }


def build_probe_cases() -> dict[str, ProbeCase]:
    files = _virtual_files()
    symbols = _virtual_symbols()

    def read_virtual_file(args: dict[str, Any]) -> str:
        path = args["path"]
        return files.get(path, f"missing:{path}")

    def search_virtual_repo(args: dict[str, Any]) -> str:
        query = args["query"]
        matches = sorted(name for name in list(files) + list(symbols) if query.lower() in name.lower())
        return json.dumps({"query": query, "matches": matches})

    def lookup_symbol(args: dict[str, Any]) -> str:
        name = args["name"]
        return symbols.get(name, f"missing:{name}")

    def run_virtual_lint(args: dict[str, Any]) -> str:
        path = args["path"]
        if path == "src/app.py":
            return json.dumps({"path": path, "status": "ok", "issues": []})
        return json.dumps({"path": path, "status": "missing", "issues": ["file not found"]})

    return {
        "one_function": ProbeCase(
            name="one_function",
            prompt="Call read_virtual_file for path main.py and nothing else.",
            expected_function_name="read_virtual_file",
            functions=[
                FunctionSpec(
                    name="read_virtual_file",
                    description="Read a known virtual file and return its contents.",
                    parameters=_object_schema(
                        {"path": {"type": "string", "description": "Virtual file path."}},
                        ["path"],
                    ),
                    execute=read_virtual_file,
                )
            ],
        ),
        "two_function": ProbeCase(
            name="two_function",
            prompt="Search the virtual repo for ToolRunner and nothing else.",
            expected_function_name="search_virtual_repo",
            functions=[
                FunctionSpec(
                    name="read_virtual_file",
                    description="Read a known virtual file and return its contents.",
                    parameters=_object_schema(
                        {"path": {"type": "string", "description": "Virtual file path."}},
                        ["path"],
                    ),
                    execute=read_virtual_file,
                ),
                FunctionSpec(
                    name="search_virtual_repo",
                    description="Search the virtual repo and return matching file or symbol names.",
                    parameters=_object_schema(
                        {"query": {"type": "string", "description": "Search query."}},
                        ["query"],
                    ),
                    execute=search_virtual_repo,
                ),
            ],
        ),
        "code_helper": ProbeCase(
            name="code_helper",
            prompt="Run the virtual lint helper on src/app.py and nothing else.",
            expected_function_name="run_virtual_lint",
            functions=[
                FunctionSpec(
                    name="lookup_symbol",
                    description="Look up a virtual symbol definition by name.",
                    parameters=_object_schema(
                        {"name": {"type": "string", "description": "Symbol name."}},
                        ["name"],
                    ),
                    execute=lookup_symbol,
                ),
                FunctionSpec(
                    name="run_virtual_lint",
                    description="Run a fake linter against a virtual source path.",
                    parameters=_object_schema(
                        {"path": {"type": "string", "description": "Virtual source path."}},
                        ["path"],
                    ),
                    execute=run_virtual_lint,
                ),
            ],
        ),
    }


def load_qwen_agent():
    try:
        import qwen_agent
        from qwen_agent.llm import get_chat_model
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            "Failed to import qwen-agent probe runtime. "
            f"Use uv run with: {', '.join(QWEN_AGENT_IMPORT_HINT)}"
        ) from exc
    return qwen_agent, get_chat_model


def _function_message(function_name: str, result: str, function_id: str = "1") -> dict[str, Any]:
    return {
        "role": "function",
        "name": function_name,
        "content": result,
        "extra": {"function_id": function_id},
    }


def _extract_function_id(first_response: list[dict[str, Any]]) -> str:
    for item in first_response:
        extra = item.get("extra") or {}
        if isinstance(extra, dict) and extra.get("function_id"):
            return str(extra["function_id"])
    return "1"


def _chat_once(
    llm: Any,
    *,
    messages: list[dict[str, Any]],
    functions: list[dict[str, Any]],
    use_raw_api: bool,
) -> list[dict[str, Any]]:
    kwargs = {
        "messages": messages,
        "functions": functions,
        "stream": use_raw_api,
        "delta_stream": False,
    }
    if not use_raw_api:
        kwargs["extra_generate_cfg"] = {"function_choice": "auto"}
    response = llm.chat(**kwargs)
    if not use_raw_api:
        return [dict(item) for item in response]
    last = None
    for chunk in response:
        last = chunk
    if last is None:
        return []
    return [dict(item) for item in last]


def run_probe_case(
    llm: Any,
    case: ProbeCase,
    *,
    repeats: int,
    use_raw_api: bool,
) -> dict[str, Any]:
    functions = [fn.as_qwen_function() for fn in case.functions]
    runs = []
    success_count = 0
    for attempt in range(1, repeats + 1):
        user_messages = [{"role": "user", "content": case.prompt}]
        first_response = []
        first_error = None
        try:
            first_response = _chat_once(
                llm,
                messages=user_messages,
                functions=functions,
                use_raw_api=use_raw_api,
            )
        except Exception as exc:  # noqa: BLE001
            first_error = repr(exc)
        callable_item = next((item for item in first_response if item.get("function_call")), None)
        function_name = None
        raw_arguments = None
        parsed_arguments = None
        parse_error = None
        schema_valid = False
        schema_error = None
        execution_ok = False
        function_result = None
        roundtrip = None
        function_matches = False
        final_text = ""
        roundtrip_error = None
        if callable_item:
            function_call = callable_item["function_call"]
            function_name = function_call.get("name")
            raw_arguments = function_call.get("arguments")
            parsed_arguments, parse_error = parse_json_arguments(raw_arguments or "")
            function_matches = function_name == case.expected_function_name
            fn_spec = next((fn for fn in case.functions if fn.name == function_name), None)
            if fn_spec and parsed_arguments is not None:
                schema_valid, schema_error = schema_validate_arguments(fn_spec.parameters, parsed_arguments)
                if schema_valid:
                    function_result = fn_spec.execute(parsed_arguments)
                    execution_ok = True
                    messages2 = user_messages + first_response + [
                        _function_message(function_name, function_result, _extract_function_id(first_response))
                    ]
                    try:
                        roundtrip = _chat_once(
                            llm,
                            messages=messages2,
                            functions=functions,
                            use_raw_api=use_raw_api,
                        )
                        final_text = " ".join(str(item.get("content", "")) for item in roundtrip if item.get("content"))
                    except Exception as exc:  # noqa: BLE001
                        roundtrip_error = repr(exc)
        run = {
            "attempt": attempt,
            "first_error": first_error,
            "callable_function_object": callable_item is not None,
            "function_name": function_name,
            "expected_function_name": case.expected_function_name,
            "function_name_correct": function_matches,
            "raw_arguments": raw_arguments,
            "parsed_arguments": parsed_arguments,
            "arguments_valid_json": parsed_arguments is not None,
            "arguments_schema_valid": schema_valid,
            "arguments_error": parse_error or schema_error,
            "downstream_execution_ok": execution_ok,
            "function_result": function_result,
            "roundtrip_completed": roundtrip is not None,
            "roundtrip_error": roundtrip_error,
            "final_assistant_text": final_text,
            "raw_markup_in_consumer_result": contains_raw_tool_markup(
                {
                    "first_response": first_response,
                    "roundtrip": roundtrip,
                    "raw_arguments": raw_arguments,
                    "final_assistant_text": final_text,
                }
            ),
            "first_response": first_response,
            "roundtrip_response": roundtrip,
        }
        if (
            run["callable_function_object"]
            and run["function_name_correct"]
            and run["arguments_valid_json"]
            and run["arguments_schema_valid"]
            and run["downstream_execution_ok"]
            and run["roundtrip_completed"]
            and not run["raw_markup_in_consumer_result"]
        ):
            success_count += 1
        runs.append(run)
    return {
        "case": case.name,
        "use_raw_api": use_raw_api,
        "attempts": repeats,
        "successes": success_count,
        "runs": runs,
    }


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(normalize_jsonable(payload), indent=2, sort_keys=True) + "\n")


def build_environment_payload(args: argparse.Namespace, qwen_agent_version: str) -> dict[str, Any]:
    return {
        "run_timestamp_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "qwen_agent_install_spec": QWEN_AGENT_INSTALL_SPEC,
        "qwen_agent_version": qwen_agent_version,
        "python_version": platform.python_version(),
        "backend_base_url": args.base_url,
        "model": args.model,
        "api_key_supplied": bool(args.api_key),
        "cases": args.case,
        "use_raw_api_values_tested": args.use_raw_api,
        "repeats": args.repeats,
    }


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    one_function_results = [r for r in results if r["case"] == "one_function"]
    one_function_pass = any(r["successes"] == r["attempts"] for r in one_function_results)
    other_any_success = any(r["successes"] > 0 for r in results if r["case"] != "one_function")
    any_case_success = any(r["successes"] > 0 for r in results)
    verdict = "fail"
    if one_function_pass and other_any_success:
        verdict = "pass"
    elif any_case_success:
        verdict = "partial"
    return {
        "verdict": verdict,
        "results": [
            {
                "case": result["case"],
                "use_raw_api": result["use_raw_api"],
                "attempts": result["attempts"],
                "successes": result["successes"],
            }
            for result in results
        ],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Probe a Qwen-Agent function-calling shadow path against an OpenAI-compatible backend.")
    parser.add_argument("--base-url", required=True, help="Backend base URL ending in /v1")
    parser.add_argument("--model", required=True, help="Served model id")
    parser.add_argument("--api-key", default="EMPTY", help="Backend API key or placeholder")
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--case", action="append", required=True, choices=sorted(build_probe_cases()))
    parser.add_argument("--use-raw-api", action="append", required=True, type=parse_bool_arg)
    parser.add_argument("--out-dir", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    qwen_agent, get_chat_model = load_qwen_agent()
    cases = build_probe_cases()
    out_dir = Path(args.out_dir)
    environment = build_environment_payload(args, getattr(qwen_agent, "__version__", "unknown"))
    write_json(out_dir / "environment.json", environment)
    results: list[dict[str, Any]] = []
    for use_raw_api in args.use_raw_api:
        llm = get_chat_model(
            {
                "model_type": "oai",
                "model": args.model,
                "model_server": args.base_url,
                "api_key": args.api_key,
                "generate_cfg": {
                    "fncall_prompt_type": "qwen",
                    "use_raw_api": use_raw_api,
                    "temperature": 0,
                    "max_tokens": 256,
                },
            }
        )
        for case_name in args.case:
            result = run_probe_case(llm, cases[case_name], repeats=args.repeats, use_raw_api=use_raw_api)
            results.append(result)
            raw_name = f"{case_name}-rawapi-{str(use_raw_api).lower()}.json"
            write_json(out_dir / "raw" / raw_name, result)
    summary = summarize(results)
    write_json(out_dir / "summary.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["verdict"] != "fail" else 1


if __name__ == "__main__":
    raise SystemExit(main())

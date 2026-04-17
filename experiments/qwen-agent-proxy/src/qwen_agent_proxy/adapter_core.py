from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any


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
class AdapterFunctionCall:
    name: str
    arguments: dict[str, Any]
    raw_arguments: str
    function_id: str | None = None


@dataclass(frozen=True)
class AdapterResult:
    status: str
    function_call: AdapterFunctionCall | None = None
    assistant_text: str = ""
    error: str | None = None
    raw_response: list[dict[str, Any]] | None = None
    use_raw_api: bool = False

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_qwen_agent():
    try:
        import qwen_agent
        from qwen_agent.llm import get_chat_model
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            "Failed to import qwen-agent adapter runtime. "
            f"Use uv run with: {', '.join(QWEN_AGENT_IMPORT_HINT)}"
        ) from exc
    return qwen_agent, get_chat_model


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


def convert_openai_tools_to_qwen_functions(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    functions = []
    for tool in tools:
        if tool.get("type") != "function":
            raise ValueError("only OpenAI function tools are supported")
        function = tool.get("function")
        if not isinstance(function, dict):
            raise ValueError("tool.function must be a dict")
        name = function.get("name")
        description = function.get("description", "")
        parameters = function.get("parameters")
        if not isinstance(name, str) or not name:
            raise ValueError("tool.function.name must be a non-empty string")
        if not isinstance(parameters, dict):
            raise ValueError("tool.function.parameters must be a dict")
        functions.append(
            {
                "name": name,
                "description": description,
                "parameters": parameters,
            }
        )
    return functions


class QwenAgentAdapter:
    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        api_key: str = "EMPTY",
        use_raw_api: bool = False,
        temperature: float = 0.0,
        max_tokens: int = 256,
    ) -> None:
        self.base_url = base_url
        self.model = model
        self.api_key = api_key
        self.use_raw_api = use_raw_api
        _qwen_agent, get_chat_model = load_qwen_agent()
        self.llm = get_chat_model(
            {
                "model_type": "oai",
                "model": model,
                "model_server": base_url,
                "api_key": api_key,
                "generate_cfg": {
                    "fncall_prompt_type": "qwen",
                    "use_raw_api": use_raw_api,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
            }
        )

    def _chat_once(self, *, messages: list[dict[str, Any]], functions: list[dict[str, Any]]) -> list[dict[str, Any]]:
        kwargs = {
            "messages": messages,
            "functions": functions,
            "stream": self.use_raw_api,
            "delta_stream": False,
        }
        if not self.use_raw_api:
            kwargs["extra_generate_cfg"] = {"function_choice": "auto"}
        response = self.llm.chat(**kwargs)
        if not self.use_raw_api:
            return [dict(item) for item in response]
        last = None
        for chunk in response:
            last = chunk
        if last is None:
            return []
        return [dict(item) for item in last]

    def run_turn(
        self,
        *,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        must_call: bool = False,
        allowed_function_names: list[str] | None = None,
    ) -> AdapterResult:
        functions = convert_openai_tools_to_qwen_functions(tools)
        try:
            raw_response = normalize_jsonable(self._chat_once(messages=messages, functions=functions))
        except Exception as exc:  # noqa: BLE001
            return AdapterResult(
                status="error",
                error=repr(exc),
                raw_response=None,
                use_raw_api=self.use_raw_api,
            )
        if contains_raw_tool_markup(raw_response):
            return AdapterResult(
                status="error",
                error="raw tool markup leaked into adapter result",
                raw_response=raw_response,
                use_raw_api=self.use_raw_api,
            )

        callable_item = next((item for item in raw_response if item.get("function_call")), None)
        if callable_item is None:
            text = " ".join(str(item.get("content", "")) for item in raw_response if item.get("content"))
            if must_call:
                return AdapterResult(
                    status="error",
                    error="must_call was requested but no callable function object was returned",
                    assistant_text=text,
                    raw_response=raw_response,
                    use_raw_api=self.use_raw_api,
                )
            return AdapterResult(
                status="assistant_text",
                assistant_text=text,
                raw_response=raw_response,
                use_raw_api=self.use_raw_api,
            )

        function_call = callable_item["function_call"]
        name = function_call.get("name")
        raw_arguments = function_call.get("arguments")
        if not isinstance(name, str) or not name:
            return AdapterResult(
                status="error",
                error="function call name missing",
                raw_response=raw_response,
                use_raw_api=self.use_raw_api,
            )
        if allowed_function_names and name not in allowed_function_names:
            return AdapterResult(
                status="error",
                error=f"function call name {name!r} not in allowed_function_names",
                raw_response=raw_response,
                use_raw_api=self.use_raw_api,
            )
        if not isinstance(raw_arguments, str):
            return AdapterResult(
                status="error",
                error="function call arguments are not a string",
                raw_response=raw_response,
                use_raw_api=self.use_raw_api,
            )
        arguments, parse_error = parse_json_arguments(raw_arguments)
        if arguments is None:
            return AdapterResult(
                status="error",
                error=f"invalid function call JSON: {parse_error}",
                raw_response=raw_response,
                use_raw_api=self.use_raw_api,
            )
        return AdapterResult(
            status="function_call",
            function_call=AdapterFunctionCall(
                name=name,
                arguments=arguments,
                raw_arguments=raw_arguments,
                function_id=(callable_item.get("extra") or {}).get("function_id"),
            ),
            raw_response=raw_response,
            use_raw_api=self.use_raw_api,
        )

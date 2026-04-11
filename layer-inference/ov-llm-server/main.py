import json
import logging
import os
import queue
import threading
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

import openvino_genai as ov_genai
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel


REGISTRY_PATH = os.path.expanduser(
    os.environ.get("OV_REGISTRY_PATH", "~/models/converted_models/registry.json")
)
MODEL_PATH = os.path.expanduser(
    os.environ.get(
        "OV_MODEL_PATH",
        "~/models/converted_models/ov-qwen2-5-3b-instruct-fp16/task-text-generation-with-past__wf-fp16",
    )
)
DEVICE = os.environ.get("OV_DEVICE", "GPU")
LOG_LEVEL = os.environ.get("OV_LOG_LEVEL", "INFO").upper()

logging.basicConfig(level=LOG_LEVEL, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("ov-llm-server")

app = FastAPI()
_PIPELINES: Dict[str, ov_genai.LLMPipeline] = {}
_REGISTRY: Dict[str, Dict[str, Any]] = {}
_REGISTRY_MTIME = 0.0
_REGISTRY_LOCK = threading.Lock()
_GENERATE_LOCK = threading.Lock()


def read_registry() -> Tuple[Dict[str, Dict[str, Any]], float]:
    if not os.path.exists(REGISTRY_PATH):
        return {}, 0.0
    try:
        mtime = os.path.getmtime(REGISTRY_PATH)
        with open(REGISTRY_PATH, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        models = data.get("models", {}) if isinstance(data, dict) else {}
        return models, mtime
    except (OSError, json.JSONDecodeError):
        return {}, 0.0


def refresh_registry(force: bool = False) -> None:
    global _REGISTRY_MTIME
    with _REGISTRY_LOCK:
        models, mtime = read_registry()
        if not force and mtime <= _REGISTRY_MTIME:
            return
        previous = _REGISTRY.copy()
        _REGISTRY.clear()
        _REGISTRY.update(models)
        _REGISTRY_MTIME = mtime

        changed = []
        for name, entry in previous.items():
            new_entry = models.get(name)
            if not new_entry or new_entry.get("path") != entry.get("path"):
                changed.append(name)
        for name in changed:
            _PIPELINES.pop(name, None)
        if changed:
            logger.info("Registry updated: reloaded=%d invalidated=%s", len(models), ",".join(changed))


_REGISTRY, _REGISTRY_MTIME = read_registry()
logger.info(
    "Startup config: device=%s registry_path=%s fallback_model=%s registry_models=%d",
    DEVICE,
    REGISTRY_PATH,
    MODEL_PATH,
    len(_REGISTRY),
)


class FunctionCall(BaseModel):
    name: str
    arguments: str


class ToolCall(BaseModel):
    id: str
    type: str = "function"
    function: FunctionCall


class ChatMessage(BaseModel):
    role: str
    content: Optional[str] = None
    tool_calls: Optional[List[ToolCall]] = None


class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    tools: Optional[List[Dict[str, Any]]] = None
    stream: bool = False
    temperature: float = 0.7
    max_tokens: int = 1024


def get_pipeline(model_name: str) -> ov_genai.LLMPipeline:
    if model_name in _PIPELINES:
        return _PIPELINES[model_name]

    model_entry = _REGISTRY.get(model_name)
    model_path = model_entry.get("path") if model_entry else None
    if not model_path:
        model_path = MODEL_PATH

    start = time.time()
    pipeline = ov_genai.LLMPipeline(model_path, DEVICE)
    elapsed = time.time() - start
    logger.info(
        "Loaded model: name=%s path=%s device=%s time=%.2fs",
        model_name,
        model_path,
        DEVICE,
        elapsed,
    )
    _PIPELINES[model_name] = pipeline
    return pipeline


def build_prompt(
    model_name: str, messages: List[ChatMessage], tools: Optional[List[Dict[str, Any]]]
) -> str:
    pipe = get_pipeline(model_name)
    tokenizer = pipe.get_tokenizer()
    payload = [{"role": m.role, "content": m.content or ""} for m in messages]
    if tools:
        payload.insert(
            0,
            {
                "role": "system",
                "content": (
                    "You can call tools. When you want to call a tool, respond with a "
                    'JSON object like {"name":"tool_name","arguments":"{...}"} and no '
                    "extra text."
                ),
            },
        )
    return tokenizer.apply_chat_template(
        payload, add_generation_prompt=True, chat_template=""
    )


def build_config(req: ChatCompletionRequest) -> ov_genai.GenerationConfig:
    config = ov_genai.GenerationConfig()
    config.max_new_tokens = req.max_tokens
    config.do_sample = True
    config.temperature = req.temperature
    return config


def extract_tool_call(
    text: str, tools: Optional[List[Dict[str, Any]]]
) -> Optional[ToolCall]:
    if not tools:
        return None
    try:
        obj = json.loads(text.strip())
        name = obj.get("name")
        arguments = obj.get("arguments")
        if isinstance(name, str) and isinstance(arguments, str):
            return ToolCall(
                id="call_0", function=FunctionCall(name=name, arguments=arguments)
            )
    except json.JSONDecodeError:
        pass
    tool = tools[0]
    function = tool.get("function", {})
    name = function.get("name") or tool.get("name") or "tool"
    return ToolCall(
        id="call_0",
        function=FunctionCall(name=name, arguments="{}"),
    )


def generate_text(prompt: str, config: ov_genai.GenerationConfig, model_name: str) -> str:
    pipe = get_pipeline(model_name)
    parts: List[str] = []
    done = threading.Event()
    token_queue: "queue.Queue[Optional[str]]" = queue.Queue()

    def callback(subword: str) -> bool:
        token_queue.put(subword)
        return False

    def run_generate() -> None:
        try:
            with _GENERATE_LOCK:
                pipe.generate(prompt, config, callback)
        finally:
            done.set()
            token_queue.put(None)

    thread = threading.Thread(target=run_generate, daemon=True)
    thread.start()

    while not done.is_set():
        token = token_queue.get()
        if token is None:
            break
        parts.append(token)
    return "".join(parts)


def stream_tokens(prompt: str, config: ov_genai.GenerationConfig, model_name: str):
    pipe = get_pipeline(model_name)
    token_queue: "queue.Queue[Optional[str]]" = queue.Queue()

    def callback(subword: str) -> bool:
        token_queue.put(subword)
        return False

    def run_generate() -> None:
        try:
            with _GENERATE_LOCK:
                pipe.generate(prompt, config, callback)
        finally:
            token_queue.put(None)

    thread = threading.Thread(target=run_generate, daemon=True)
    thread.start()
    while True:
        token = token_queue.get()
        if token is None:
            break
        yield token


def stream_chat_response(
    text_stream, model_name: str, tool_call: Optional[ToolCall]
):
    created = int(time.time())
    yield (
        "data: "
        + json.dumps(
            {
                "id": "chatcmpl-stream",
                "object": "chat.completion.chunk",
                "created": created,
                "model": model_name,
                "choices": [{"index": 0, "delta": {"role": "assistant"}}],
            }
        )
        + "\n\n"
    )

    if tool_call:
        yield (
            "data: "
            + json.dumps(
                {
                    "id": "chatcmpl-stream",
                    "object": "chat.completion.chunk",
                    "created": created,
                    "model": model_name,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {
                                "tool_calls": [
                                    {
                                        "id": tool_call.id,
                                        "type": "function",
                                        "function": {
                                            "name": tool_call.function.name,
                                            "arguments": tool_call.function.arguments,
                                        },
                                    }
                                ]
                            },
                            "finish_reason": "tool_calls",
                        }
                    ],
                }
            )
            + "\n\n"
        )
    else:
        for token in text_stream:
            yield (
                "data: "
                + json.dumps(
                    {
                        "id": "chatcmpl-stream",
                        "object": "chat.completion.chunk",
                        "created": created,
                        "model": model_name,
                        "choices": [
                            {"index": 0, "delta": {"content": token}}
                        ],
                    }
                )
                + "\n\n"
            )
        yield (
            "data: "
            + json.dumps(
                {
                    "id": "chatcmpl-stream",
                    "object": "chat.completion.chunk",
                    "created": created,
                    "model": model_name,
                    "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
                }
            )
            + "\n\n"
        )
    yield "data: [DONE]\n\n"


@app.get("/health")
def health() -> Dict[str, Any]:
    loaded_models = sorted(_PIPELINES.keys())
    return {
        "status": "ok",
        "device": DEVICE,
        "models": len(_REGISTRY),
        "loaded_models": loaded_models,
        "loaded_models_count": len(loaded_models),
    }


@app.get("/v1/models")
def list_models() -> Dict[str, Any]:
    registry, _ = read_registry()
    data = [
        {"id": name, "object": "model", "owned_by": "local"}
        for name in sorted(registry.keys())
    ]
    return {"object": "list", "data": data}


@app.post("/v1/chat/completions")
def chat_completions(request: ChatCompletionRequest, raw_request: Request):
    request_id = uuid.uuid4().hex[:8]
    start = time.time()
    model_name = request.model
    client_host = raw_request.client.host if raw_request.client else "unknown"
    refresh_registry()
    if model_name not in _REGISTRY and REGISTRY_PATH:
        refresh_registry(force=True)
        logger.info("Reloaded registry for missing model: %s", model_name)
    prompt = build_prompt(model_name, request.messages, request.tools)
    config = build_config(request)
    created = int(time.time())

    if request.stream:
        if request.tools:
            text = generate_text(prompt, config, model_name)
            tool_call = extract_tool_call(text, request.tools)
            response = StreamingResponse(
                stream_chat_response([], model_name, tool_call),
                media_type="text/event-stream",
            )
            logger.info(
                "Request complete: id=%s model=%s stream=%s client=%s time=%.2fs",
                request_id,
                model_name,
                request.stream,
                client_host,
                time.time() - start,
            )
            return response
        response = StreamingResponse(
            stream_chat_response(stream_tokens(prompt, config, model_name), model_name, None),
            media_type="text/event-stream",
        )
        logger.info(
            "Request complete: id=%s model=%s stream=%s client=%s time=%.2fs",
            request_id,
            model_name,
            request.stream,
            client_host,
            time.time() - start,
        )
        return response

    text = generate_text(prompt, config, model_name)
    tool_call = extract_tool_call(text, request.tools)
    message: Dict[str, Any]
    finish_reason = "stop"
    if tool_call:
        message = {"role": "assistant", "content": None, "tool_calls": [tool_call.dict()]}
        finish_reason = "tool_calls"
    else:
        message = {"role": "assistant", "content": text}

    response = JSONResponse(
        {
            "id": "chatcmpl-0",
            "object": "chat.completion",
            "created": created,
            "model": model_name,
            "choices": [
                {
                    "index": 0,
                    "message": message,
                    "finish_reason": finish_reason,
                }
            ],
        }
    )
    logger.info(
        "Request complete: id=%s model=%s stream=%s client=%s time=%.2fs",
        request_id,
        model_name,
        request.stream,
        client_host,
        time.time() - start,
    )
    return response


def main():
    print("Run with: uv run uvicorn main:app --host 0.0.0.0 --port 9000")


if __name__ == "__main__":
    main()

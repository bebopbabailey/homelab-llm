# What TinyAgents Does (Plain-English)

TinyAgents is the **orchestrator** between your prompts, your model gateway, and your tools.

It is **not** the model backend itself.

## Mental model

Think of TinyAgents as a local worker that does:

1. Accept a request (CLI or HTTP)
2. Decide whether to call a tool
3. Run tool(s) through MCP (if needed)
4. Send context to LiteLLM
5. Return a final answer

## Architecture (MVP)

```text
You (CLI or HTTP)
    |
    v
TinyAgents (this service)
    |                     \
    |                      \__ MCP tools (search.web, web.fetch, ...)
    |
    v
LiteLLM (127.0.0.1:4000)
    |
    v
Model backends (MLX / others behind LiteLLM)
```

## Request walkthrough (example)

User request:
`"openvino llm"`

Flow:
1. TinyAgents receives the request (`tiny-agents run ...` or `POST /run`).
2. It loads allowed tools from MCP registry.
3. It may call `search.web` first (MVP deterministic behavior).
4. Tool output is appended as context.
5. TinyAgents sends prompt + context to LiteLLM `/chat/completions`.
6. Model response is returned with tool call records.

## What TinyAgents currently does

- CLI runner: `tiny-agents`
- Local HTTP service: `tiny-agents-service`
- Localhost-only bind: `127.0.0.1:4030`
- Tool calls via MCP registry
- LLM calls via LiteLLM only
- Tool scaffold helper for new MCP tool skeletons

## What TinyAgents does NOT do yet

- No autonomous scheduling/looping by default
- No privileged system actions by default
- No direct calls to backend inference services
- No LAN exposure

## Why this exists

This is the first practical autonomy layer: it lets models use tools in a controlled way,
with explicit boundaries and local-first operation.

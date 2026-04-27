# 2026-04-27 — orchestration-cockpit local bring-up

## Summary

Brought up the phase 4 `orchestration-cockpit` prototype on the Mini against a
real Studio-local oMLX listener and the validated `omlx-runtime` adapter path.

Result: **the local cockpit concept is viable**.

What succeeded:
- Studio-local oMLX listener on `127.0.0.1:8120`
- Mini-local SSH forward on `127.0.0.1:8129`
- LangGraph dev server on `127.0.0.1:2024`
- non-vendored Agent Chat UI web app on `127.0.0.1:3030`
- live ordinary, specialized, and invalid specialized missions through the
  LangGraph API

What required correction during bring-up:
- `langgraph dev` needed the local checkout `PYTHONPATH`
- `langgraph dev` rejected the graph when it included a custom checkpointer
- the stock `create-agent-chat-app` scaffold root `pnpm dev` flow was the wrong
  launch shape for this repo because it tries to start its own agent server on
  `:2024` and defaults the web app toward the commodity `:3000` path

## Runtime shape

- Worktree:
  `/home/christopherbailey/homelab-llm-orchestration-cockpit-phase4-20260427`
- Local artifacts dir:
  `/tmp/orchestration-cockpit-phase4`
- Studio listener:
  `127.0.0.1:8120`
- Mini forwarded endpoint:
  `127.0.0.1:8129 -> Studio 127.0.0.1:8120`
- LangGraph dev server:
  `127.0.0.1:2024`
- Agent Chat UI web app:
  `127.0.0.1:3030`
- Graph ID:
  `operator-cockpit`
- API key mode:
  fixed local eval key (`eval-key`)
- Local LangGraph tooling key:
  local-only placeholder `LANGSMITH_API_KEY` was accepted for the dev server
  process and was not used as cockpit auth

## Validated paths

### Specialized-runtime liveness

The Mini forwarded endpoint responded cleanly before LangGraph bring-up:

```json
{
  "object": "list",
  "data": [
    {
      "id": "Qwen3-4B-Instruct-2507-4bit",
      "object": "model",
      "owned_by": "omlx"
    }
  ]
}
```

### LangGraph API

`/openapi.json` and `/docs` both served on `127.0.0.1:2024`.

`/assistants/search` returned the expected graph-backed assistant:
- `graph_id=operator-cockpit`
- `name=operator-cockpit`

### Mission results

All runs were executed through the live LangGraph API on the local Agent
Server.

#### 1. Ordinary placeholder

Input:
- `hello`

Result:
- route message: `Route: ordinary-placeholder`
- final text:
  `Ordinary placeholder path: phase 4 keeps commodity model calls out of scope. Received ordinary mission text: hello`

#### 2. Valid specialized mission

Input:
- `/specialized S02 explain the repeated-prefix runtime path briefly`

Result:
- route message: `Route: specialized-runtime (fixture S02)`
- route decision:
  `specialized-runtime`
- fixture id:
  `S02`
- final text came back through the live `omlx-runtime` path and began:
  `Specialized runtime completed: **helper_2 behavior**: ...`

This proves the graph invoked the existing `OmlxRuntimeClient` through the
validated `127.0.0.1:8129 -> 127.0.0.1:8120` transport path.

#### 3. Invalid specialized mission

Input:
- `/specialized TOOL please run tools`

Result:
- route message:
  `Route: out-of-scope (unsupported specialized fixture 'TOOL')`
- final text:
  `Out of scope: unsupported specialized fixture 'TOOL'`

This remained local and did not need the specialized runtime.

## UI bring-up

The non-vendored Agent Chat UI path was viable, but only in the narrower
web-only form.

Observed facts:
- Open WebUI remained on `0.0.0.0:3000`
- the Agent Chat UI web app served cleanly on `127.0.0.1:3030`
- the root HTML loaded successfully on `127.0.0.1:3030`

Important operational detail:
- the `create-agent-chat-app` scaffold's root `pnpm dev` command is **not** the
  right phase 4 launch path for this repo
- it tries to start its own agent server on `:2024` and assumes the default web
  path rather than the repo's non-conflicting `:3030`
- the correct phase 4 launch is web-only, pointed at the existing local
  LangGraph server

## Corrections applied in this slice

- switched graph imports to package-safe imports for live loading
- removed the custom `InMemorySaver` from the graph export so `langgraph dev`
  would accept the graph
- documented `PYTHONPATH=./src:../omlx-runtime/src` as a real local bring-up
  requirement
- updated the cockpit runbook/UI wrapper to describe the web-only Agent Chat UI
  launch shape

## Remaining caveat

This slice proved:
- local LangGraph API viability
- route visibility
- specialized runtime invocation
- non-conflicting local UI serving

It did **not** perform browser automation against the chat UI itself. The GUI
served on `127.0.0.1:3030`, and the same graph-backed missions succeeded
through the live local Agent Server API, but no automated click-through was
captured in this slice.

## Cleanup state

At the end of verification, the following local processes remained up for
operator use:
- Studio oMLX listener on `127.0.0.1:8120`
- Mini SSH forward on `127.0.0.1:8129`
- LangGraph dev server on `127.0.0.1:2024`
- Agent Chat UI web app on `127.0.0.1:3030`

No public routing, Open WebUI changes, LiteLLM aliasing, or OpenHands/MCP work
were introduced.

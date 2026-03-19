# 2026-03-17 — `main-shadow` `8123` direct-gate failure closure

## Summary
- Resumed the failed `8123` rollout after Studio recovery and captured the
  direct backend evidence.
- The `vllm-metal` baseline on `8123` does start successfully and serves
  `Qwen3-Next-80B-A3B-Instruct`.
- The rollout still fails its hard gate because tool calling is not returned in
  the required structured OpenAI format.
- `8123` was rolled back on Studio after direct validation failed.
- Mini LiteLLM remained unchanged throughout; `main-shadow` was never exposed.

## Relationship to prior entry
This closes and refines:
- `docs/journal/2026-03-17-main-shadow-8123-rollout-failure.md`

The earlier entry recorded a startup/host-contamination failure window. After
Studio recovered, the direct backend was observed cleanly and the real blocking
failure mode was captured.

## What was proven on `8123`
Launch contract:
- `vllm-metal` on `192.168.1.72:8123`
- model path:
  `/Users/thestudio/models/hf/models--LibraxisAI--Qwen3-Next-80B-A3B-Instruct-MLX-MXFP4/snapshots/35386111fd494a54a4e3a3705758e280c44d9e9e`
- served model:
  `mlx-qwen3-next-80b-mxfp4-a3b-instruct`
- flags:
  - `--max-model-len 32768`
  - `--generation-config vllm`
  - `--no-async-scheduling`
  - `--enable-auto-tool-choice`
  - `--tool-call-parser qwen3_xml`
- env:
  - `VLLM_METAL_MEMORY_FRACTION=auto`

Observed direct success:
- `/v1/models` returned the expected served model
- structured outputs passed `5/5`
- long-context sanity passed `3/3`

Observed direct failure:
- `tool_choice="required"` returned `400 Bad Request` on every attempt
- error payload showed raw `<tool_call>` content where structured tool-call JSON
  was expected
- `tool_choice="auto"` returned `200 OK` but the assistant message content was
  raw `<tool_call>...</tool_call>` markup and `tool_calls` remained empty

Representative backend error:
```text
Invalid JSON: expected value at line 1 column 1
input_value='<tool_call>\n{"name": "noop", "arguments": {}}\n</tool_call>'
```

## Supporting runtime evidence
- Studio logs showed the model loading cleanly and the API server starting:
  - model loaded in ~22.5s
  - server started on `http://192.168.1.72:8123`
  - `/v1/models` available
- Logs also showed repeated `Qwen3XMLToolParser` imports and xgrammar/FSM
  rejection noise during tool-call attempts.
- The failure is therefore not “server never starts”; it is specifically
  “server starts but does not satisfy the required structured tool-call
  contract for this rollout.”

## Rollback
- Booted out `com.bebop.mlx-shadow.8123`
- Removed `/Library/LaunchDaemons/com.bebop.mlx-shadow.8123.plist` from Studio
- Reconfirmed canonical Studio listeners:
  - `8100` healthy
  - `8101` healthy
  - `4020` healthy

## Contract decision
- `main-shadow` remains blocked.
- Do not expose `main-shadow` through LiteLLM.
- Do not change public `main`, `boost*`, `code-reasoning`, OpenCode defaults,
  or OpenHands contracts.

## Next step
One of these must happen before re-attempting LiteLLM exposure:
1. prove a different `vllm-metal` parser/artifact combination on `8123` that
   returns structured tool calls for both `required` and acceptable `auto`
   behavior, or
2. promote the documented fallback investigation on
   `main-fallback-shadow` / `mlx-openai-server`.

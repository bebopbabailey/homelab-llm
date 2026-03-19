# 2026-03-18 — `main-shadow` `8123` hermes retry (`NO-GO`, rolled back)
## Summary
- Retried `main-shadow` on Studio `8123` with the documented Qwen/vLLM
  function-calling path:
  - `--tool-call-parser hermes`
  - `--enable-auto-tool-choice`
  - `--structured-outputs-config.backend xgrammar`
- Kept the boring baseline:
  - `--generation-config vllm`
  - `--max-model-len 32768`
  - `--no-async-scheduling`
  - `--no-enable-prefix-caching`
  - `VLLM_METAL_MEMORY_FRACTION=auto`
- Startup, `/v1/models`, and structured outputs passed.
- `tool_choice="auto"` improved and now returned structured `tool_calls`.
- `tool_choice="required"` still failed on every attempt with backend `400`.
- Per rollout contract, `8123` was rolled back immediately and Mini LiteLLM was
  left unchanged.

## Relationship to prior entries
This entry refines:
- `docs/journal/2026-03-17-main-shadow-8123-rollout-failure.md`
- `docs/journal/2026-03-17-main-shadow-8123-direct-gate-failure-closure.md`

The prior entries established that `qwen3_xml` was the wrong parser path.
This retry proved that switching to `hermes` fixes `auto` tool calling but does
not yet fix the hard `required` gate.

## Runtime contract used
- host: `192.168.1.72`
- port: `8123`
- label: `com.bebop.mlx-shadow.8123`
- runtime: `vllm-metal 0.1.0` / `vllm 0.14.1`
- model path:
  `/Users/thestudio/models/hf/models--LibraxisAI--Qwen3-Next-80B-A3B-Instruct-MLX-MXFP4/snapshots/35386111fd494a54a4e3a3705758e280c44d9e9e`
- served model:
  `mlx-qwen3-next-80b-mxfp4-a3b-instruct`
- flags:
  - `--max-model-len 32768`
  - `--generation-config vllm`
  - `--structured-outputs-config.backend xgrammar`
  - `--no-async-scheduling`
  - `--enable-auto-tool-choice`
  - `--tool-call-parser hermes`
  - `--no-enable-prefix-caching`
- env:
  - `VLLM_METAL_MEMORY_FRACTION=auto`

## Direct backend results
- `GET /v1/models`: PASS
- structured outputs gate: PASS (`5/5`)
- tool gate A, `tool_choice="required"`: FAIL (`0/5`)
- tool gate B, `tool_choice="auto"`: PASS (`10/10`)
- long-context sanity: NOT RUN
- bounded generic concurrency: NOT RUN
- shared-prefix branch-generation probe: NOT RUN

## Failure shape
`tool_choice="required"` returned backend `400` on every attempt with an error
payload of the form:

```text
Invalid JSON: expected value at line 1 column 1
input_value='<tool_call>\n{"name": "noop", "arguments": {}}\n</tool_call>'
```

This means:
- the runtime now emits valid structured `tool_calls` for `auto`
- but the guided/required path still collapses into raw XML-style tool markup
  that fails JSON validation under the xgrammar-guided requirement path

## Supporting runtime evidence
- startup was healthy on `8123`
- logs showed the revised runtime args:
  - `tool_call_parser='hermes'`
  - `structured_outputs_config.backend='xgrammar'`
  - `enable_prefix_caching=False`
- repeated `required` failures coincided with xgrammar FSM rejection noise and
  backend `400 Bad Request`
- `auto` requests returned `200 OK` with proper `tool_calls`

## Mini exposure
- NOT DONE
- `MAIN_SHADOW_*` was not populated
- LiteLLM was not restarted
- `main-shadow` remains absent from the live Mini `/v1/models` surface

## Rollback
- booted out `com.bebop.mlx-shadow.8123`
- removed `/Library/LaunchDaemons/com.bebop.mlx-shadow.8123.plist` from Studio
- reconfirmed healthy canonical listeners:
  - `8100`
  - `8101`
  - `4020`
- Mini LiteLLM readiness remained healthy

## Verdict
- `NO-GO and rolled back`

## Next step
Choose one of:
1. run the bounded alternate-artifact retry on `8123` with the same
   `hermes`/xgrammar protocol contract, or
2. promote the documented `main-fallback-shadow` investigation on
   `mlx-openai-server`

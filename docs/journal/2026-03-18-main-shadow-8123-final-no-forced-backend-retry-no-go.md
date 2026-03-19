# 2026-03-18 — `main-shadow` `8123` final no-forced-backend retry (`NO-GO`, rolled back)
## Summary
- Ran the final narrow `main-shadow` retry on Studio `8123` with:
  - `--tool-call-parser hermes`
  - `--enable-auto-tool-choice`
  - no explicit `--structured-outputs-config.backend ...`
- Kept the same conservative baseline:
  - `--generation-config vllm`
  - `--max-model-len 32768`
  - `--no-async-scheduling`
  - `--no-enable-prefix-caching`
  - `VLLM_METAL_MEMORY_FRACTION=auto`
- Startup, `/v1/models`, and structured outputs passed.
- `tool_choice="auto"` passed with proper structured `tool_calls`.
- `tool_choice="required"` still failed on every attempt with backend `400`.
- explicit named-tool forcing also failed: `tool_calls` existed, but
  `function.arguments` still contained raw `<tool_call>...</tool_call>` markup
  instead of JSON
- logs still showed xgrammar/FSM failures even without forcing xgrammar in the
  launch contract
- local runtime evidence confirmed `guidance` is not installed, so the planned
  alternate-backend Retry B was not eligible
- per the contract, `8123` was rolled back and Mini LiteLLM remained unchanged

## Relationship to prior entries
This closes the `8123` retry sequence after:
- `docs/journal/2026-03-17-main-shadow-8123-rollout-failure.md`
- `docs/journal/2026-03-17-main-shadow-8123-direct-gate-failure-closure.md`
- `docs/journal/2026-03-18-main-shadow-8123-hermes-retry-no-go.md`

The earlier `hermes` retry proved that `auto` improved but `required` still
failed under explicit xgrammar. This final retry proved that removing the
explicit xgrammar flag does not clear the forced-tool failure on the current
Studio build.

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
- tool gate B, named tool choice: FAIL (`0/5`)
- tool gate C, `tool_choice="auto"`: PASS (`10/10`)
- long-context sanity: NOT RUN
- bounded generic concurrency: NOT RUN
- shared-prefix branch-generation probe: NOT RUN

## Failure shape
### `tool_choice="required"`
Every attempt returned backend `400` with an error payload of the form:

```text
Invalid JSON: expected value at line 1 column 1
input_value='<tool_call>\n{"name": "noop", "arguments": {}}\n</tool_call>'
```

### Named tool choice
Every attempt returned `200 OK`, but the returned `tool_calls[0].function.arguments`
field contained raw XML-wrapped tool markup:

```text
<tool_call>
{"name": "noop", "arguments": {}}
</tool_call>
```

This means the endpoint still cannot satisfy forced-tool semantics cleanly,
even though `auto` now works.

## Supporting runtime evidence
- startup was healthy on `8123`
- `auto` tool requests returned valid structured `tool_calls`
- logs still showed repeated xgrammar/FSM rejection noise during forced-tool
  requests even though the launch contract no longer explicitly set xgrammar
- local runtime check showed:
  - `xgrammar`: installed
  - `guidance`: not installed

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

## Contract decision
On the current Studio build:
- `main-shadow` must remain blocked
- `vllm-metal` is not yet a valid MAIN-shadow forced-tool backend for
  `Qwen3-Next-80B-A3B-Instruct`
- do not expose `main-shadow`
- do not change public `main`
- do not change `code-reasoning`
- do not change `boost*`

## Next step
Move to one of these:
1. the documented `main-fallback-shadow` investigation on `mlx-openai-server`, or
2. an explicit decision to retire `vllm-metal` as the MAIN-shadow backend
   candidate on the current Studio build

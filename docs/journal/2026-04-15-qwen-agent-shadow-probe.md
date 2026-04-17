# 2026-04-15 — Qwen-Agent shadow probe on the accepted Qwen lane

## Summary
- Added a narrow probe harness for testing `Qwen-Agent` as a function-calling
  adapter over the accepted `8101` Qwen backend.
- This probe is intentionally **not** a backend fix and does not change any
  public lane, gateway route, or runtime lock.
- The first live result is promising on the accepted lane:
  - `use_raw_api=false` passed all current probe cases on `8101`
  - `use_raw_api=true` failed inside `Qwen-Agent` normalization before the
    consumer received a callable function object
- The planned tiny `Qwen3-Coder-Next` confirmation has **not** been run yet
  because the artifact is no longer cached on Studio after the earlier cleanup,
  and re-downloading it is a large model pull that needs explicit approval.

## Probe contract
- Backend under test: direct Studio `8101`
  (`mlx-qwen3-next-80b-mxfp4-a3b-instruct`).
- Adapter under test: pinned `qwen-agent==0.0.34`.
- Runtime note: the current package import path also requires a few extra
  runtime dependencies in the ephemeral probe environment, so the probe records
  the exact `qwen-agent` pin and imported version in `environment.json`.
- Cases:
  - one obvious single-function call
  - two-function disambiguation
  - a simple code-helper shaped function call
- Modes:
  - `generate_cfg.use_raw_api=false`
  - `generate_cfg.use_raw_api=true`
- Success means the consumer receives a callable function invocation object with
  valid JSON arguments, local function execution succeeds, and the round-trip
  completes without raw tool markup leaking into the consumer-visible result.

## Current result
### Accepted `8101` lane
- Probe command pinned `qwen-agent==0.0.34`.
- `environment.json` also records:
  - imported Qwen-Agent version
  - Python version
  - backend URL and model id
  - tested `use_raw_api` values
- Current `8101` result:
  - `one_function`, `two_function`, and `code_helper` all passed `3/3` with
    `use_raw_api=false`
  - all three cases failed `0/3` with `use_raw_api=true`

### `use_raw_api=false`
- Qwen-Agent successfully returned callable function-call dicts.
- Arguments parsed as valid JSON.
- The local function executed cleanly.
- The round-trip assistant reply completed.
- No raw `<tool_call>`-style markup leaked into the consumer-visible result.

### `use_raw_api=true`
- Failure mode is in Qwen-Agent itself, not in the consumer:
  - the raw API path on this backend produces a tool-call stream chunk with
  `arguments=None`
  - Qwen-Agent `0.0.34` crashes while normalizing that chunk into its
    `FunctionCall` schema
- The recorded error in the raw artifacts is:
  - `Input should be a valid string` for `FunctionCall.arguments`

## Tiny `Qwen3-Coder-Next` confirmation
- A temporary direct shadow was launched on Studio loopback `127.0.0.1:8134`
  and tunneled locally to `18134`.
- Artifact used:
  `mlx-community/Qwen3-Coder-Next-4bit`
- One local runtime-only repair was still required on the fresh download:
  - `tokenizer_config.json` shipped `extra_special_tokens` as a list
  - `transformers` expects a mapping there
  - local-only fix applied in the Studio cache with a `.bak-qwen-agent` backup
- After that repair, the shadow listener started successfully and
  `GET /v1/models` returned `mlx-qwen3-coder-next-4bit-shadow`.
- One-function Qwen-Agent confirmation result:
  - `use_raw_api=false`: `3/3`
  - `use_raw_api=true`: `3/3`
- In this coder-next confirmation, both modes produced:
  - callable function-call objects
  - valid JSON arguments
  - clean downstream execution
  - clean round-trip assistant text
  - no raw tool markup in the consumer-visible result

## Immediate disposition
- Qwen-Agent has now shown practical value on both:
  - the accepted `8101` Qwen lane
  - the target `Qwen3-Coder-Next` shadow runtime
- The current evidence supports moving to the next narrow slice: a small
  internal adapter contract, not gateway or UI integration.
- No LiteLLM or Open WebUI integration was added in this proof slice.

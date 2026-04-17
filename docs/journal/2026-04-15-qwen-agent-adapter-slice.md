# 2026-04-15 — Qwen-Agent adapter slice

## Summary
- Added a narrow internal `QwenAgentAdapter` module for one coding-agent
  surface.
- The adapter does **not** claim native backend forced-tool semantics.
- Its contract is adapter-level only:
  - convert OpenAI-style `tools` into Qwen-Agent `functions`
  - call Qwen-Agent against the existing OpenAI-compatible backend
  - return either:
    - normalized callable function-call object
    - plain assistant text
    - explicit adapter error

## Adapter contract
- Input:
  - `messages`
  - OpenAI-style `tools`
  - `must_call`
  - optional `allowed_function_names`
- Output:
  - `AdapterResult.status = function_call | assistant_text | error`
  - `AdapterResult.function_call.arguments` is parsed JSON on success
  - `must_call=True` upgrades “no function returned” to an explicit error
- The adapter also rejects consumer-visible raw tool markup instead of letting a
  caller silently parse around it.

## Validation
- Unit tests cover:
  - OpenAI tool conversion
  - `must_call` enforcement
  - normalized function-call output
  - raw markup rejection
- Live validation remains direct-to-backend only; no LiteLLM or Open WebUI
  integration is included in this slice.
- Current live adapter smoke on `8101`:
  - backend: `http://192.168.1.72:8101/v1`
  - model: `mlx-qwen3-next-80b-mxfp4-a3b-instruct`
  - mode: `use_raw_api=false`
  - result: `status="function_call"` with parsed args
  - returned call:
    - `name = read_virtual_file`
    - `arguments = {"path": "main.py"}`

# 2026-04-15 — Qwen-Agent proxy + OpenHands shadow slice

## Summary
- Added an experimental localhost-only `qwen-agent-proxy` sidecar on the Mini.
- Kept the trusted `code-reasoning` worker lane unchanged.
- Added a shadow LiteLLM alias `code-qwen-agent` for OpenHands-side validation
  of `Qwen3-Coder-Next` through the sidecar.

## Contract
- Sidecar bind: `127.0.0.1:4021`
- Sidecar model id: `qwen-agent-coder-next-shadow`
- Supported:
  - `/v1/models`
  - `/v1/chat/completions`
  - `tool_choice=auto`
  - `tool_choice=required`
  - named function choice
- Unsupported:
  - streaming
  - `/v1/responses`
- Failure mode:
  - fail closed when `required` or named tool choice does not yield a callable
    function object

## OpenHands shadow shape
- Preferred direct OpenHands container path:
  `http://host.docker.internal:4021/v1`
- Preferred direct model id: `qwen-agent-coder-next-shadow`
- Optional LiteLLM validation path:
  - shadow LiteLLM alias: `code-qwen-agent`
  - shadow worker key file:
    `/home/christopherbailey/.config/openhands/worker_api_key_shadow`
  - shadow OpenHands container path:
    `http://host.docker.internal:4001/v1`
- Intended backend chain:
  - OpenHands
  - `qwen-agent-proxy`
  - Mini-local SSH tunnel `18134`
  - Studio `Qwen3-Coder-Next` shadow on `8134`

## Verified results
- Direct `qwen-agent-proxy` checks passed for:
  - `GET /v1/models`
  - `POST /v1/chat/completions` with named function choice
  - `POST /v1/chat/completions` with `tool_choice="required"`
- Shadow LiteLLM on `127.0.0.1:4001` passed for:
  - `GET /v1/models` with a worker-scoped key
  - `POST /v1/chat/completions` with populated `tool_calls`
- Remaining gap:
  - the optional shadow LiteLLM path still returns `403` for worker-scoped
    `model/info` on `4001` because LiteLLM collapses the supplied route list to
    `["llm_api_routes"]`
  - `/v1/responses` remains intentionally unavailable on the shadow alias

## Disposition
- The Qwen-Agent-backed shadow lane is proven for direct OpenHands-compatible
  `models`, `model/info`, and `chat/completions` through the sidecar.
- The optional shadow LiteLLM path remains operator-only validation, not the
  preferred app integration path.

## Notes
- `qwen-agent==0.0.34` remains the pinned adapter runtime for this slice.
- The sidecar lives under `experiments/qwen-agent-proxy`; the earlier internal
  adapter script now imports from the service module instead of owning the
  implementation itself.

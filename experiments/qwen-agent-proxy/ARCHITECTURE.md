# Architecture: qwen-agent-proxy

## Role
- Provide a localhost-only OpenAI-compatible Chat Completions shim on the Mini.
- Normalize Qwen-Agent function-calling over the Studio `Qwen3-Coder-Next`
  backend into a callable tool payload that OpenHands can consume through LiteLLM.

## Data Flow
- OpenHands -> shadow LiteLLM alias -> `qwen-agent-proxy` -> Studio `8134` Qwen backend.
- Direct operator validation may call `http://127.0.0.1:4021/v1/*`.

## Boundaries
- The proxy is experimental and scoped to the `code-qwen-agent` shadow alias only.
- The proxy is the function-calling adapter. It does not claim native backend
  forced-tool guarantees.
- The trusted `code-reasoning` lane remains canonical.

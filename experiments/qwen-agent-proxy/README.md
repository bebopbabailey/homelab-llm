# qwen-agent-proxy

Experimental localhost-only Qwen-Agent sidecar for the OpenHands shadow coding lane.

This service wraps the Studio `Qwen3-Coder-Next` shadow backend and normalizes
tool calls into a callable Chat Completions payload for a shadow LiteLLM alias.

Read first:
- `SERVICE_SPEC.md`
- `ARCHITECTURE.md`
- `CONSTRAINTS.md`
- `RUNBOOK.md`

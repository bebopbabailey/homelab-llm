# LiteLLM Feature Inventory (What We Should Not Rebuild)

This document summarizes LiteLLM proxy capabilities we can rely on to avoid custom re-implementation.

## Model Registry & Routing
- `model_list` defines client-facing `model_name` and upstream `litellm_params` (api_base, api_key, headers, etc.). citeturn0search0
- Router strategies (e.g., `simple-shuffle`, `least-busy`) and aliasing (`model_group_alias`) are built in. citeturn0search1turn0search3
- `ignore_invalid_deployments` prevents bad entries from blocking all models (proxy default is true). citeturn0search1

## Health & Readiness (Scalable)
- `/health` performs model calls to validate deployments. citeturn0search4
- `/health/readiness` and `/health/liveliness` are provided for service checks. citeturn0search4
- Background health checks can be enabled via `general_settings.background_health_checks` with an interval. citeturn0search4
- Per-model opt-out is supported with `model_info.disable_background_health_check`. citeturn0search4

## Failure Handling & Retries
- Router retries and cooldowns are configurable (`retry_policy`, `allowed_fails`, `cooldown_time`). citeturn0search1
- Context-window fallbacks and model fallbacks are supported (`context_window_fallbacks`, `fallbacks`). citeturn0search1
- Pre-call checks for context window enforcement (`enable_pre_call_checks`). citeturn0search1

## OpenAI-Compatible Endpoints
- Use `openai/<model>` in `litellm_params.model` for OpenAI-compatible upstreams. citeturn0search2
- `/v1/search` is supported via `search_tools` config entries (e.g., SearXNG).

## Config Surface
- `general_settings`, `router_settings`, `litellm_settings` are first-class config sections; Swagger exposes the full schema. citeturn0search0

## Where This Leaves Our Stack
- Gateway: use LiteLLM for routing, health, retries, and basic policy knobs.
- tinyagents: focus on orchestration logic, not transport-level health.

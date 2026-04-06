# 10-TASKS_TINYAGENTS

## Phase 0 - Foundations
- [ ] Create repo skeleton (README, DEV_CONTRACT, TASKS, decision log).
- [ ] Add env template with `LITELLM_BASE_URL` and optional `LITELLM_API_KEY`.
- [ ] Write smoke tests before coding (curl commands).
- [ ] Verify LiteLLM `/health` and `/v1/models` from target host.
- [x] Verify Open WebUI unit status; use systemd service only (user unit removed).
- [x] Verify OpenVINO bind scope (localhost vs 0.0.0.0) and update docs.
- [x] Verify Studio MLX host and ports match `config/env.local`.

## Phase 1 - LiteLLM client wiring
- [ ] Implement a minimal OpenAI-compatible client using LiteLLM base URL.
- [ ] Validate model list from `/v1/models`.
- [ ] Add request ID logging for traceability.

## Phase 2 - Orchestration MVP
- [ ] Implement deterministic model selection rules (use logical model names only).
- [ ] Add task-level retries without touching LiteLLM transport settings.
- [ ] Add structured trace logging (no secrets).

## Phase 3 - Ops readiness
- [ ] Add config validation for base URL and API key.
- [ ] Document log correlation with LiteLLM request IDs.
- [ ] Add failure-handling runbook entries.

## Phase 4 - Optional extensions
- [ ] Add optional metadata enrichment (no new ports).
- [ ] Update docs and decision log.

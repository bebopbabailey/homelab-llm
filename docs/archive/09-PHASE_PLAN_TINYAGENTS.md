# 09-PHASE_PLAN_TINYAGENTS

Platform-aware project plan for Tiny Agents. All phases respect port immutability from `02-PORTS_ENDPOINTS_REGISTRY.md`.

## Phase 0 - Foundations (before implementation)
- Goals:
  - Establish repo skeleton, docs scaffolding, and verification checklists.
  - Validate access to LiteLLM and upstream services without changing ports.
- Tasks:
  - Create repo skeleton (README, DEV_CONTRACT, TASKS, decision log).
      - Define env template for `LITELLM_BASE_URL` and `LITELLM_API_KEY` (use `http://mini:4000` or `http://192.168.1.71:4000`).
  - Add smoke-test commands in docs before any code.
  - Confirm LiteLLM `/health` and `/v1/models` work from the target machine.
- Deliverables:
  - Minimal README and runbook.
  - Smoke-test doc with curl commands.
  - Checklist for verified assumptions (LAN IPs, enabled units).
- Test plan:
  - `curl -fsS http://127.0.0.1:4000/health` (Mini) or configured `LITELLM_BASE_URL`.
- Rollback:
  - Remove Tiny Agents repo only; no platform changes.

## Phase 1 - LiteLLM client wiring
- Goals:
  - Implement a minimal client wrapper that calls LiteLLM via OpenAI-compatible API.
  - Keep model selection to logical names from LiteLLM (`jerry-*`, `lil-jerry`).
- Tasks:
  - Implement a single request path to `/v1/chat/completions` using env-configured base URL.
  - Read model list from `/v1/models` to validate availability.
  - Log LiteLLM request IDs for traceability.
- Deliverables:
  - Minimal client module and usage doc.
- Test plan:
  - `POST /v1/chat/completions` with `model: jerry-weak` and `model: lil-jerry`.
- Rollback:
  - Remove client module and config without touching LiteLLM.

## Phase 2 - Orchestration MVP
- Goals:
  - Implement small, deterministic orchestration (routing decisions, retries at task level) without changing gateway behavior.
- Tasks:
  - Add a router function that selects model names based on task type.
  - Add task-level retry policy (do not override LiteLLM transport retries).
  - Add basic trace logging (no secrets).
- Deliverables:
  - Orchestration module with documented model selection rules.
- Test plan:
  - Simulate failures by targeting a disabled model and ensure graceful error handling.
- Rollback:
  - Disable orchestration path and fall back to direct LiteLLM calls.

## Phase 3 - Ops readiness
- Goals:
  - Add operational hooks and clear runbooks without exposing new ports.
- Tasks:
  - Add config validation for `LITELLM_BASE_URL` and API key presence (if enabled).
  - Add structured log output for request/response timing.
  - Document how to align Tiny Agents logs with LiteLLM request IDs.
- Deliverables:
  - Ops runbook and logging guide.
- Test plan:
  - Ensure logs contain request IDs for successful and failed calls.
- Rollback:
  - Disable additional logging and revert to baseline.

## Phase 4 - Optional extensions (only if needed)
- Goals:
  - Optional tool integrations or metadata enrichment that do not alter network exposure.
- Tasks:
  - Add optional metadata output (tags, capabilities) using LiteLLM responses.
- Deliverables:
  - Updated docs, no port changes.
- Test plan:
  - Verify metadata output does not affect response payloads.
- Rollback:
  - Remove optional metadata features.

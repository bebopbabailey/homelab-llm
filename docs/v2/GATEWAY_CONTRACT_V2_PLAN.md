# V2 Planning Material: Gateway Contract V2 Plan

Not current runtime truth. This file defines the public gateway contract that V2 should preserve or intentionally change in later rebuild slices.

## Purpose

- Preserve the boring public gateway contract while decoupling it from specific V1 backend identities.
- Define additive V2 alias vocabulary without forcing runtime or naming cutover before parity is proven.
- Keep specialized runtime, retrieval, and host-expansion work outside the first gateway slice.

## Current Contract Evidence

- Current public gateway implementation evidence points to LiteLLM on Mini as the user-facing OpenAI-compatible gateway candidate. Evidence: [../../services/litellm-orch/SERVICE_SPEC.md](../../services/litellm-orch/SERVICE_SPEC.md), [../foundation/topology.md](../foundation/topology.md)
- Current stable public human aliases are `fast` and `deep`. Evidence: [../INTEGRATIONS.md](../INTEGRATIONS.md), [../../services/litellm-orch/config/router.yaml](../../services/litellm-orch/config/router.yaml)
- Current internal coding/runtime vocabulary still includes `code-reasoning`, but that should not become V2 architecture identity. Evidence: [../../services/litellm-orch/SERVICE_SPEC.md](../../services/litellm-orch/SERVICE_SPEC.md), [../INTEGRATIONS.md](../INTEGRATIONS.md)
- Current speech aliases `voice-stt` and `voice-tts` exist in repo canon, but Phase 1A should treat them only as reserved future vocabulary within V2 planning. Evidence: [../INTEGRATIONS.md](../INTEGRATIONS.md), [../foundation/topology.md](../foundation/topology.md)

## Proposed V2 Alias Set

### Preserve current stable aliases

- `fast`
- `deep`

These stay in place until additive V2 aliases prove parity. No existing stable alias is removed or renamed before that point.

### Additive V2 aliases

- `default`
  - intended everyday general lane
- `code-fast`
  - intended latency-first coding lane
- `code-main`
  - intended primary coding lane
- `code-review`
  - intended highest-scrutiny coding/review lane

### Vocabulary rules

- `general` and `review` are descriptive capability words, not alias IDs.
- `code-reasoning` remains historical/current implementation vocabulary only, not desired V2 public contract vocabulary.
- `voice-stt` and `voice-tts` remain reserved future vocabulary only in V2 planning. They are not Phase 1A acceptance targets.

## Compatibility Targets

### Preserve as current public contract evidence

- `POST /v1/chat/completions`
- `GET /v1/models`
- `GET /v1/model/info`
- `GET /health`
- `GET /health/readiness`
- `GET /health/liveliness`
- `GET /metrics/`

### Candidate or desirable compatibility targets

- `POST /v1/responses`

Current repo canon documents `POST /v1/responses` as part of the LiteLLM public contract. Evidence: [../../services/litellm-orch/SERVICE_SPEC.md](../../services/litellm-orch/SERVICE_SPEC.md). Phase 1A should preserve that evidence in planning, but should not make `/v1/responses` a mandatory runtime acceptance requirement unless direct client dependency is explicitly confirmed in the implementation slice.

### Exposure policy

- `/v1/models` should expose logical aliases, not backend IDs.
- Backend names remain implementation detail.
- Direct raw backend probes remain diagnostic only, not public contract proof.

## Auth And Key Posture

- Preserve bearer-authenticated public gateway posture. Evidence: [../INTEGRATIONS.md](../INTEGRATIONS.md), [../../services/litellm-orch/SERVICE_SPEC.md](../../services/litellm-orch/SERVICE_SPEC.md)
- Preserve health/readiness/liveliness behavior that does not require exposing secret values.
- Preserve the rule that backend credentials and upstream keys stay hidden behind the gateway contract.
- Do not expand auth surface in Phase 1A.

## Logging And Observability Posture

- Preserve gateway health/readiness/liveliness as the boring operational contract.
- Preserve the current metrics surface as `GET /metrics/`, matching current repo evidence. Evidence: [../../services/litellm-orch/SERVICE_SPEC.md](../../services/litellm-orch/SERVICE_SPEC.md), [../INTEGRATIONS.md](../INTEGRATIONS.md)
- Preserve alias-level observability and health attribution.
- Do not expose backend implementation identity as user-facing contract or logging identity unless explicitly needed for operator-only debugging.
- Keep secret-bearing logging out of scope.

## Cutover And Rollback Principles

- Introduce new aliases additively before any retirement or rename.
- Keep current stable aliases live until additive aliases prove parity.
- Prefer alias-map rollback before runtime-family or host-level rollback.
- Preserve the rule that direct backend success does not prove gateway success. Evidence: [V1_DO_NOT_REPEAT.md](V1_DO_NOT_REPEAT.md)
- Preserve the rule that the public contract stays boring even when backend experimentation continues privately. Evidence: [V1_LESSONS_LEARNED.md](V1_LESSONS_LEARNED.md), [../foundation/runtime-planes.md](../foundation/runtime-planes.md)

## Explicitly Out Of Scope

- MLX runtime rebuild
- Specialized runtime exposure
- Retrieval rebuild
- OpenHands expansion
- Orin integration
- HP integration
- Concrete port changes
- Backend promotion based only on direct/raw probes

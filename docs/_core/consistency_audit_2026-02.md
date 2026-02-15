# Consistency Audit — 2026-02 (Phase 1)

This ledger tracks canonical/root documentation claims that diverged from active
runtime/config/registry truth.

Operational note: the evergreen “what does consistent mean?” checklist lives in
`docs/_core/CONSISTENCY_DOD.md`. This file remains the dated ledger of findings.

| id | doc | section | claim (before) | authoritative evidence | severity | disposition | resolution |
| --- | --- | --- | --- | --- | --- | --- | --- |
| CLAIM-LITE-DEEP-ENV-DRIFT | `layer-gateway/litellm-orch/config/router.yaml` | `model_list` `deep` alias | `deep` referenced `MLX_MLX_GPT_OSS_120B_MXFP4_Q4_*` env keys that were not present in `config/env.local`, causing LiteLLM startup failure | Runtime evidence: `TypeError: argument of type 'NoneType' is not iterable` during config load; `config/env.local` defines `MLX_TXGSYNC_GPT_OSS_120B_DERESTRICTED_MXFP4_MLX_*` keys | high | resolved_phase1_2026-02-12 | Updated `deep` to `MLX_TXGSYNC_GPT_OSS_120B_DERESTRICTED_MXFP4_MLX_*`; `litellm-orch.service` now starts and serves models. |
| CLAIM-LITE-JSON-LOGS | `docs/INTEGRATIONS.md` | LiteLLM routing | `json_logs: true` | `layer-gateway/litellm-orch/config/router.yaml` has `litellm_settings.json_logs: false` | high | resolved_phase1_2026-02-09 | Docs updated: `litellm_settings.json_logs: false`. |
| CLAIM-LITE-EXPERIMENTS | `docs/INTEGRATIONS.md` | LiteLLM routing | `x1-x4` reserved aliases | `router.yaml` currently defines `main/deep/fast/swap/boost/task-*` only | medium | resolved_phase1_2026-02-09 | Docs updated: `x1-x4` are described as not currently configured. |
| CLAIM-LITE-BOOST-DEEP | `docs/INTEGRATIONS.md` | OptiLLM boost lane | `boost-deep` exists | `router.yaml` defines `boost` only | medium | resolved_phase1_2026-02-09 | Docs updated: `boost-deep` removed; only `boost` is current. |
| CLAIM-LITE-AUTH-PLANNED | `docs/INTEGRATIONS.md` | LiteLLM routing | proxy key is planned only | Current deployment docs indicate active auth on gateway (`LITELLM_MASTER_KEY`) | high | resolved_phase1_2026-02-10 | Verified: canonical docs no longer describe LiteLLM auth as “planned only”; they state bearer auth is required in current deployment. |
| CLAIM-OV-WIRED-CONFLICT | `docs/PLATFORM_DOSSIER.md` | Service inventory (OpenVINO) | "LiteLLM now uses ov-* aliases" and "ov-* is deprecated" | `router.yaml`/`handles.jsonl` contain no `ov-*` entries | high | resolved_phase1_2026-02-10 | Docs updated: OpenVINO is standalone and not currently wired as active LiteLLM handles. |
| CLAIM-MLX-8101-DRIFT | `docs/PLATFORM_DOSSIER.md`, `docs/foundation/topology.md` | Boot ensemble | `8101` listed as gemma-27b | `router.yaml` + `handles.jsonl` map `8101` to `mlx-qwen3-next-80b-mxfp4-a3b-instruct` | high | resolved_phase1_2026-02-10 | Docs updated: `8101` is `mlx-qwen3-next-80b-mxfp4-a3b-instruct`.
| CLAIM-FOUNDATION-OPT-REF | `docs/foundation/README.md` | Sources of Truth | points to `opt-techniques.md` | File is `docs/foundation/optillm-techniques.md` | medium | resolved_phase1_2026-02-10 | Docs updated: path is `docs/foundation/optillm-techniques.md`. |
| CLAIM-FOUNDATION-OV-POLICY | `docs/foundation/constraints-and-decisions.md` | Decisions (current) | "OpenVINO stays behind LiteLLM" | Canonical docs now describe OpenVINO as standalone and not currently wired as active LiteLLM handles | high | resolved_phase1_2026-02-10 | Docs updated: OpenVINO is standalone and not wired as active LiteLLM handles. |
| CLAIM-FOUNDATION-MLX-BOOT | `docs/foundation/mlx-registry.md` | Current Boot Ensemble | `8101` is gemma-27b | `router.yaml` and handles map `8101` to `mlx-qwen3-next-80b-mxfp4-a3b-instruct` | high | resolved_phase1_2026-02-10 | Docs updated: boot ensemble `8101` is qwen3-next-80b.
| CLAIM-FOUNDATION-OPT-PROXY-POLICY | `docs/foundation/service-additions.md` | Intro policy | OptiLLM must sit behind LiteLLM | Current architecture/docs allow direct localhost OptiLLM calls for explicit `optillm_approach` usage | medium | resolved_phase1_2026-02-10 | Docs updated: OptiLLM can be used explicitly via `boost` (preferred) and direct localhost calls are operator-only.
| CLAIM-FOUNDATION-TEST-OV-CONDITIONAL | `docs/foundation/testing.md` | LiteLLM Aliases | implies `ov-*` alias checks as default | OpenVINO aliases are not currently active in LiteLLM by default | medium | resolved_phase1_2026-02-10 | Docs updated: OpenVINO alias checks are conditional (“only when intentionally wired”). |

| CLAIM-LITE-HEALTH-AUTH | `docs/foundation/topology.md`, `docs/PLATFORM_DOSSIER.md`, `docs/INTEGRATIONS.md` | LiteLLM health probes | LiteLLM `/health` can be used as an unauthenticated health signal | Mini evidence: `GET http://127.0.0.1:4000/health` returns `401` (auth required); `/health/readiness` returns JSON | high | resolved_phase1_2026-02-09 | Docs updated: `/health/readiness` is the default probe; `/health` requires auth in current deployment. |
| CLAIM-OPTILLM-4020-HOST | `docs/foundation/topology.md`, `docs/PLATFORM_DOSSIER.md`, `TOPOLOGY.md`, `docs/foundation/testing.md` | OptiLLM proxy topology | OptiLLM proxy runs on Mini at `127.0.0.1:4020` | Evidence: Mini has no listener on 4020. Studio has `0.0.0.0:4020` listener and `/v1/models` responds. Studio launchd: `/Library/LaunchDaemons/com.bebop.optillm-proxy.plist`. LiteLLM routes `boost` via `OPTILLM_API_BASE` in `router.yaml`. | high | resolved_phase1_2026-02-09 | Docs updated: OptiLLM proxy is a Studio launchd service on port 4020 and is used via LiteLLM `boost`. |
| CLAIM-STUDIO-V1MODELS-ID | `docs/foundation/testing.md`, `docs/PLATFORM_DOSSIER.md`, `docs/foundation/topology.md` | MLX `/v1/models` semantics | Studio `/v1/models` returns `mlx-*` model IDs | Studio evidence: `/v1/models` returns local filesystem snapshot path IDs; `mlxctl` shows canonical `mlx-*` IDs | medium | resolved_phase1_2026-02-09 | Docs updated: `mlxctl` is canonical; `/v1/models` may return snapshot paths. |

## Deferred to Phase 2
- Per-service docs under `layer-*` that still reference legacy `ov-*`/`opt-*`/old alias states.

---

## Repository-wide discovery and reconciliation (canonical)

This section is the canonical home for repo-wide consistency-audit discovery,
coverage, and claim reconciliation status. Audit material should live here, not
in `implementation_plan.md`.

### Scope coverage summary
- Root docs: reviewed
- `docs/` top-level canonical docs: reviewed
- `docs/foundation`: reviewed
- `docs/_core`: reviewed
- Layer-level docs (`layer-*` roots): reviewed
- Service-tier docs (13 service directories): reviewed
- Ops/planning/script surfaces: reviewed
- Historical bucket (`docs/archive`, `docs/deprecated`): tracked, de-prioritized

### Coverage buckets
| Coverage Bucket | Scope | Priority |
|---|---|---|
| Active canonical/operational | root + canonical docs + layer/service docs + ops/templates/scripts affecting runtime | high |
| Scoped support/planning | `next-projects/*`, `docs/journal/*`, selected guidance docs | medium |
| Historical bucket | `docs/archive/*`, `docs/deprecated/*` | low |

### Claim reconciliation (current status)
| Claim | Evidence source(s) | Status | Notes |
|---|---|---|---|
| OpenVINO posture-sensitive guidance | `docs/INTEGRATIONS.md`, `docs/PLATFORM_DOSSIER.md`, `docs/foundation/ov-model-onboarding.md` | resolved | Docs now consistently state OpenVINO is standalone and not active LiteLLM handles. |
| OptiLLM posture-sensitive guidance | `docs/INTEGRATIONS.md`, `docs/foundation/optillm-techniques.md`, `layer-gateway/optillm-*` docs | resolved | Docs treat OptiLLM local inference as deferred; active proxy path is Studio `:4020` via LiteLLM `boost`. |
| Ops governance discoverability | `platform/ops/scripts/*`, `platform/ops/systemd/*`, `platform/ops/templates/*`, `platform/ops/README.md` | resolved | Added `platform/ops/README.md` as ops narrative/index. |
| Scripts discoverability contract | `scripts/validate_handles.py`, `scripts/README.md` | resolved | Added `scripts/README.md` documenting script purpose and usage. |
| Next-project temporal hygiene | `next-projects/TINYAGENTS_PLAN.md`, `next-projects/VOICE_ASSISTANT_V1.md` | resolved | Added explicit non-canonical planning status notes and refreshed stale model example. |
| Service-doc shape consistency | Service-tier matrix coverage | accepted | `voice-gateway` is intentionally sparse (will be expanded when implementation starts). |

### Round-2 drift candidate disposition
- Service-doc bundle sparsity exceptions (`layer-interface/voice-gateway`): **accepted for now**.
- Ops narrative gap (`platform/ops`): **resolved**.
- Scripts index gap (`scripts`): **resolved**.
- Temporal planning staleness labeling (`next-projects/*`): **resolved**.

### Execution gate status (audit perspective)
- Audit claim table contains no unresolved `needs-refresh` entries for active Wave B scope.
- Remaining structural/taxonomy improvements are non-blocking and belong to later waves.

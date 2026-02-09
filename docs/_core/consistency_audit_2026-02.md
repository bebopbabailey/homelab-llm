# Consistency Audit — 2026-02 (Phase 1)

This ledger tracks canonical/root documentation claims that diverged from active
runtime/config/registry truth.

| id | doc | section | claim (before) | authoritative evidence | severity | disposition | resolution |
| --- | --- | --- | --- | --- | --- | --- | --- |
| CLAIM-LITE-JSON-LOGS | `docs/INTEGRATIONS.md` | LiteLLM routing | `json_logs: true` | `layer-gateway/litellm-orch/config/router.yaml` has `litellm_settings.json_logs: false` | high | fix_now_phase1 | Update docs to `json_logs: false` |
| CLAIM-LITE-EXPERIMENTS | `docs/INTEGRATIONS.md` | LiteLLM routing | `x1-x4` reserved aliases | `router.yaml` currently defines `main/deep/fast/swap/boost/task-*` only | medium | fix_now_phase1 | Mark `x1-x4` as not currently configured |
| CLAIM-LITE-BOOST-DEEP | `docs/INTEGRATIONS.md` | OptiLLM boost lane | `boost-deep` exists | `router.yaml` defines `boost` only | medium | fix_now_phase1 | Remove `boost-deep` from current-state claims |
| CLAIM-LITE-AUTH-PLANNED | `docs/INTEGRATIONS.md` | LiteLLM routing | proxy key is planned only | Current deployment docs indicate active auth on gateway (`LITELLM_MASTER_KEY`) | high | fix_now_phase1 | Document active auth requirement; avoid “planned only” wording |
| CLAIM-OV-WIRED-CONFLICT | `docs/PLATFORM_DOSSIER.md` | Service inventory (OpenVINO) | "LiteLLM now uses ov-* aliases" and "ov-* is deprecated" | `router.yaml`/`handles.jsonl` contain no `ov-*` entries | high | fix_now_phase1 | State OpenVINO is standalone and not currently wired in LiteLLM |
| CLAIM-MLX-8101-DRIFT | `docs/PLATFORM_DOSSIER.md`, `docs/foundation/topology.md` | Boot ensemble | `8101` listed as gemma-27b | `router.yaml` + `handles.jsonl` map `8101` to `mlx-qwen3-next-80b-mxfp4-a3b-instruct` | high | fix_now_phase1 | Update boot ensemble naming to qwen3-next-80b handle |
| CLAIM-FOUNDATION-OPT-REF | `docs/foundation/README.md` | Sources of Truth | points to `opt-techniques.md` | File is `docs/foundation/optillm-techniques.md` | medium | fix_now_phase1 | Correct source-of-truth reference path |
| CLAIM-FOUNDATION-OV-POLICY | `docs/foundation/constraints-and-decisions.md` | Decisions (current) | "OpenVINO stays behind LiteLLM" | Canonical docs now describe OpenVINO as standalone and not currently wired as active LiteLLM handles | high | fix_now_phase1 | Update decision wording to current operational state |
| CLAIM-FOUNDATION-MLX-BOOT | `docs/foundation/mlx-registry.md` | Current Boot Ensemble | `8101` is gemma-27b | `router.yaml` and handles map `8101` to `mlx-qwen3-next-80b-mxfp4-a3b-instruct` | high | fix_now_phase1 | Update boot ensemble model for port 8101 |
| CLAIM-FOUNDATION-OPT-PROXY-POLICY | `docs/foundation/service-additions.md` | Intro policy | OptiLLM must sit behind LiteLLM | Current architecture/docs allow direct localhost OptiLLM calls for explicit `optillm_approach` usage | medium | fix_now_phase1 | Align wording with current direct-call optimization workflow |
| CLAIM-FOUNDATION-TEST-OV-CONDITIONAL | `docs/foundation/testing.md` | LiteLLM Aliases | implies `ov-*` alias checks as default | OpenVINO aliases are not currently active in LiteLLM by default | medium | fix_now_phase1 | Make OpenVINO alias check conditional |

## Deferred to Phase 2
- Per-service docs under `layer-*` that still reference legacy `ov-*`/`opt-*`/old alias states.

# 2026-03 GPT-OSS / `vllm-metal` Experimental Campaign (Archived)

Status: archived historical reference. This document is not current runtime canon.

Canonical current docs:
- `docs/PLATFORM_DOSSIER.md`
- `docs/INTEGRATIONS.md`
- `docs/foundation/topology.md`
- `docs/foundation/testing.md`
- `docs/foundation/mlx-registry.md`
- `layer-inference/RUNBOOK.md`

Scope of archived material:
- GPT-OSS runtime evaluation on Studio experimental ports
- `vllm-metal` tuning and comparison packets
- LiteLLM transport and enforcement investigations tied to the same campaign

Included root artifacts:
- `APPLE_MLX_VLLM_GPTOSS_RUNTIME_REVIEW_2026-03-13.md`
- `Codex_implementation_spec.md`
- `FAST_LANE_GPT_OSS_VLLM_METAL_REVIEW_PACK_2026-03-15.md`
- `FAST_LANE_VLLM_METAL_INCIDENT_REVIEW_PACK_2026-03-15.md`
- `GPT_OSS_20B_CONSTRAINED_CONTRACT_REVIEW_PACK_2026-03-15.md`
- `GPT_OSS_20B_VS_120B_AB_VERIFICATION_REVIEW_PACK_2026-03-15.md`
- `GPT_OSS_8120_RESPONSES_STORE_REVIEW_PACK_2026-03-15.md`
- `GPT_OSS_FAST_LANE_EXPERIMENTAL_VALIDATION_REPORT_2026-03-15.md`
- `GPT_OSS_RESPONSES_FIRST_AB_COMPARISON_REVIEW_PACK_2026-03-15.md`
- `LITELLM_GPTOSS20B_ENFORCEMENT_INVESTIGATION_REPORT_2026-03-16.md`
- `LITELLM_GPTOSS20B_EXPERIMENTAL_LANE_SOAK_REPORT_2026-03-17.md`
- `LITELLM_GPTOSS20B_NOOP_TOOL_CAUSAL_ISOLATION_REPORT_2026-03-17.md`

Chronology summary:
- `2026-03-13`: initial runtime-review packet framed the backend choice and tool-calling constraints.
- `2026-03-15`: the campaign expanded into constrained-contract, A/B, and review-pack validation across GPT-OSS variants.
- `2026-03-16` to `2026-03-17`: LiteLLM transport enforcement and direct-backend causal-isolation work clarified that the remaining blocker was backend behavior, not caller drift.

Outcome:
- Active public runtime truth moved into the platform canon and runbooks.
- The detailed evidence packet names remain listed here for historical traceability;
  the active archive surface is the dated rollup, not one file per packet.

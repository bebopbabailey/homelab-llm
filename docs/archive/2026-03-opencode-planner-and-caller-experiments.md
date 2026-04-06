# 2026-03 OpenCode Planner And Caller Experiments (Archived)

Status: archived historical reference. This document is not current OpenCode canon.

Canonical current docs:
- `docs/OPENCODE.md`
- `docs/INTEGRATIONS.md`
- `docs/foundation/testing.md`
- `docs/foundation/runtime-lock.md`

Scope of archived material:
- planner-path and caller-path experiments involving OpenCode, LiteLLM, and OptiLLM
- early incident reports and follow-up packets around planning aliases and GPT-OSS caller behavior

Included root artifacts:
- `GPT_OSS_20B_OPENCODE_CALLER_FACING_PILOT_REVIEW_PACK_2026-03-16.md`
- `OPENCODE_NATIVE_CONFIG_FOLLOWUP_REPORT_2026-03-16.md`
- `OPENCODE_PHASE_A_LANE_INCIDENT_REPORT_2026-03-12.md`
- `OPENCODE_PLANNING_INCIDENT_REPORT_2026-03-11.md`

Chronology summary:
- `2026-03-11`: planner alias incident work established that tool-shaped repo analysis could not safely rely on the planning aliases under test.
- `2026-03-12`: `/phase-a` lane incident work narrowed command-path and lane-shaping problems.
- `2026-03-16`: caller-facing GPT-OSS pilot and native-config follow-up documented the remaining compatibility limits.

Outcome:
- Current repo-local OpenCode policy now lives in the control-plane docs.
- These packet names remain as historical evidence for why the present OpenCode
  posture hardened the way it did.

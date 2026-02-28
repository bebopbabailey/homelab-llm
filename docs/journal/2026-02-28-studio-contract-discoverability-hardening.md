# 2026-02-28 — Studio contract discoverability hardening

## Context
After the Studio scheduling policy rollout, several core docs still had partial
discoverability gaps for coding agents:
- one runbook still implied `8101/8102` as default checks
- core `_core` docs did not explicitly wire Studio scheduling policy into
  source-of-truth/change obligations
- service onboarding checklist remained systemd-heavy
- root agent guardrails lacked an explicit owned-label allowlist rule

## Changes made
1. Aligned inference lane checks to canonical active listener wording:
   - `layer-inference/RUNBOOK.md`
   - `8100` is required default check; `8101/8102` are optional if assigned.
2. Added Studio scheduling policy to authoritative core hierarchy:
   - `docs/_core/SOURCES_OF_TRUTH.md`
3. Added Studio launchd/lane change obligations:
   - `docs/_core/CHANGE_RULES.md`
4. Added Studio launchd checklist for new services:
   - `docs/foundation/service-additions.md`
5. Added root hard guardrail for owned Studio labels:
   - `AGENTS.md`

## Why this matters
- Reduces agent ambiguity for Studio operations.
- Makes launchd/label drift easier to detect during doc maintenance.
- Keeps service onboarding consistent across Linux/systemd and macOS/launchd.

## Validation
- Verified updated files contain explicit Studio-policy references.
- Verified runbook wording distinguishes required active lane checks from
  optional assigned lanes.
- Confirmed changes are docs-only and do not alter runtime configuration.

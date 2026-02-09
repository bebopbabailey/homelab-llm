# 2026-02-09 — OptiLLM Proxy Deploy Workflow (Mini → Studio)

## Summary
- Declared Mini as source of truth for `layer-gateway/optillm-proxy` development.
- Added a Studio deploy helper to pull, sync deps, restart launchd, and run smoke/bench.
- Documented launchd label and override knobs for deploy automation.

## Decisions
- Deploy is git-pull based (no rsync).
- Launchd label default: `optillm.proxy.studio`.
- Smoke test + optional benchmark live beside deploy script for shared ownership.

## Follow-ups
- Keep optillm-local deferred to Orin AGX.

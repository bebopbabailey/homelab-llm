# 2026-02-18 — Open WebUI web-search Phase A baseline harness

## Summary
- Added a reproducible Phase A baseline harness for Open WebUI web search.
- Implemented a helper script to print a run-tagged prompt pack and score
  retrieval/extraction signals from systemd journals.
- Added end-user test instructions to `docs/foundation/testing.md`.

## What was added
- `scripts/openwebui_phase_a_baseline.py`
  - `print-pack --run-id ...` prints a 10-query pack for manual Open WebUI use.
  - `score --run-id ... --since ...` summarizes:
    - per-case prompt marker detection in Open WebUI logs
    - per-case source block detection
    - SearXNG rate-limit/429 errors from `searxng.service` logs
    - pass/fail booleans for baseline viability checks

## Why this matters
- Establishes a baseline quality/stability gate before adding rerankers or
  additional retrieval components.
- Keeps validation reproducible and operator-friendly while preserving normal
  end-user flow in Open WebUI.

## Notes
- This harness reads service journals only; it does not alter runtime behavior.
- For best signal quality, run a dedicated `run_id` and score immediately after
  sending prompts.

# 2026-02-08 — Journal Integrity Policy + Restoration

## Goal
Restore any displaced journal entries and lock in an append-only journal policy for future agents.

## Changes
- Restored OptiLLM-local journal entries back into `docs/journal/`.
- Documented append-only rules in `docs/_core/CHANGE_RULES.md` and `docs/journal/README.md`.
- Added the same rule to the `homelab-durability` skill for agent enforcement.

## Notes
- The journal is a chronological record. Corrections should be additive (new entries), not edits to past entries.
- `docs/journal/index.md` must always be updated when new entries are added.

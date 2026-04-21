# 2026-03-04 — Codex history pilot-ingest enablement (vector store)

## Summary
Implemented a deterministic pilot-corpus builder for Codex conversation history,
wired the operator runbook flow, and executed a first 30-day pilot ingest into
the Studio main vector store.

No port/bind changes were made.

## What changed
- Added `layer-data/vector-db/scripts/build_codex_history_pilot.py`:
  - input: `~/.codex/history.jsonl` (or explicit `--in`)
  - output: ingest-ready JSONL with:
    - `source`, `source_thread_id`, `source_message_id`, `timestamp`
    - `title`, `uri`, `raw_ref`, `schema_version`, `text`
  - defaults:
    - `--since-days 30`
    - `--source codex_history_pilot`
    - redaction enabled
  - deterministic message IDs:
    - `ts + sha256(text)` with collision suffixing
  - secret redaction patterns:
    - bearer/API-key-like tokens
    - long hex blobs
    - private key markers
  - sensitive-reference guard:
    - skips records containing markers like `.codex/auth.json`, `.sqlite`, state/cache internals

- Updated `layer-data/vector-db/RUNBOOK.md` with:
  - pilot corpus build command
  - optional dry-run
  - copy-to-Studio step
  - one-time ingest invocation with explicit `MEMORY_INGEST_PATH`
  - retrieval smoke probe
  - rollback by source (`codex_history_pilot`)

- Updated task tracking:
  - `layer-data/vector-db/TASKS.md`
  - `NOW.md`

## Why this approach
- `~/.codex/history.jsonl` is lower-noise and easier to normalize than full
  `~/.codex/sessions/*` event envelopes.
- Source-scoped ingest keying + delete-by-source gives clean rollback.
- Redaction-first posture reduces accidental secret retention during pilot.

## Execution + verification performed
- Builder dry-run and full output generation:
  - `kept=1690`, `redacted_records=9`, `since_days=30`
- Staged pilot corpus to Studio ingest path:
  - `/Users/thestudio/data/memory-main/ingest/events.codex-history.pilot.normalized.jsonl`
- One-time ingest run completed:
  - `run_id=INGEST-20260304-170412`
  - `status=ok`, `docs=1690`, `chunks=1804`
- Post-ingest API checks:
  - `/v1/memory/stats` -> documents/chunks/vectors increased
  - `/v1/memory/search` on known homelab queries returned `source=codex_history_pilot` hits
- Policy + health preflight checks passed:
  - `validate_studio_policy --json`
  - `audit_studio_scheduling --policy-only --json`
  - `GET /health` on memory API

## Follow-up gate
- Run 30-day pilot ingest and score retrieval quality on a fixed homelab query
  set before expanding corpus breadth or enabling recurring ingestion.

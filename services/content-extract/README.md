# Content Extract (Data Layer)

Mission: turn various personal data exports (initially ChatGPT, Codex, iMessages)
into a single canonical, provenance-preserving **JSONL event stream** suitable for
downstream indexing (RAG) and reflection pipelines.

This is a **batch CLI** tool. It does not run as a long-lived service.

## Scope (v0)
Inputs (first wins):
- ChatGPT export JSON → events JSONL
- Codex conversations/logs JSON/JSONL → events JSONL
- iMessage `chat.db` SQLite (from iDevice backups) → events JSONL

Outputs:
- Canonical `events.*.jsonl` (1 line = 1 event/message)
- Normalized canonical `events.*.normalized.jsonl`
- `manifest.json` (counts, hashes, schema version, run metadata)
- Optional per-run stats report for quick sanity checks

## Non-goals
- No summarization, topic labeling, embeddings, or vector DB writes.
- No “memory distillation” or reflection artifacts here.
- No network calls required for normal operation.
- No storing raw exports inside the repo.

## Data retention and safety (important)
Raw exports and extracted outputs MUST live **outside** the git repo.

Recommended external data root (pick one and standardize):
- `/srv/homelab-llm/data/ingest/`
- `~/homelab-data/ingest/`
- `/Volumes/Data/homelab-llm/ingest/`

Suggested layout under that root:
- `raw/`     (original exports; never edited)
- `staging/` (intermediate scratch; safe to delete)
- `out/`     (canonical JSONL + manifests; immutable artifacts)

This repo contains only:
- code, schemas, docs, config templates

## Quickstart (expected workflow)
1) Extract source → `out/events.<source>.jsonl`
2) Normalize → `out/events.<source>.normalized.jsonl`
3) Validate → ensure schema correctness and stable IDs
4) Hand off normalized JSONL to downstream indexer (vector-db ingestion)

See: SERVICE_SPEC.md for the CLI contract and RUNBOOK.md for operational details.

## Documentation contract
This directory follows the monorepo documentation contract:
- README.md
- SERVICE_SPEC.md
- ARCHITECTURE.md
- RUNBOOK.md
- TASKS.md
- DEPENDENCIES.md
- CONSTRAINTS.md
- docs/README.md (deep dives)
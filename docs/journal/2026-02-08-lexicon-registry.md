# 2026-02-08 — Lexicon Registry (Data Layer)

## Decision
Introduce a minimal **lexicon registry** in the data layer to support
**deterministic spelling/term corrections** (e.g., LiteLLM, Open WebUI)
without free-form rewriting.

## Files
- Registry: `layer-data/registry/lexicon.jsonl`
- Schema notes: `layer-data/registry/README.md`

## Policy (v0)
- Corrections are **explicit** and **deterministic**.
- Only apply in non‑strict modes (e.g., clarify/post‑processing).
- Do not use for verbatim/strict transcript modes.
- Normalize aliases by lowercasing and removing spaces/punctuation.

## Rationale
- Prevents accidental drift while still fixing known, recurring mis-spellings.
- Keeps a clear path for migration to a vector store later (`embedding_text`).

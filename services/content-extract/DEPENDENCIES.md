# Dependencies and Contracts

## Upstream inputs (v0)
- ChatGPT export JSON (OpenAI export format)
- Codex conversations/logs in JSON/JSONL (format depends on exporter)
- iMessage SQLite `chat.db` from iDevice backups

## Downstream consumers
- Data-layer indexing pipeline (e.g., vector-db ingestion)
- Digest/reflection pipeline (summaries, learning extraction, style hypotheses)

## Contract: canonical event stream
This project must produce JSONL where:
- One line = one atomic event (message/email/note/etc.)
- Every event includes stable provenance fields
- Text is normalized deterministically (no semantic rewriting)
- IDs are stable and reproducible (see ARCHITECTURE.md)

Downstream must be able to:
- filter by metadata (source, author, time range, thread)
- cite back to `source_message_id` and `raw_ref` for evidence

## What this project does not do
- No direct writes to vector stores or databases.
- No chunking policy decisions for embeddings (downstream concern).
- No “profile” or “self model” inference (downstream concern).
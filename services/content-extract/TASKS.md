# Tasks: Content Extract (v0 → v1)

## v0: MVP (fast wins)
- [ ] Create canonical event schema definition (events.v0)
- [ ] Implement extractor interface contract (common base)
- [ ] ChatGPT extractor: export JSON → events JSONL
- [ ] Codex extractor: export JSON/JSONL → events JSONL
- [ ] iMessage extractor: chat.db → events JSONL (attachments referenced only)
- [ ] Deterministic normalizer (whitespace, unicode hygiene, code block preservation)
- [ ] Validator (required fields, timestamp format, ID uniqueness)
- [ ] Manifest generator (counts + hashes + schema version)
- [ ] Golden test fixtures (tiny sample exports) + regression tests
- [ ] Docs complete + `/init` generates AGENTS.md cleanly

Acceptance criteria:
- Produces stable IDs across re-runs
- Handles >1M events with streaming memory behavior
- No raw data in repo; clear external data-root workflow

## v1: Quality + extensibility
- [ ] Add “merge” utility to combine multiple normalized JSONLs into one
- [ ] Add simple PII redaction hooks (optional, off by default) for logs
- [ ] Add attachment expansion stage (text-only attachments first)
- [ ] Add calendar/notes extractors (once v0 is stable)
- [ ] Add metrics report (empty-rate, avg length, per-source counts)

## Future (explicitly out of scope here)
- Audio transcription/diarization pipelines
- Photo tagging / vision extraction
- Summarization/digest/reflection generation
- Embeddings + vector DB ingestion
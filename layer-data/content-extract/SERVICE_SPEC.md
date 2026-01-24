# Service Spec: Content Extract CLI

## Purpose
Convert source exports into a canonical JSONL event stream, then normalize and
validate it for downstream RAG/reflection ingestion.

## Interface
This service is a CLI with subcommands:

### Extract
- `content-extract extract chatgpt --in <export.json> --out <events.jsonl>`
- `content-extract extract codex --in <path> --out <events.jsonl>`
- `content-extract extract imessage --db <chat.db> --out <events.jsonl>`

Extractors must:
- preserve ordering within a thread when possible
- emit one event per message
- preserve code blocks and URLs verbatim
- preserve source IDs and timestamps

### Normalize
- `content-extract normalize --in <events.jsonl> --out <events.normalized.jsonl>`

Normalization must be deterministic:
- normalize whitespace/newlines
- normalize Unicode oddities (zero-width, bad quotes) when safe
- preserve code blocks verbatim
- DO NOT paraphrase or summarize

### Validate
- `content-extract validate --in <events.normalized.jsonl>`

Validation must fail if:
- required fields are missing
- timestamps are not ISO-8601
- IDs are missing/empty
- schema_version mismatch
- duplicated `id` values in a single output file (unless explicitly allowed)

### Manifest
- `content-extract manifest --in <events.normalized.jsonl> --out <manifest.json>`

Manifest should include:
- schema version
- record count
- earliest/latest timestamps
- hash (or hashes) of the output file(s)
- per-source counts (if multi-source file)
- run metadata (tool version, git commit, run_id, wall clock time)

## Canonical event schema (v0)
Each JSONL line is an object with at least:

- `id`: stable, deterministic identifier (see ARCHITECTURE.md)
- `schema_version`: e.g. `"events.v0"`
- `source`: `"chatgpt" | "codex" | "imessage" | ...`
- `source_thread_id`: conversation/chat/thread id
- `source_message_id`: message id inside source (or derived stable id)
- `timestamp`: ISO-8601 (timezone-aware when possible)
- `author`: `"me" | "assistant" | "other"`
- `role`: `"user" | "assistant" | "system" | "other"`
- `text`: normalized content (may be empty if attachment-only)
- `attachments`: array (may be empty)
- `raw_ref`: pointer to original file path and/or primary key(s)

Optional fields are allowed but must not break downstream invariants.

## Exit codes
- `0` success
- `2` validation failure / bad input
- `3` runtime failure (I/O, permissions, unexpected schema)

## Logging
- Default: structured logs to stderr (human readable OK)
- `--json-logs` optional for machine parsing
- Never log raw message bodies unless explicitly enabled (privacy)
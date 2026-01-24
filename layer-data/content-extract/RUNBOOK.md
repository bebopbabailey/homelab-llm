# Runbook: Content Extract

## Pre-flight checklist
- Confirm your external data root is NOT inside the repo.
- Confirm you have enough disk space for `out/` artifacts.
- Confirm raw exports are read-only (or treated as such).

## Typical run (v0)
1) Extract
    - ChatGPT:
      `content-extract extract chatgpt --in <export.json> --out <out/events.chatgpt.jsonl>`
    - Codex:
      `content-extract extract codex --in <codex_export_path> --out <out/events.codex.jsonl>`
    - iMessage:
      `content-extract extract imessage --db <chat.db> --out <out/events.imessage.jsonl>`

2) Normalize
    - `content-extract normalize --in <out/events.chatgpt.jsonl> --out <out/events.chatgpt.normalized.jsonl>`
    - repeat for each source

3) Validate
    - `content-extract validate --in <out/events.chatgpt.normalized.jsonl>`

4) Manifest
    - `content-extract manifest --in <out/events.chatgpt.normalized.jsonl> --out <out/manifest.chatgpt.json>`

## Troubleshooting
### Validation fails: missing required fields
- Check the extractor mapping for that source.
- Confirm timestamps exist and are ISO-8601.
- Confirm `source_thread_id` and `source_message_id` are populated.

### Duplicate IDs
- Your stable ID tuple is insufficient.
- Add a stable per-thread message index (derived from ordering) as a fallback.

### Garbled text / weird characters
- Improve deterministic normalization (do not use LLM rewriting here).
- Preserve original text in a separate field only if absolutely required.

### Performance problems
- Ensure streaming reads/writes.
- Avoid building giant in-memory lists of events.
- Prefer line-by-line JSONL processing.

## Safety notes
- Do not print raw message bodies in logs by default.
- Do not commit any raw or normalized output to git.
- Keep manifests safe to commit only if they contain no sensitive info (usually OK).

## When to escalate
- If a new database is proposed (violates data-layer constraints)
- If a new LAN-facing service is proposed
- If an extractor requires network access for core functionality
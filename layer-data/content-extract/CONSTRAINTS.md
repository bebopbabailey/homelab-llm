# Content Extract Constraints

This service inherits global + layer constraints:
- Global: `../../CONSTRAINTS.md`
- Sandbox: `../../SANDBOX_PERMISSIONS.md`
- Data layer: `../CONSTRAINTS.md`

## Hard constraints (non-negotiable)
- **No raw user data in the repo.** No exports, no transcripts, no attachments.
- **No secrets in the repo.** Use env files outside git when needed.
- **No new databases** without an explicit migration plan and approval.
- **No network dependency** for core extraction/normalization (offline-first).
- **Provenance must be preserved** for every event:
    - `source`, `source_thread_id`, `source_message_id`, `raw_ref`
- **Idempotent outputs:** running the same input twice should produce the same
  canonical event IDs and equivalent normalized output (ignoring manifest run_id).
- **Streaming first:** must handle very large corpora (millions of events) without
  loading entire datasets in memory.
- **Do not mutate canonical outputs in place.** Produce new files; keep prior
  artifacts immutable once validated.
- **No summarization in this repo.** “Digest” generation happens downstream.

## Practical constraints (strong preferences)
- Keep schema changes rare; version them explicitly if needed.
- Prefer deterministic normalization (avoid LLM “cleanup” here).
- Attachments are referenced, not deeply extracted, in v0 (unless trivial text).

## Sandbox permissions (service-local summary)
Layer-data defaults:
- Read: `layer-data/*`
- Write: docs + schemas (and this service’s code)
- Execute: no restarts by default

This tool should be safe to run locally as a CLI against an external data root.
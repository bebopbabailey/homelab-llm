# Architecture: Content Extract

## Design goals
- **Provenance-first**: every output event can be traced back to its source.
- **Deterministic**: same input → same IDs + equivalent normalized output.
- **Streaming**: handle very large datasets without loading everything in RAM.
- **Composable**: extraction, normalization, validation are separate steps.
- **Safe by default**: no network dependency; no raw data in repo.

## Data flow
1) Extract (source-specific)
    - Parse source export
    - Emit canonical-ish events JSONL (may be minimally normalized)

2) Normalize (source-agnostic)
    - Apply deterministic text normalization
    - Standardize timestamps and required fields
    - Compute stable `id` if missing
    - Emit normalized JSONL

3) Validate (source-agnostic)
    - Schema validation
    - ID uniqueness check (within file)
    - Sanity checks (timestamp ranges, empty rate, etc.)

4) Manifest (source-agnostic)
    - Summarize output for auditing and reproducibility

## Stable IDs (critical invariant)
`id` MUST be reproducible across runs.

Recommended approach:
- If source provides a stable unique message id: use it as primary.
- Otherwise derive a stable hash from a tuple like:
  `(source, source_thread_id, source_message_id_or_index, timestamp, author, text_hash)`

Notes:
- Avoid including full `text` directly in the ID input; use a stable `text_hash`.
- Ensure normalization happens before computing final IDs if text is included.

## Extractor plugin model
Each extractor implements:
- input parsing
- mapping to canonical fields
- minimal field cleanup

Extractors must NOT:
- summarize content
- infer topics
- embed or call external services
- do cross-thread merging

## Attachments strategy (v0)
- Attachments are referenced in `attachments[]` with file paths/ids.
- Do not OCR or transcribe here in v0.
- Later: a separate “attachment-enrich” stage can create new events linked back
  to the parent message via provenance fields.

## Failure modes + mitigations
- Schema drift in exports:
    - isolate in extractor; add format version detection
- Huge files:
    - streaming JSON parsing where possible
- Duplicates:
    - rely on stable IDs; allow downstream dedupe if needed
- Missing timestamps:
    - use best available; record uncertainty in a field like `timestamp_inferred=true`
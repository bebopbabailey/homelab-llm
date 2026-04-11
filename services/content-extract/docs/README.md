# Content Extract Docs

This folder contains deeper documentation that should not clutter the top-level
service docs.

Suggested additions as the project evolves:
- `SCHEMA.md`: canonical event field definitions + examples
- `SOURCE_FORMATS.md`: notes on ChatGPT/Codex/iMessage export schema variants
- `NORMALIZATION.md`: exact deterministic normalization rules
- `PRIVACY.md`: retention rules, logging policy, redaction policy
- `FIXTURES.md`: how golden fixtures are constructed (without sensitive data)
- `DOWNSTREAM_CONTRACTS.md`: what vector-db ingesters and reflection jobs expect

Top-level entrypoints:
- `../SERVICE_SPEC.md` (CLI contract)
- `../ARCHITECTURE.md` (design + invariants)
- `../CONSTRAINTS.md` (non-negotiables)
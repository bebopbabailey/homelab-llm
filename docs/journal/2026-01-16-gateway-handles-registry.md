# 2026-01-16 — Gateway handles registry v0

## Summary
- Introduced a minimal gateway-owned handles registry (JSONL) for alias-like routing.
- Handles cover both models and callables without exposing endpoint topology.
- Registry does not store health/state; runtime monitoring derives health from probes.
- Naming convention: registry keys use `snake_case`; registry values use `kebab-case`.
- Deferred gateway entities: endpoint registry and policy registry are intentionally out of scope for v0.
- Canonical model IDs are standardized system-wide (dash-only, no vendor prefixes).
  For models, `handle` and `selector.model` must match the canonical model ID.
  Exception: OptiLLM selectors include technique prefixes (e.g., `moa-`) while
  handles remain `opt-*`.
- MLX slots 8100–8119 are team ports; 8120–8139 are experimental.

## Handles entity (v0 fields)
- `handle` (string, PK): user-facing stable name
- `kind` (enum): `model` | `callable`
- `invoke` (enum): `openai-chat` | `openai-embeddings` | `mcp-tool` | `http-get` | `http-post`
- `managed_by` (enum): `systemd` | `launchd` | `docker` | `manual` | `external`
- `endpoint_ref` (string): opaque reference to upstream endpoint
- `selector` (object|null): optional routing discriminator within endpoint
- `notes` (string, optional)

## Resolution contract v0
- Resolve handle → locate the single row in `layer-gateway/registry/handles.jsonl`.
- Use `invoke` to determine the invocation contract.
- Use `endpoint_ref` to select the upstream endpoint (details mapped later).
- If `selector` is present, inject it into the request (e.g., model or tool key).
- Health is not per-handle in v0; it will derive from endpoint probes once the endpoint registry exists.

## Validator
Run:
- `python3 scripts/validate_handles.py`
- `python3 scripts/validate_handles.py layer-gateway/registry/handles.jsonl`

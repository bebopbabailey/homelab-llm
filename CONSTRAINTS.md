# Global Constraints (Non‑Negotiable)

These apply to all agents and all layers unless explicitly overridden by a
written migration plan.

## Sources of truth
Resolve cross-document conflicts using `docs/_core/SOURCES_OF_TRUTH.md`.

## Networking
- **Do not change or reuse ports** without a port‑migration plan.
- **Do not expose new LAN‑facing services** by default.

## Gateway rule
- **Clients must call LiteLLM only.** No direct client → backend calls.

## Safety
- **Do not touch or modify `ollama`** (port 11434).
- **Do not store secrets in the repo.** Use env files under `/etc`.
- **No system driver installs** unless explicitly requested.

## Submodules
- Commit changes inside submodules first, then update the monorepo pointer.

## Sandbox permissions (summary)
See `SANDBOX_PERMISSIONS.md` for per‑layer scope rules.

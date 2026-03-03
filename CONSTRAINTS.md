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
- Node/global CLI policy: use Volta for managed CLIs; avoid `sudo npm -g` (see `docs/foundation/node-toolchain.md`).

## Studio scheduling policy
- Studio is a power inference node; persistent Studio processes we own must be launchd services.
- Only `com.bebop.mlx-launch` and `com.bebop.optillm-proxy` are inference-lane labels.
- Non-inference transient Studio work from repo automation must run via
  `platform/ops/scripts/studio_run_utility.sh` (taskpolicy utility clamp).
- Owned Studio launchd labels (`com.bebop.*`, `com.deploy.*`) are fail-closed by
  policy allowlist; unmanaged owned labels are violations.
- Policy source of truth: `docs/foundation/studio-scheduling-policy.md`.

## Submodules
- Commit changes inside submodules first, then update the monorepo pointer.

## Sandbox permissions (summary)
See `SANDBOX_PERMISSIONS.md` for per‑layer scope rules.

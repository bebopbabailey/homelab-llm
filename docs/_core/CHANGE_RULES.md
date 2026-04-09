# Change Rules

Use these rules to keep documentation and registries consistent.

## Consistency gate
After any change that affects runtime behavior (ports, bindings, auth, routing,
handles, registries), validate the high-risk claim families in
`docs/_core/CONSISTENCY_DOD.md`.

## Topology and Ports
- If any service port, host binding, or endpoint path changes, update:
  - `docs/foundation/topology.md`
  - `docs/PLATFORM_DOSSIER.md`
  - `TOPOLOGY.md`

## Integrations and Routing
- If an integration is added/removed or routing logic changes, update:
  - `docs/INTEGRATIONS.md`
  - `docs/PLATFORM_DOSSIER.md`

## OpenCode control plane
- If repo-local OpenCode defaults, lane policy, agent names, skill names, or
  verification assumptions change, update:
  - `docs/OPENCODE.md`
  - `docs/INTEGRATIONS.md`
  - `docs/foundation/testing.md`

## Service Behavior and Contracts
- If a service's inputs, outputs, env vars, health checks, or lifecycle steps
  change, update that service bundle plus any affected canonical platform docs.

## Root Hygiene
- If the repo-root allowlist or root/journal/archive placement rules change,
  update:
  - `DOCS_CONTRACT.md`
  - `docs/_core/root_hygiene_manifest.json`
  - `scripts/repo_hygiene_audit.py`
  - `docs/foundation/testing.md`
  - `.github/workflows/repo-hygiene.yml`
  - `scripts/README.md`

## Internal Markdown Links
- If internal markdown links are added, removed, or retargeted, update:
  - `scripts/docs_link_audit.py`
  - `scripts/README.md`
  - `docs/foundation/testing.md`
  - `.github/workflows/repo-hygiene.yml`
  - affected docs/journal index entries or correction notes

## Concurrent Efforts
- If concurrent-effort rules or worktree tooling change, update:
  - `docs/_core/CONCURRENT_EFFORTS.md`
  - `scripts/worktree_effort.py`
  - `scripts/start_effort.py`

## Journal Integrity
- Journal entries are append-only.
- If a correction is needed, add a new entry that references the original.
- Always update `docs/journal/index.md` when adding a new entry.

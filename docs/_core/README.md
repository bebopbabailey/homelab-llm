# Documentation Center (_core)

## Purpose
`docs/_core` is the single navigation hub for this repo's documentation. It does not replace existing docs; it points to them and defines how to read them.

## Read Order (humans)
1. `docs/_core/README.md`
2. `docs/_core/SOURCES_OF_TRUTH.md`
3. `docs/_core/CONSISTENCY_DOD.md`
4. `docs/_core/OPERATING_MODEL.md`
5. `docs/_core/CHANGE_RULES.md`
6. `docs/foundation/overview.md`
7. `docs/PLATFORM_DOSSIER.md`
8. `docs/foundation/topology.md`
9. `docs/INTEGRATIONS.md`
10. `docs/OPENCODE.md`
11. `docs/foundation/testing.md`
12. `docs/foundation/node-toolchain.md`

## Read Order (agents)
1. `docs/_core/README.md`
2. `docs/_core/SOURCES_OF_TRUTH.md`
3. `docs/_core/CONSISTENCY_DOD.md`
4. `DOCS_CONTRACT.md`
5. `docs/PLATFORM_DOSSIER.md`
6. `docs/foundation/overview.md`
7. `docs/foundation/topology.md`
8. `docs/INTEGRATIONS.md`
9. `docs/OPENCODE.md`
10. `docs/foundation/testing.md`
11. `docs/_core/OPERATING_MODEL.md`
12. `docs/_core/CHANGE_RULES.md`
13. `docs/foundation/node-toolchain.md`

## Repo-Root Descent
- Start with root `AGENTS.md`, then use `docs/_core/README.md` as the doc hub.
- For a touched layer, read that layer's `AGENTS.md`, `CONSTRAINTS.md`,
  `DEPENDENCIES.md`, and `RUNBOOK.md`.
- For a touched service, read that service's `AGENTS.md`, `CONSTRAINTS.md`,
  `RUNBOOK.md`, and `SERVICE_SPEC.md`.
- If working below the service root, read each deeper applicable `AGENTS.md`
  on the path to the touched directory.

### Live-Tree Preflight
Use this when confirming the current nested `AGENTS.md` boundaries before
planning deeper-than-service work.

```bash
find layer-* -path '*/AGENTS.md' | sort

python3 - <<'PY'
from pathlib import Path
for p in sorted(Path('.').glob('layer-*/*/*/AGENTS.md')):
    print(p)
PY
```

## Canonical Links
- `docs/foundation/overview.md`
- `docs/foundation/topology.md`
- `docs/foundation/testing.md`
- `docs/foundation/node-toolchain.md`
- `docs/PLATFORM_DOSSIER.md`
- `docs/INTEGRATIONS.md`
- `docs/OPENCODE.md`
- `docs/_core/CONSISTENCY_DOD.md`

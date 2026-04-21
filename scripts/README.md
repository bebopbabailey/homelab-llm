# scripts

Repository utility scripts.

## Current scripts
- `validate_handles.py` — validates `platform/registry/handles.jsonl`
  for schema, naming constraints, and duplicate tuple collisions.
- `service_registry.py` — resolves canonical service metadata from
  `platform/registry/services.jsonl`.
- `service_registry_audit.py` — audits registry coverage against discovered
  service roots and validates the service catalog.
- `docs_contract_audit.py` — audits layer taxonomy README coverage and
  service-level docs contract completeness (`README`, `SERVICE_SPEC`,
  `ARCHITECTURE`, `AGENTS`, `CONSTRAINTS`, `RUNBOOK`, `TASKS`).
- `repo_hygiene_audit.py` — audits root-file allowlist, journal index/link
  shape, and top-level archive shape against
  `docs/_core/root_hygiene_manifest.json`.
- `control_plane_sync_audit.py` — audits that repo-local skill/validator
  contracts are reflected across the docs and workflow surfaces that describe
  them.
- `docs_link_audit.py` — audits internal markdown links on root markdown,
  `docs/**`, layer/service bundle markdown, `platform/ops/README.md`, and
  `scripts/README.md`.
- `worktree_effort.py` — manages local per-worktree effort metadata and blocks
  unsafe `Build`/`Verify` work when concurrent implementation scopes overlap or
  the current dirty tree exceeds its declared effort scope. The primary
  worktree is baseline-only and cannot host `Build`/`Verify` work.
- `start_effort.py` — creates a linked worktree from a clean primary `master`
  baseline, registers the effort, and runs preflight before implementation
  starts.
- `closeout_effort.py` — lands a linked worktree locally by committing scoped
  work if needed, running repo audits, fast-forward merging to `master`,
  closing local metadata, removing the linked worktree, and deleting the local
  branch.
- `abandon_effort.py` — abandons a failed linked worktree without losing
  append-only journal records; it blocks deletion on unsalvaged
  `docs/journal/` deltas unless `--salvage-journal` is used.
- `repo_snapshot_zip.py` — packages the current repo filesystem snapshot as it
  exists on disk, including service contents automatically, while excluding
  obvious local heavyweight junk such as `.git`, `.venv*`, caches, and build
  artifacts; copies the ZIP to `studio:~/` by default.
- `websearch_eval_summary.py` — summarizes saved promptfoo web-search eval
  JSON outputs into a markdown report with latency, blocked-domain hits,
  category breakdowns, and `owui-fast` vs `owui-research` comparison tables.
- `websearch_review_packet.py` — builds a reviewer-friendly directory from saved
  web-search eval JSON artifacts, including per-slice markdown packets, copied
  summaries, and blank scoring CSVs in one place.
- `websearch_score_rollup.py` — aggregates manually completed web-search
  scoring CSVs into a markdown comparison grouped by profile and lane.
- `play_orin_tts_voices.sh` — runs over `ssh orin`, fetches registered
  `voice-gateway` voices, synthesizes one WAV per voice, and plays them through
  the Orin audio output.

## Usage
- Orin TTS voice cycle:
  - `scripts/play_orin_tts_voices.sh`
  - list active voices only: `scripts/play_orin_tts_voices.sh --list`
  - filter to selected voices: `scripts/play_orin_tts_voices.sh af_nova am_echo`
  - force ALSA path: `PLAYER=aplay scripts/play_orin_tts_voices.sh`
- Prefer `uv run python scripts/validate_handles.py`.
- Default path target is `platform/registry/handles.jsonl`.
- Docs contract audit:
  - `uv run python scripts/docs_contract_audit.py`
  - `uv run python scripts/docs_contract_audit.py --json`
  - `uv run python scripts/docs_contract_audit.py --strict --json`
  - `--json` preserves the existing service keys and appends layer taxonomy audit keys:
    `required_layer_files`, `layer_count`, `layers`, `layers_with_gaps`,
    `layers_ok`, `overall_ok`
- Repo hygiene audit:
  - `uv run python scripts/repo_hygiene_audit.py`
  - `uv run python scripts/repo_hygiene_audit.py --json`
  - `uv run python scripts/repo_hygiene_audit.py --scope root --strict --json`
  - `uv run python scripts/repo_hygiene_audit.py --scope journal --json`
  - `uv run python scripts/repo_hygiene_audit.py --scope archive --json`
  - checks root-file allowlist drift, journal index/link drift, and top-level archive shape
- Control-plane sync audit:
  - `uv run python scripts/control_plane_sync_audit.py`
  - `uv run python scripts/control_plane_sync_audit.py --json`
  - `uv run python scripts/control_plane_sync_audit.py --strict --json`
  - checks that repo-local durability and hygiene contracts are reflected in the
    docs/workflow surfaces that describe them
- Docs link audit:
  - `uv run python scripts/docs_link_audit.py`
  - checks root markdown, `docs/**`, layer/service bundle markdown,
    `platform/ops/README.md`, and `scripts/README.md`
- Worktree effort preflight:
  - `uv run python scripts/start_effort.py --id <id> --scope <repo-path> --json`
  - `uv run python scripts/start_effort.py --id <id> --service <service-id> --json`
  - `uv run python scripts/worktree_effort.py park --notes "holding context" --json`
  - `uv run python scripts/worktree_effort.py register --effort-id <id> --stage build --scope <repo-path>`
  - `uv run python scripts/worktree_effort.py status --json`
  - `uv run python scripts/worktree_effort.py preflight --stage build --json`
  - `uv run python scripts/worktree_effort.py preflight --stage verify --json`
  - `uv run python scripts/worktree_effort.py close --json`
  - `uv run python scripts/closeout_effort.py --worktree <linked-worktree-path> --json`
  - `uv run python scripts/abandon_effort.py --worktree <linked-worktree-path> --json`
  - `uv run python scripts/abandon_effort.py --worktree <linked-worktree-path> --salvage-journal --json`
  - `start_effort.py` is the normal bootstrap path from the primary worktree
  - `start_effort.py` rejects broad parallel docs/layer scopes and cleans up a
    partially created lane automatically on bootstrap failure
  - the primary worktree is baseline-only, so `register --stage build|verify`
    and implementation preflight must run in the linked worktree
  - use `park` for dirty context-only worktrees and `register` for active
    `build`/`verify` work
  - `close` removes the local metadata file and returns the worktree to a null state
  - `close` is metadata-only; use `closeout_effort.py` when you want to land a
    finished lane and restore the boring baseline
  - `closeout_effort.py` is local-only and deterministic: no auto-rebase, no
    push, and no automatic `NOW.md` edits
  - `abandon_effort.py` is the failed-lane deletion path; journal deltas must be
    salvaged to `master` before pruning
  - first-party services under `layer-*` are plain tracked directories, not
    submodules
  - keeps concurrent implementation state local to each worktree and out of repo-tracked files
- Service registry:
  - `uv run python scripts/service_registry.py show litellm-orch --json`
  - `uv run python scripts/service_registry.py path open-webui`
  - `uv run python scripts/service_registry_audit.py --strict --json`
  - `platform/registry/services.jsonl` is the canonical service taxonomy during
    the current service-centric layout
  - repo-local ops/validation scripts should resolve first-party service roots
    through the service registry instead of hardcoded `layer-*` path maps
  - broad `services` and `experiments` scopes are treated like broad `layer-*`
    scopes for concurrent-effort safety once those roots are live
  - `legacy_paths` is historical traceability only
  - `layer-*` is README-only taxonomy/navigation, not a live service-root surface
- Repo review snapshot ZIP:
  - `./scripts/repo_snapshot_zip.py`
  - filesystem-based and Git-independent at runtime
  - prints progress while writing the ZIP
- Web-search eval summary:
  - `uv run python scripts/websearch_eval_summary.py --input evals/websearch/artifacts/<run>.json`
  - optional blocked-domain override:
    `uv run python scripts/websearch_eval_summary.py --input <run>.json --blocked-domains evals/websearch/blocked_domains.txt`
- Web-search review packet:
  - `uv run python scripts/websearch_review_packet.py --input evals/websearch/artifacts/<run-a>.json --input evals/websearch/artifacts/<run-b>.json --output-dir evals/websearch/review/<packet>`
- Web-search manual score rollup:
  - `uv run python scripts/websearch_score_rollup.py --input <scored>.csv --baseline baseline:owui-fast`

## Canonical references
- Registry contract context: `docs/INTEGRATIONS.md`
- Truth hierarchy: `docs/_core/SOURCES_OF_TRUTH.md`

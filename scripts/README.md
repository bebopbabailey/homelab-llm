# scripts

Repository utility scripts.

## Current scripts
- `validate_handles.py` — validates `layer-gateway/registry/handles.jsonl`
  for schema, naming constraints, and duplicate tuple collisions.
- `docs_contract_audit.py` — audits layer-level docs contract completeness
  (`README`, `AGENTS`, `CONSTRAINTS`, `DEPENDENCIES`, `RUNBOOK`) and
  service-level docs contract completeness (`README`, `SERVICE_SPEC`,
  `ARCHITECTURE`, `AGENTS`, `CONSTRAINTS`, `RUNBOOK`, `TASKS`).
- `repo_snapshot_zip.py` — packages the current repo filesystem snapshot as it
  exists on disk, including submodule contents automatically, while excluding
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
- Default path target is `layer-gateway/registry/handles.jsonl`.
- Docs contract audit:
  - `uv run python scripts/docs_contract_audit.py`
  - `uv run python scripts/docs_contract_audit.py --json`
  - `uv run python scripts/docs_contract_audit.py --strict --json`
  - `--json` preserves the existing service keys and appends layer audit keys:
    `required_layer_files`, `layer_count`, `layers`, `layers_with_gaps`,
    `layers_ok`, `overall_ok`
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

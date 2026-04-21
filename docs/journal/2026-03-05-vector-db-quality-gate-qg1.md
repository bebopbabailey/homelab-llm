# 2026-03-05 — Studio vector-store retrieval quality gate (QG1)

## Summary
Implemented a deterministic evaluation scaffold for Studio main vector-store
retrieval tuning (QG1), including a fixed 24-query pack, judgment template, and
CLI helper for run/scoring/comparison.

No runtime ports/bindings changed.

## What changed
- Added fixed query pack:
  - `layer-data/vector-db/eval/query_pack.v1.jsonl`
- Added judgment template:
  - `layer-data/vector-db/eval/judgment_template.v1.csv`
- Added evaluation helper:
  - `layer-data/vector-db/scripts/eval_memory_quality.py`
  - subcommands: `print-pack`, `run-pack`, `score`, `compare`
- Updated runbook/testing with QG1 execution contract and gates:
  - `layer-data/vector-db/RUNBOOK.md`
  - `docs/foundation/testing.md`
- Updated active task tracking:
  - `layer-data/vector-db/TASKS.md`
  - `NOW.md`

## QG1 gates
- `hit_at_5 >= 0.85`
- `mrr_at_10 >= 0.65`
- `ndcg_at_10 >= 0.70`
- `bad_hit_rate_at_5 <= 0.30`
- `p95_latency_ms <= 800`
- every bucket `hit_at_5 >= 0.75`

## Notes
- QG1 is evaluation-only; no integration boundary changes were introduced.
- Labeling is operator-driven (`grade: 2/1/0`) to keep relevance judgments
  explicit before defaults are changed.

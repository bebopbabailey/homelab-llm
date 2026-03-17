# Websearch Review Packet: 20260308T193329Z-lane-review

Start here:
1. Read the per-slice markdown files in this directory.
2. Use the copied summary markdown files in `summaries/` for quick aggregate context.
3. Fill in the score CSVs in this directory.
4. Run `scripts/websearch_score_rollup.py` on the completed CSVs.

## Included slices
- [freshness-high-extra](freshness-high-extra.md)
  - score sheet: `freshness-high-extra-review.csv`
- [smoke](smoke.md)
  - score sheet: `smoke-review.csv`

## Aggregate summaries
- [summaries/20260308T193329Z-baseline-fast-smoke-summary.md](summaries/20260308T193329Z-baseline-fast-smoke-summary.md)
- [summaries/20260308T193329Z-baseline-deep-smoke-summary.md](summaries/20260308T193329Z-baseline-deep-smoke-summary.md)
- [summaries/20260308T193329Z-baseline-fast-freshness-high-extra-summary.md](summaries/20260308T193329Z-baseline-fast-freshness-high-extra-summary.md)
- [summaries/20260308T193329Z-baseline-deep-freshness-high-extra-summary.md](summaries/20260308T193329Z-baseline-deep-freshness-high-extra-summary.md)

## Source artifacts
- `evals/websearch/artifacts/20260308T193329Z-baseline-fast-smoke.json`
- `evals/websearch/artifacts/20260308T193329Z-baseline-deep-smoke.json`
- `evals/websearch/artifacts/20260308T193329Z-baseline-fast-freshness-high-extra.json`
- `evals/websearch/artifacts/20260308T193329Z-baseline-deep-freshness-high-extra.json`

## Score rollup command
```bash
uv run python scripts/websearch_score_rollup.py \
  --input evals/websearch/review/20260308T193329Z-lane-review/freshness-high-extra-review.csv \
  --input evals/websearch/review/20260308T193329Z-lane-review/smoke-review.csv \
  --baseline baseline:owui-fast \
  --output evals/websearch/review/20260308T193329Z-lane-review/lane-rollup.md
```

If `owui-fast` is not the baseline you want, change `--baseline` before running the rollup.

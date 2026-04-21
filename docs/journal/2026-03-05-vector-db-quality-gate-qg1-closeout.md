# 2026-03-05 — Studio vector-store QG1 run-matrix execution + provisional closeout

## Summary
Executed the full QG1 run matrix on Studio memory API and completed a baseline
confirmation run (`R5`).

Current result under provisional auto-labeled judgments: **no gate-passing
candidate**. Retrieval defaults remain unchanged.

## What was executed
- Studio preflight health/stats:
  - `GET /health` on `127.0.0.1:55440` -> ok
  - `GET /v1/memory/stats` -> stable counts
- QG1 matrix runs:
  - `R0`: `qwen, top_k=10, lexical_k=30, vector_k=30`
  - `R1`: `qwen, top_k=10, lexical_k=60, vector_k=20`
  - `R2`: `qwen, top_k=10, lexical_k=20, vector_k=60`
  - `R3`: `qwen, top_k=12, lexical_k=30, vector_k=30`
  - `R4`: `mxbai, top_k=10, lexical_k=30, vector_k=30`
- Confirmation run:
  - `R5`: baseline repeat of `R0` params

Artifacts were written under:
- `/home/christopherbailey/homelab-data/memory-eval`
  - `R0..R5.run.json`
  - `R0..R5.judgments.csv` (provisional auto labels)
  - `R0..R5.score.json`
  - `R1..R5.vs.R0.json`

## Provisional metrics snapshot
- `R0`: `hit@5=0.25`, `mrr@10=0.2083`, `ndcg@10=0.2755`, `bad@5=0.8167`, `p95=1912.561`
- `R1`: `hit@5=0.25`, `mrr@10=0.2083`, `ndcg@10=0.2701`, `bad@5=0.8250`, `p95=113.408`
- `R2`: `hit@5=0.25`, `mrr@10=0.2083`, `ndcg@10=0.2755`, `bad@5=0.8167`, `p95=177.421`
- `R3`: `hit@5=0.25`, `mrr@10=0.2083`, `ndcg@10=0.2755`, `bad@5=0.8167`, `p95=186.014`
- `R4`: `hit@5=0.2917`, `mrr@10=0.2188`, `ndcg@10=0.3204`, `bad@5=0.7417`, `p95=809.660`
- `R5`: `hit@5=0.25`, `mrr@10=0.2083`, `ndcg@10=0.2755`, `bad@5=0.8167`, `p95=185.088`

Gate status (all runs): fail (`hit@5`, `mrr@10`, `ndcg@10`, `bad@5`, bucket-floor).
Latency gate passed for `R1/R2/R3/R5`; failed for `R0/R4`.

## Important caveat
This closeout is **provisional** because judgments were auto-generated from a
signal-match heuristic. Authoritative QG1 disposition still requires manual
human grading of `R0..R5` judgment files before any default-lock decision.

## Outcome
- No retrieval-default changes applied.
- QG1 remains open pending manual judgments and re-score.

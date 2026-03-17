# Runbook: Vector DB (Studio Main Store)

## Scope
Studio-local operations for Postgres + pgvector and memory API.

Canonical source tree:
- `/home/christopherbailey/homelab-llm/layer-data/vector-db`

Current Studio runtime target:
- `/Users/thestudio/optillm-proxy/layer-data/vector-db`

## Utility wrapper
Use the Studio utility wrapper for transient remote commands:
`platform/ops/scripts/studio_run_utility.sh`.

## Preflight (Mini)
```bash
uv run python platform/ops/scripts/validate_studio_policy.py --json
uv run python platform/ops/scripts/audit_studio_scheduling.py --policy-only --json
uv run python platform/ops/scripts/audit_studio_scheduling.py --host studio --json
```

## Deploy service code to Studio
```bash
cd /home/christopherbailey/homelab-llm
./layer-data/vector-db/scripts/deploy_studio.sh
```

Preview sync first:
```bash
cd /home/christopherbailey/homelab-llm
./layer-data/vector-db/scripts/deploy_studio.sh --dry-run
```

## Initialize DB on Studio (legacy schema)
```bash
platform/ops/scripts/studio_run_utility.sh --host studio -- \
  "cd /Users/thestudio/optillm-proxy/layer-data/vector-db && ./scripts/studio_install.sh"
```

## Initialize Haystack schema/tables (new backend)
```bash
platform/ops/scripts/studio_run_utility.sh --host studio -- \
  "cd /Users/thestudio/optillm-proxy/layer-data/vector-db && \
   uv run python scripts/init_haystack_schema.py"
```

## Start/restart Studio launchd labels
```bash
platform/ops/scripts/studio_run_utility.sh --host studio --sudo -- \
  "launchctl bootstrap system /Library/LaunchDaemons/com.bebop.pgvector-main.plist || true"
platform/ops/scripts/studio_run_utility.sh --host studio --sudo -- \
  "launchctl bootstrap system /Library/LaunchDaemons/com.bebop.memory-api-main.plist || true"
platform/ops/scripts/studio_run_utility.sh --host studio --sudo -- \
  "launchctl kickstart -k system/com.bebop.pgvector-main"
platform/ops/scripts/studio_run_utility.sh --host studio --sudo -- \
  "launchctl kickstart -k system/com.bebop.memory-api-main"
```

## Health checks
```bash
platform/ops/scripts/studio_run_utility.sh --host studio -- \
  "curl -fsS http://127.0.0.1:55440/health | jq ."
platform/ops/scripts/studio_run_utility.sh --host studio -- \
  "curl -fsS http://127.0.0.1:55440/v1/memory/stats | jq ."
platform/ops/scripts/studio_run_utility.sh --host studio -- \
  "lsof -nP -iTCP -sTCP:LISTEN | egrep ':55432|:55440'"
```

## Ingestion run (JSONL)
```bash
platform/ops/scripts/studio_run_utility.sh --host studio -- \
  "cd /Users/thestudio/optillm-proxy/layer-data/vector-db && \
   MEMORY_BACKEND=haystack \
   MEMORY_INGEST_MODE=jsonl \
   MEMORY_INGEST_PATH=/Users/thestudio/data/memory-main/ingest/events.codex-history.pilot.normalized.jsonl \
   ./scripts/run_ingest.sh"
```

## Ingestion run (manuals PDF lane)
```bash
platform/ops/scripts/studio_run_utility.sh --host studio -- \
  "cd /Users/thestudio/optillm-proxy/layer-data/vector-db && \
   MEMORY_BACKEND=haystack \
   MEMORY_INGEST_MODE=manuals_pdf \
   MEMORY_MANUALS_PDF_GLOB='/Users/thestudio/data/memory-main/manuals/**/*.pdf' \
   MEMORY_MANUALS_SOURCE=manuals_pdf \
   ./scripts/run_ingest.sh"
```

## Retrieval smoke
```bash
platform/ops/scripts/studio_run_utility.sh --host studio -- \
  "curl -fsS http://127.0.0.1:55440/v1/memory/search \
    -H 'Content-Type: application/json' \
    -d '{\"query\":\"mlxctl sync-gateway\",\"top_k\":5,\"model_space\":\"qwen\"}' | jq ."
```

## Cutover
1) Keep default in service env: `MEMORY_BACKEND=legacy` until validation passes.
2) Enable haystack mode in service env and restart `com.bebop.memory-api-main`.
3) Verify `/health`, `/v1/memory/stats`, and retrieval smoke.

## Rollback
```bash
# 1) Set MEMORY_BACKEND=legacy in service env
# 2) Restart memory API label
platform/ops/scripts/studio_run_utility.sh --host studio --sudo -- \
  "launchctl kickstart -k system/com.bebop.memory-api-main"
```

## Backup run
```bash
platform/ops/scripts/studio_run_utility.sh --host studio -- \
  "cd /Users/thestudio/optillm-proxy/layer-data/vector-db && ./scripts/run_backup.sh"
```

## Docs retrieval quality gate
Canonical flow:
1. `run-pack`
2. `autolabel`
3. `triage`
4. optional flagged-only `label`
5. `score`

Canonical eval artifacts are:
- ranked retrieval output (`run.json`)
- judgments keyed by `chunk_id` in `judgments.csv`

`score` converts those artifacts internally into TREC-style `run` + `qrels`
structures and computes canonical IR metrics through `ir-measures`
(`Success@5`, `RR@10`, `nDCG@10`, `P@5`). Only these remain custom:
- `p95_latency_ms`
- `bad_hit_rate_at_5`

Run the docs pack on Studio:
```bash
platform/ops/scripts/studio_run_utility.sh --host studio -- \
  "cd /Users/thestudio/optillm-proxy && \
   uv run python layer-data/vector-db/scripts/eval_memory_quality.py run-pack \
     --pack layer-data/vector-db/eval/query_pack.docs.v1.jsonl \
     --api-base http://127.0.0.1:55440 \
     --model-space qwen \
     --top-k 10 \
     --lexical-k 30 \
     --vector-k 30 \
     --run-id D1 \
     --out /Users/thestudio/data/memory-main/eval/D1.run.json"
```

Auto-label conservatively:
```bash
platform/ops/scripts/studio_run_utility.sh --host studio -- \
  "cd /Users/thestudio/optillm-proxy && \
   uv run python layer-data/vector-db/scripts/eval_memory_quality.py autolabel \
     --run-json /Users/thestudio/data/memory-main/eval/D1.run.json \
     --out-csv /Users/thestudio/data/memory-main/eval/D1.judgments.auto.csv \
     --mode conservative_graded \
     --labeler codex-auto \
     --run-id D1"
```

Flag only the cases that need human review:
```bash
platform/ops/scripts/studio_run_utility.sh --host studio -- \
  "cd /Users/thestudio/optillm-proxy && \
   uv run python layer-data/vector-db/scripts/eval_memory_quality.py triage \
     --run-json /Users/thestudio/data/memory-main/eval/D1.run.json \
     --judgments /Users/thestudio/data/memory-main/eval/D1.judgments.auto.csv \
     --out /Users/thestudio/data/memory-main/eval/D1.triage.json"
```

Review only flagged cases when triage output is non-empty:
```bash
ssh -t studio "cd /Users/thestudio/optillm-proxy && \
  uv run python layer-data/vector-db/scripts/eval_memory_quality.py label \
    --run-json /Users/thestudio/data/memory-main/eval/D1.run.json \
    --seed-judgments /Users/thestudio/data/memory-main/eval/D1.judgments.auto.csv \
    --triage-json /Users/thestudio/data/memory-main/eval/D1.triage.json \
    --out-csv /Users/thestudio/data/memory-main/eval/D1.judgments.final.csv \
    --labeler chris \
    --run-id D1"
```

If there are no triage flags, promote auto labels directly:
```bash
platform/ops/scripts/studio_run_utility.sh --host studio -- \
  "cp /Users/thestudio/data/memory-main/eval/D1.judgments.auto.csv \
      /Users/thestudio/data/memory-main/eval/D1.judgments.final.csv"
```

Score the run:
```bash
platform/ops/scripts/studio_run_utility.sh --host studio -- \
  "cd /Users/thestudio/optillm-proxy && \
   uv run python layer-data/vector-db/scripts/eval_memory_quality.py score \
     --run-json /Users/thestudio/data/memory-main/eval/D1.run.json \
     --judgments /Users/thestudio/data/memory-main/eval/D1.judgments.final.csv \
     --out /Users/thestudio/data/memory-main/eval/D1.score.json && \
   jq '{metrics_support,metrics_disconfirm,gates,diagnostics,bucket_hit_at_5_support}' \
      /Users/thestudio/data/memory-main/eval/D1.score.json"
```

# Runbook: Vector DB (Studio Main Store)

## Scope
Studio-hosted retrieval operations for the memory API and its Elastic-backed
primary backend.

Canonical source tree:
- `/home/christopherbailey/homelab-llm/services/vector-db`

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
./services/vector-db/scripts/deploy_studio.sh
```

Preview sync first:
```bash
cd /home/christopherbailey/homelab-llm
./services/vector-db/scripts/deploy_studio.sh --dry-run
```

## Start/restart Studio launchd label
```bash
platform/ops/scripts/studio_run_utility.sh --host studio --sudo -- \
  "launchctl bootstrap system /Library/LaunchDaemons/com.bebop.elasticsearch-memory-main.plist || true"
platform/ops/scripts/studio_run_utility.sh --host studio --sudo -- \
  "launchctl kickstart -k system/com.bebop.elasticsearch-memory-main"
platform/ops/scripts/studio_run_utility.sh --host studio --sudo -- \
  "launchctl bootstrap system /Library/LaunchDaemons/com.bebop.memory-api-main.plist || true"
platform/ops/scripts/studio_run_utility.sh --host studio --sudo -- \
  "launchctl kickstart -k system/com.bebop.memory-api-main"
```

## Elastic/version preflight
Run this before treating the Elastic backend as active:
```bash
platform/ops/scripts/studio_run_utility.sh --host studio -- \
  "curl -fsS ${MEMORY_ELASTIC_URL:-http://127.0.0.1:9200}/ | jq '{version:.version.number,cluster_name}'"
platform/ops/scripts/studio_run_utility.sh --host studio -- \
  "curl -fsS ${MEMORY_ELASTIC_URL:-http://127.0.0.1:9200}/_license | jq .license"
```

Expected:
- version is at least `8.19.x`
- preferred path is pinned `9.3.3`
- license probe succeeds and is reported in `/health` and `/v1/memory/stats`

## Health checks
```bash
curl -fsS http://192.168.1.72:55440/health | jq .
curl -fsS http://192.168.1.72:55440/v1/memory/stats | jq .
platform/ops/scripts/studio_run_utility.sh --host studio -- \
  "curl -fsS http://127.0.0.1:9200/_cluster/health?pretty"
platform/ops/scripts/studio_run_utility.sh --host studio -- \
  "lsof -nP -iTCP -sTCP:LISTEN | egrep ':9200|:55440'"
```

Expected stats fields:
- `index_alias`
- `index_name`
- `documents`
- `chunks`
- `response_maps`
- `embedding_model`
- `embedding_dims`
- `vector_index_type`
- `hnsw_m`
- `hnsw_ef_construction`
- `single_doc_exact_max_chunks`
- `retriever_mode`

## Retrieval smoke
```bash
curl -fsS http://192.168.1.72:55440/v1/memory/search \
  -H 'Content-Type: application/json' \
  -d '{"query":"mlxctl sync-gateway","profile":"balanced","document_id":"ops:mlxctl-guide"}' | jq .
```

## Response-map smoke
```bash
TOKEN="$(platform/ops/scripts/studio_run_utility.sh --host studio -- \
  'cat /Users/thestudio/data/memory-main/secrets/memory-api-write-token')"
curl -fsS http://192.168.1.72:55440/v1/memory/response-map/upsert \
  -H "Authorization: Bearer ${TOKEN}" \
  -H 'Content-Type: application/json' \
  -d '{"response_id":"resp_test","document_id":"youtube:test","source_type":"youtube","summary_mode":"indexed_long"}' | jq .
curl -fsS http://192.168.1.72:55440/v1/memory/response-map/resolve \
  -H 'Content-Type: application/json' \
  -d '{"response_id":"resp_test"}' | jq .
```

## Ingestion runs
JSONL/manual ingest still flows through `app/ingest.py`. The preferred v1
upsert surface is explicit chunk records with spans.

Example direct upsert:
```bash
TOKEN="$(platform/ops/scripts/studio_run_utility.sh --host studio -- \
  'cat /Users/thestudio/data/memory-main/secrets/memory-api-write-token')"
curl -fsS http://192.168.1.72:55440/v1/memory/upsert \
  -H "Authorization: Bearer ${TOKEN}" \
  -H 'Content-Type: application/json' \
  -d '{
    "documents":[
      {
        "document_id":"youtube:test",
        "source_type":"youtube",
        "source":"youtube",
        "title":"test video",
        "uri":"https://youtu.be/test",
        "chunks":[
          {"chunk_index":0,"text":"hello world","timestamp_label":"00:00","start_ms":0,"end_ms":1000}
        ]
      }
    ]
  }' | jq .
```

Write-auth smoke:
```bash
curl -sS -o /tmp/memory-unauth.json -w '%{http_code}\n' \
  -X POST http://192.168.1.72:55440/v1/memory/upsert \
  -H 'Content-Type: application/json' \
  -d '{"documents":[{"source":"memory://unauth","text":"probe"}]}'
cat /tmp/memory-unauth.json
```
Expected:
- `401` without a bearer token

## Reindex path
Use a fresh physical chunk index whenever any of these change:
- embedding model
- embedding dims
- vector `index_options.type`
- HNSW `m`
- HNSW `ef_construction`

Operator sequence:
1. Create a fresh physical index generation with the new mapping.
2. Re-embed or `_reindex` into the new target as appropriate.
3. Validate retrieval quality and latency on the new generation.
4. Move the `memory-chunks-current` alias to the new index.
5. Retire the old generation only after rollback confidence is no longer needed.

Important:
- changing `index_options` on the mapping does not retroactively rebuild
  already-indexed vectors
- clean evaluation requires a fresh index generation

## Cutover
1. Set `MEMORY_BACKEND=elastic` in the Studio service env.
2. Ensure `com.bebop.elasticsearch-memory-main` is healthy on `127.0.0.1:9200`.
3. Restart `com.bebop.memory-api-main`.
4. Verify `/health`, `/v1/memory/stats`, retrieval smoke, and response-map
   resolution.
5. Run the eval gates before treating the backend as accepted.

## Rollback
```bash
# 1) Set MEMORY_BACKEND=legacy in the service env
# 2) Restart the memory API label
platform/ops/scripts/studio_run_utility.sh --host studio --sudo -- \
  "launchctl kickstart -k system/com.bebop.memory-api-main"
```

## Snapshots
```bash
platform/ops/scripts/studio_run_utility.sh --host studio -- \
  "cd /Users/thestudio/optillm-proxy/layer-data/vector-db && \
   MEMORY_ELASTIC_URL=http://127.0.0.1:9200 \
   MEMORY_ELASTIC_SNAPSHOT_DIR=/Users/thestudio/optillm-proxy/layer-data/vector-db/runtime/elasticsearch-snapshots \
   ./scripts/register_snapshot_repo.sh"

platform/ops/scripts/studio_run_utility.sh --host studio -- \
  "curl -fsS -X PUT http://127.0.0.1:9200/_snapshot/memory-main-repo/manual-\$(date +%Y%m%d)?wait_for_completion=true \
    -H 'Content-Type: application/json' -d '{}'"
```
Restore reference:
```bash
platform/ops/scripts/studio_run_utility.sh --host studio -- \
  "curl -fsS -X POST http://127.0.0.1:9200/_snapshot/memory-main-repo/<snapshot-name>/_restore \
    -H 'Content-Type: application/json' -d '{\"indices\":\"memory-*\",\"include_global_state\":true}'"
```

## Eval gates
Canonical retrieval acceptance now includes:
- `hit@5`
- `MRR@10`
- citation/span correctness
- absent-answer refusal accuracy
- ingest latency
- query latency

Use the existing eval scripts as the reporting surface:
```bash
cd /home/christopherbailey/homelab-llm/services/vector-db
uv run python scripts/eval_memory_quality.py --help
uv run python scripts/eval_ir.py
```

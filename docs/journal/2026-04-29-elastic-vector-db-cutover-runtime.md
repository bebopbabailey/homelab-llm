# 2026-04-29 Elastic vector-db cutover runtime

## Objective
Bring the Elastic-backed `services/vector-db` cutover to a real Studio runtime,
validate the Mini-facing memory API, and prove that the new retrieval state is
durable enough for `task-youtube-summary` follow-up grounding.

## Runtime shape
- Studio architecture check: `uname -m` returned `arm64`
- Elastic artifact:
  - `https://artifacts.elastic.co/downloads/elasticsearch/elasticsearch-9.3.3-darwin-aarch64.tar.gz`
  - `https://artifacts.elastic.co/downloads/elasticsearch/elasticsearch-9.3.3-darwin-aarch64.tar.gz.sha512`
- Elasticsearch runtime:
  - single-node `9.3.3`
  - `network.host=http.host=transport.host=127.0.0.1`
  - `discovery.type=single-node`
  - `xpack.security.enabled=false`
  - `xpack.security.autoconfiguration.enabled=false`
  - repo-managed data/log/snapshot paths under
    `/Users/thestudio/optillm-proxy/layer-data/vector-db/runtime/`
- Studio launchd labels:
  - `com.bebop.elasticsearch-memory-main`
  - `com.bebop.memory-api-main`
- Memory API:
  - bind `192.168.1.72:55440`
  - `MEMORY_BACKEND=elastic`
  - embedding default `studio-nomic-embed-text-v1.5`
  - dims `768`
  - prefix mode `search_query/search_document`
- Firewall:
  - pf anchor allows Mini `192.168.1.71` to `192.168.1.72:55440`
  - blocks broader inbound access to `55440`

## Decisions and fixes
- Kept Elastic as the only primary retrieval backend; pgvector remains rollback
  only.
- Added the repo-managed Studio Elastic launchd plist and policy-manifest entry.
- Fixed Nomic embedding bootstrap by:
  - loading `SentenceTransformer(..., trust_remote_code=True)`
  - adding `einops` to the vector-db dependency set
- Resolved Elastic health hangs by killing an older manual background
  Elasticsearch process that was competing with the launchd-managed node for
  the same runtime/data tree.
- Kept the memory API write-token contract:
  - token file on Studio:
    `/Users/thestudio/data/memory-main/secrets/memory-api-write-token`
  - read/search routes remain open on the Mini-only LAN path

## Validation evidence
- Policy:
  - `uv run python platform/ops/scripts/validate_studio_policy.py --json`
    passed with the new managed label
- Elasticsearch:
  - root info probe succeeded on `127.0.0.1:9200`
  - `_cluster/health` reached `yellow` on a single node
  - `_license` reported `basic`
- Memory API:
  - `curl http://192.168.1.72:55440/health`
    returned `backend=elastic`, `elastic_version=9.3.3`,
    `embedding_model=studio-nomic-embed-text-v1.5`, `embedding_dims=768`
  - `curl http://192.168.1.72:55440/v1/memory/stats`
    reported:
    - `index_alias=memory-chunks-current`
    - physical chunk index
      `memory-chunks-v1-studio-nomic-embed-text-v1-5-d768-int8_hnsw`
    - `vector_index_type=int8_hnsw`
    - `hnsw_m=16`
    - `hnsw_ef_construction=100`
    - `native_rrf_enabled=true`
- Auth:
  - unauthenticated `POST /v1/memory/upsert` returned `401`
  - authenticated write succeeded with `documents=1`, `chunks=2`
- Retrieval:
  - document-scoped search over a probe document returned the expected chunk
    about retrieval quality
  - `response_id -> document_id` upsert and resolve both succeeded for
    `resp-probe-001`
- Snapshot:
  - snapshot repository registration acknowledged
  - manual snapshot `manual-20260429` succeeded with all shards successful
- Exact vs approximate benchmark on a single document:
  - exact `p50=73.538 ms`, `p95=378.132 ms`
  - approximate `p50=80.778 ms`, `p95=127.987 ms`
  - top-5 overlap was identical on the probe corpus

## Commands of note
- Studio rollout:
  - `./services/vector-db/scripts/deploy_studio.sh`
  - `./services/vector-db/scripts/stage_launchd_plists.sh`
  - `./services/vector-db/scripts/install_memory_api_firewall.sh`
- Snapshot:
  - `./services/vector-db/scripts/register_snapshot_repo.sh`
  - `PUT /_snapshot/memory-main-repo/manual-20260429?wait_for_completion=true`
- Benchmark:
  - `uv run python services/vector-db/scripts/benchmark_single_document_retrieval.py --api-base http://192.168.1.72:55440 --document-id bench-doc --query 'Which section discusses approximate HNSW search and latency?' --runs 5`

## Cleanup state
- The stray manual Elastic process tree from the earlier bootstrap trial was
  killed before the final health pass.
- Probe and benchmark documents were deleted from the memory API after the
  smokes.
- The manual snapshot remains in the registered repository as the v1 restore
  proof.

## Completion note
- The linked rollout lane was later merged to `master`, pushed to `origin`,
  and restarted on both Studio and Mini.
- The Studio memory API write token was wired into the Mini LiteLLM runtime
  before the live gateway restart.
- Initial `task-youtube-summary` live validation passed after the retrieval
  cutover, and the subsequent follow-up lane now redesigns transcript
  acquisition around `media-fetch-mcp` rather than revisiting the Elastic
  retrieval substrate itself.

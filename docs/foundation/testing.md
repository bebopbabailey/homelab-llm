# Testing and Verification

This doc captures the recommended test steps for new changes. Run these on the
appropriate host and confirm outputs before declaring a change complete.

## MLX Registry and Controller (Studio)

Current runtime baseline (per-port MLX lanes):
```bash
mlxctl init
mlxctl ensure <hf_repo_id> --convert auto
mlxctl list
mlxctl status
mlxctl verify
mlxctl studio-cli-sha
```

Notes:
- `mlxctl ensure` takes a Hugging Face repo id (example: `mlx-community/Qwen3-4B-Instruct-2507-gabliterated-mxfp4`).
  Use `mlxctl list` to discover canonical `mlx-*` model ids.
- `mlxctl verify` is read-only by default and also validates (on gateway hosts) that
  served MLX handles in `layer-gateway/registry/handles.jsonl` exist in the Studio registry.
- Use `mlxctl verify --fix-defaults` only when explicitly persisting inferred defaults.

Expanded runtime inspection:
```bash
mlxctl status --checks
mlxctl status --checks --json
mlxctl status --json
```

`status --checks` includes `http_models_ok` so lanes can be considered healthy
even when `listener_visible=false` under root-owned launchd runtime.

Lane drift recovery (disabled/unloaded launchd labels):
```bash
mlxctl repair-lanes --json
mlxctl repair-lanes --apply --json
mlxctl status --checks --json
mlxctl verify
```

`repair-lanes` is safe to run from Mini; it fetches Studio registry/status and
applies launchctl actions on Studio only when `--apply` is used.

`mlx-launch-start --ports` now refuses partial assigned-team-lane scope by
default. Use `--allow-partial` only for intentional scoped restarts.

Lane load/unload:
```bash
mlxctl load <hf_repo_id_or_mlx_model_id> 8100
mlxctl status --checks
mlxctl unload 8100
mlxctl status --checks
```

Unload all ports:
```bash
mlxctl unload-all
```

Reconcile after reboot:
```bash
mlxctl reconcile --json
mlxctl reconcile --apply --json
```

## MLX lanes (Studio)
After reboot or launchd restart, confirm all active `mlxctl` assignments are serving
`/v1/models`.
Note: `GET /v1/models` on the Studio may return a local filesystem snapshot path
as the model `id`. Use `mlxctl status` for canonical model/port mapping.

As of `2026-03-01`, expected production active lanes are `8100`, `8101`, and `8102`.
Any deviation should be treated as drift and triaged with `mlxctl status --checks`
and `mlxctl verify`.

```bash
ACTIVE_PORTS=$(ssh studio "mlxctl status --json | jq -r '.ports[] | select(.status==\"listening\" or .status==\"running\") | .port'")
for p in $ACTIVE_PORTS; do
  ssh studio "curl -fsS http://127.0.0.1:${p}/v1/models | jq ."
done
```

## Studio scheduling policy (Mini -> Studio)
This section is authoritative for Studio scheduling verification workflow.

Policy source of truth:
- `platform/ops/templates/studio_scheduling_policy.json`
- `docs/foundation/studio-scheduling-policy.md`

Quick path (recommended order):
1) `uv run python platform/ops/scripts/validate_studio_policy.py --json`
2) `uv run python platform/ops/scripts/audit_studio_scheduling.py --policy-only --json`
3) `uv run python platform/ops/scripts/audit_studio_scheduling.py --host studio --json`
4) optional read-only check: `uv run python platform/ops/scripts/enforce_studio_launchd_policy.py --host studio --json`
5) apply only when needed, in staged order (`optillm-proxy` then `mlx-lane.*`), then rerun strict audit

Deterministic local checks:
```bash
uv run python platform/ops/scripts/validate_studio_policy.py --json
uv run python platform/ops/scripts/audit_studio_scheduling.py --policy-only --json
```

Remote check-only:
```bash
uv run python platform/ops/scripts/enforce_studio_launchd_policy.py --host studio --json
uv run python platform/ops/scripts/audit_studio_scheduling.py --host studio --json
```

Robust plist key spot-check (no brittle exit-code presence test):
```bash
ssh studio "sudo -n plutil -convert json -o - /Library/LaunchDaemons/com.bebop.mlx-lane.8100.plist | jq '{ProcessType, Nice, LowPriorityIO, LowPriorityBackgroundIO}'"
ssh studio "sudo -n plutil -convert json -o - /Library/LaunchDaemons/com.bebop.mlx-lane.8101.plist | jq '{ProcessType, Nice, LowPriorityIO, LowPriorityBackgroundIO}'"
ssh studio "sudo -n plutil -convert json -o - /Library/LaunchDaemons/com.bebop.mlx-lane.8102.plist | jq '{ProcessType, Nice, LowPriorityIO, LowPriorityBackgroundIO}'"
ssh studio "sudo -n plutil -convert json -o - /Library/LaunchDaemons/com.bebop.optillm-proxy.plist | jq '{ProcessType, Nice, LowPriorityIO, LowPriorityBackgroundIO}'"
# Fallback if JSON conversion is unavailable:
ssh studio "sudo -n /usr/libexec/PlistBuddy -c 'Print :ProcessType' /Library/LaunchDaemons/com.bebop.mlx-lane.8100.plist"
ssh studio "sudo -n /usr/libexec/PlistBuddy -c 'Print :ProcessType' /Library/LaunchDaemons/com.bebop.mlx-lane.8101.plist"
ssh studio "sudo -n /usr/libexec/PlistBuddy -c 'Print :ProcessType' /Library/LaunchDaemons/com.bebop.mlx-lane.8102.plist"
ssh studio "sudo -n /usr/libexec/PlistBuddy -c 'Print :ProcessType' /Library/LaunchDaemons/com.bebop.optillm-proxy.plist"
```

Staged apply order:
1) `com.bebop.optillm-proxy` via:
   `uv run python platform/ops/scripts/enforce_studio_launchd_policy.py --host studio --apply --managed-label com.bebop.optillm-proxy --json`
2) validate
3) MLX lane labels via:
   `uv run python platform/ops/scripts/enforce_studio_launchd_policy.py --host studio --apply --managed-label com.bebop.mlx-lane.8100 --json`
   `uv run python platform/ops/scripts/enforce_studio_launchd_policy.py --host studio --apply --managed-label com.bebop.mlx-lane.8101 --json`
   `uv run python platform/ops/scripts/enforce_studio_launchd_policy.py --host studio --apply --managed-label com.bebop.mlx-lane.8102 --json`
4) full strict audit

### Studio main vector-store labels (background lane)
Studio memory store labels included in policy checks:
- `com.bebop.pgvector-main`
- `com.bebop.memory-api-main`
- `com.bebop.memory-ingest-nightly`
- `com.bebop.memory-backup-nightly`

Read-only audit checks:
```bash
uv run python platform/ops/scripts/validate_studio_policy.py --json
uv run python platform/ops/scripts/audit_studio_scheduling.py --host studio --json
ssh studio "sudo -n plutil -convert json -o - /Library/LaunchDaemons/com.bebop.pgvector-main.plist | jq '{ProcessType, Nice, LowPriorityIO, LowPriorityBackgroundIO}'"
ssh studio "sudo -n plutil -convert json -o - /Library/LaunchDaemons/com.bebop.memory-api-main.plist | jq '{ProcessType, Nice, LowPriorityIO, LowPriorityBackgroundIO}'"
```

Runtime smoke checks:
```bash
ssh studio "lsof -nP -iTCP -sTCP:LISTEN | egrep ':55432|:55440'"
ssh studio "curl -fsS http://127.0.0.1:55440/health | jq ."
```

### Studio vector-store retrieval quality gate (QG1)
Goal: tune retrieval defaults using a fixed judged query set before integration.

Print fixed query pack:
```bash
cd /home/christopherbailey/homelab-llm
uv run python layer-data/vector-db/scripts/eval_memory_quality.py print-pack \
  --pack layer-data/vector-db/eval/query_pack.v1.jsonl
```

Baseline run on Studio (`R0`):
```bash
platform/ops/scripts/studio_run_utility.sh --host studio -- \
  "cd /Users/thestudio/optillm-proxy && \
   uv run python layer-data/vector-db/scripts/eval_memory_quality.py run-pack \
     --pack layer-data/vector-db/eval/query_pack.v1.jsonl \
     --api-base http://127.0.0.1:55440 \
     --model-space qwen \
     --top-k 10 \
     --lexical-k 30 \
     --vector-k 30 \
     --run-id R0 \
     --out /Users/thestudio/data/memory-main/eval/R0.run.json"
scp studio:/Users/thestudio/data/memory-main/eval/R0.run.json \
  /home/christopherbailey/homelab-data/memory-eval/R0.run.json
cp /home/christopherbailey/homelab-llm/layer-data/vector-db/eval/judgment_template.v1.csv \
  /home/christopherbailey/homelab-data/memory-eval/R0.judgments.csv
```

After manual top-10 labeling (`grade: 2 relevant / 1 partial / 0 irrelevant`):
```bash
cd /home/christopherbailey/homelab-llm
uv run python layer-data/vector-db/scripts/eval_memory_quality.py score \
  --run-json /home/christopherbailey/homelab-data/memory-eval/R0.run.json \
  --judgments /home/christopherbailey/homelab-data/memory-eval/R0.judgments.csv \
  --out /home/christopherbailey/homelab-data/memory-eval/R0.score.json
```

Gate thresholds:
- `hit_at_5 >= 0.85`
- `mrr_at_10 >= 0.65`
- `ndcg_at_10 >= 0.70`
- `bad_hit_rate_at_5 <= 0.30`
- `p95_latency_ms <= 800`
- every bucket `hit_at_5 >= 0.75`

Runtime lineage check expectation:
- ports `8100/8101/8102` listeners are `vllm serve`
- process ancestry includes `com.bebop.mlx-lane.<port>` lineage

Verify GPT‑OSS content channel is present (requires adequate max_tokens):
```bash
curl -fsS http://127.0.0.1:8102/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"mlx-gpt-oss-20b-mxfp4-q4","messages":[{"role":"user","content":"ping"}],"max_tokens":256}' \
  | jq -r '.choices[0].message | {content, reasoning_content}'
```

Smoke check for raw Harmony-tag leakage (should return no `<|channel|>`):
```bash
curl -fsS http://127.0.0.1:8100/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"mlx-gpt-oss-120b-mxfp4-q4","messages":[{"role":"user","content":"Return one short sentence about oranges."}],"max_tokens":128}' \
  | jq -r '.choices[0].message.content'
```

After any MLX served-set change (handles) or Studio registry/defaults change:
```bash
mlxctl sync-gateway
```

Quality gate (post-reboot / post-change):
```bash
mlxctl status --checks
mlxctl verify
uv run python /home/christopherbailey/homelab-llm/platform/ops/scripts/mlx_quality_gate.py --host 192.168.1.72 --json
```

Expected:
- exit code `0`
- `failed: 0`
- no raw protocol markers in output (`<|channel|>`, `<think>`, tool tags)


## LiteLLM Aliases (Mini)
```bash
curl -fsS http://127.0.0.1:4000/v1/models \
  -H "Authorization: Bearer $LITELLM_API_KEY" | jq .
```

Note: in the current deployment, unauthenticated `GET /health` may return `401`.
Prefer `/health/readiness` as the default probe when validating service liveness.

## Documentation predictability sweep (repo)
Use this when running doc-consistency hardening work for coding-agent safety.

```bash
cd /home/christopherbailey/homelab-llm
uv run python scripts/docs_contract_audit.py --strict --json
uv run python scripts/validate_handles.py
```

Expected:
- `docs_contract_audit.py` returns `ok: true` with `services_with_gaps: 0`.
- `validate_handles.py` returns `ok`.

## OpenCode basic smoke (per host)
Use your local `~/.config/opencode/opencode.json` and run:
```bash
opencode models litellm
opencode run -m litellm/main "Reply with exactly: main-ok"
opencode run -m litellm/deep "Reply with exactly: deep-ok"
opencode run -m litellm/fast "Reply with exactly: fast-ok"
```

Backend preflight for `main` tool-calling:
```bash
./platform/ops/scripts/mlxctl vllm-capabilities --json
./platform/ops/scripts/mlxctl vllm-render --ports 8101 --validate --json
```

If `main` still fails with a parser/auto-tool error, verify lane args directly:
```bash
ssh studio "ps -eo pid,command | rg -- '--port 8101|enable-auto-tool-choice|tool-call-parser'"
```

Direct lane smoke for `tool_choice:\"auto\"`:
```bash
ssh studio "python3 - <<'PY'
import json, urllib.request
payload={
  'model':'mlx-qwen3-next-80b-mxfp4-a3b-instruct',
  'messages':[{'role':'user','content':'Reply with exactly: main-tool-ok'}],
  'tools':[{'type':'function','function':{'name':'noop','description':'noop','parameters':{'type':'object','properties':{}}}}],
  'tool_choice':'auto',
  'max_tokens':32
}
req=urllib.request.Request(
  'http://127.0.0.1:8101/v1/chat/completions',
  data=json.dumps(payload).encode(),
  headers={'Content-Type':'application/json'},
  method='POST',
)
with urllib.request.urlopen(req, timeout=30) as r:
  print(r.status)
PY"
```

## LiteLLM Prometheus (Mini)
```bash
curl -fsS -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  http://127.0.0.1:4000/metrics/ | head -n 20
```
Note: `/metrics` redirects to `/metrics/` (307).

## Prometheus (Mini)
```bash
curl -fsS http://127.0.0.1:9090/-/ready
curl -fsS http://127.0.0.1:9090/-/healthy
```

## Grafana (Mini)
```bash
curl -fsS http://127.0.0.1:3001/api/health
```

Check for MLX aliases:
```bash
curl -fsS http://127.0.0.1:4000/v1/models \
  -H "Authorization: Bearer $LITELLM_API_KEY" \
  | jq -r '.data[].id' | rg '^mlx-'
```

Check for OpenVINO aliases (only when OpenVINO is intentionally wired into LiteLLM):
```bash
curl -fsS http://127.0.0.1:4000/v1/models \
  -H "Authorization: Bearer $LITELLM_API_KEY" \
  | jq -r '.data[].id' | rg '^ov-'
```

## OptiLLM via LiteLLM `boost` (Mini)
Confirm `boost` handle is present:
```bash
curl -fsS http://127.0.0.1:4000/v1/models \
  -H "Authorization: Bearer $LITELLM_API_KEY" \
  | jq -r '.data[].id' | rg '^boost$'
```

Then send a request through `boost` (Studio OptiLLM proxy path) and confirm a 200 response:
```bash
curl -fsS http://127.0.0.1:4000/v1/chat/completions \
  -H "Authorization: Bearer $LITELLM_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"boost","messages":[{"role":"user","content":"ping"}],"max_tokens":16}' \
  | jq .
```

Then send a request through `boost` (Studio OptiLLM proxy path):
```bash
curl -fsS http://127.0.0.1:4000/v1/chat/completions \
  -H "Authorization: Bearer $LITELLM_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"boost","messages":[{"role":"user","content":"ping"}],"max_tokens":16}' \
  | jq .
```

### PlanSearchTrio blind quality gate (`boost-plan` vs `boost-plan-trio`)
Use this flow when validating quality impact (not just latency/sentinel health):

1) Capture paired outputs:
```bash
cd /home/christopherbailey/homelab-llm/layer-gateway/optillm-proxy
./scripts/ab_capture_plansearch.py \
  --url http://127.0.0.1:4000/v1/chat/completions \
  --bearer "$LITELLM_API_KEY" \
  --model-a boost-plan \
  --model-b boost-plan-trio \
  --model-b-extra-json '{"plansearchtrio_mode":"auto","plansearchtrio_latency_budget_ms":17000,"plansearchtrio_reasoning_effort_synthesis":"high","plansearchtrio_reasoning_effort_rewrite":"high"}' \
  --max-tokens 220 \
  --prompts ./scripts/canary_prompts_plansearch.txt \
  --out-jsonl /tmp/plansearchtrio_ab_capture.jsonl \
  --summary-json /tmp/plansearchtrio_ab_capture_summary.json
```

2) Build a blinded human-scoring packet:
```bash
cd /home/christopherbailey/homelab-llm/layer-gateway/optillm-proxy
./scripts/ab_blind_packet.py \
  --capture-jsonl /tmp/plansearchtrio_ab_capture.jsonl \
  --out-csv /tmp/plansearchtrio_blind_score.csv \
  --out-key-json /tmp/plansearchtrio_blind_key.json \
  --seed 42
```

3) Score each row in `/tmp/plansearchtrio_blind_score.csv`:
- `winner` must be `A`, `B`, or `TIE`.

4) Compute model-level summary:
```bash
cd /home/christopherbailey/homelab-llm/layer-gateway/optillm-proxy
./scripts/ab_score_blind.py \
  --scored-csv /tmp/plansearchtrio_blind_score.csv \
  --key-json /tmp/plansearchtrio_blind_key.json \
  --baseline-model boost-plan \
  --candidate-model boost-plan-trio \
  --out-json /tmp/plansearchtrio_blind_score_summary.json
```

Suggested quality gate:
- `candidate_win_rate_decisive >= 0.55`

## OptiLLM proxy (Studio)
```bash
curl -fsS http://127.0.0.1:4020/v1/models -H "Authorization: Bearer dummy" | jq .
```
Note: missing the `Authorization` header returns `Invalid Authorization header`.

## Orin (mount + no inference listener)
```bash
ssh orin "findmnt /mnt/seagate -o TARGET,SOURCE,FSTYPE,OPTIONS"
ssh orin "ss -ltn | rg -n ':4040\\b' || echo 'ok: 4040 not listening'"
```

Verify OptiLLM directly (Mini): see “OptiLLM via LiteLLM `boost` (Mini)” above.

Verify direct MLX handles (when models are registered):
```bash
curl -fsS http://127.0.0.1:4000/v1/chat/completions \
  -H "Authorization: Bearer $LITELLM_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"mlx-<base-model>","messages":[{"role":"user","content":"ping"}],"max_tokens":128}' \
  | jq .
```

## OpenVINO (Mini)
```bash
curl -fsS http://127.0.0.1:9000/health | jq .
```

## OpenVINO device mode evaluation (Mini)
Test latency and throughput with the same 1500-char input:
```bash
# GPU only (current)
sudo sed -i 's/^OV_DEVICE=.*/OV_DEVICE=GPU/' /etc/homelab-llm/ov-server.env
sudo systemctl restart ov-server.service

# AUTO
sudo sed -i 's/^OV_DEVICE=.*/OV_DEVICE=AUTO/' /etc/homelab-llm/ov-server.env
sudo systemctl restart ov-server.service

# MULTI CPU+GPU
sudo sed -i 's/^OV_DEVICE=.*/OV_DEVICE=MULTI:GPU,CPU/' /etc/homelab-llm/ov-server.env
sudo systemctl restart ov-server.service
```

## Non-LLM pilot tests (Mini)
Run and capture timing + quality notes:
```bash
platform/ops/.venv-onnx/bin/python /home/christopherbailey/homelab-llm/platform/ops/scripts/onnx_eval.py
platform/ops/.venv-onnx/bin/python /home/christopherbailey/homelab-llm/platform/ops/scripts/clean_punct_onnx.py
```

## STT/TTS/Vision evaluation (planned)
Track candidate models, ports, and benchmarks in `docs/journal/`.

## AFM (Studio, planned)
Once the AFM OpenAI-compatible API is running:
```bash
curl -fsS http://192.168.1.72:9999/v1/models | jq .
```

## SearXNG (Mini, once installed)
```bash
curl -fsS "http://127.0.0.1:8888/search?q=ping&format=json" | jq .
```

## Open WebUI Web Search Phase A Baseline (Mini, end-user flow)
Goal: verify baseline search viability before adding rerankers/vector stores.

1) Generate a run-specific prompt pack:
```bash
cd /home/christopherbailey/homelab-llm
python3 scripts/openwebui_phase_a_baseline.py print-pack --run-id PHASEA-001
```

2) Programmatic run (recommended for speed/repeatability):
```bash
cd /home/christopherbailey/homelab-llm
export OWUI_API_KEY=<your_openwebui_api_key>
python3 scripts/openwebui_phase_a_baseline.py run-pack --run-id PHASEA-001 --model fast
```

3) End-user test in Open WebUI (manual alternative):
- Open the UI normally.
- Ensure web search is enabled for the chat.
- Send each printed prompt as a separate message (keep `[PHASEA-001:Qxx]` prefix intact).

4) Score from logs:
```bash
cd /home/christopherbailey/homelab-llm
python3 scripts/openwebui_phase_a_baseline.py score --run-id PHASEA-001 --since "45 minutes ago"
```

5) Fresh proof check (most recent activity only):
```bash
sudo journalctl -u open-webui.service --since "2 minutes ago" --no-pager \
  | rg -n 'OWUI_SEARXNG_RAW_JSON|source id=|web search|loader|fetch'
```

Pass guidance:
- `searx_rate_limit_or_429_errors == 0`
- `phase2_quality.poisoned_query_events == 0`
- `phase2_quality.grounding_warn_rate <= 0.10` (when present)
- `phase2_quality.citation_map_ready_rate >= 0.90` (when present)

If pass criteria fail, fix retrieval/extraction baseline first and re-run Phase A.

## Open WebUI Native Web Search (Mini)
Config authority checks:
```bash
systemctl show -p Environment open-webui.service --no-pager | rg -n \
  'ENABLE_PERSISTENT_CONFIG=False|ENABLE_WEB_SEARCH=True|WEB_SEARCH_ENGINE=searxng|SEARXNG_QUERY_URL=http://127.0.0.1:8888/search\\?q=<query>&format=json|WEB_SEARCH_RESULT_COUNT=6|WEB_SEARCH_CONCURRENT_REQUESTS=1|WEB_LOADER_ENGINE=safe_web|WEB_LOADER_TIMEOUT=15|WEB_LOADER_CONCURRENT_REQUESTS=2|WEB_FETCH_FILTER_LIST=|WEB_SEARCH_DOMAIN_FILTER_LIST='

systemctl show -p Environment open-webui.service --no-pager | rg -n \
  'EXTERNAL_WEB_LOADER_URL|SEARXNG_QUERY_URL=http://127.0.0.1:8899/search\\?q=<query>|WEB_LOADER_ENGINE=external'
```

SearXNG JSON smoke:
```bash
curl -fsS "http://127.0.0.1:8888/search?q=openwebui+searxng&format=json" \
  | jq '{count:(.results|length), first:(.results[0] // {}) | {title, url}}'
```

Open WebUI end-to-end smoke:
```bash
export OWUI_API_KEY='<open-webui-api-key>'
curl -N -fsS http://127.0.0.1:3000/api/chat/completions \
  -H "Authorization: Bearer ${OWUI_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model":"fast",
    "stream":true,
    "messages":[{"role":"user","content":"Search the web for two recent Open WebUI and SearXNG references and summarize them in two bullets."}],
    "features":{"web_search":true}
  }' | tee /tmp/owui-websearch-smoke.ndjson

rg -n '"type": "web_search"|"type":"web_search"|"sources": \\[' /tmp/owui-websearch-smoke.ndjson
rg -n '"content"|"delta"' /tmp/owui-websearch-smoke.ndjson | tail -n 40
```

Pass guidance:
- `ENABLE_PERSISTENT_CONFIG=False` is present so env/drop-ins are authoritative.
- `WEB_SEARCH_ENGINE=searxng` and `WEB_LOADER_ENGINE=safe_web` are present.
- Result count, concurrency, and filter-list controls are visible in the service environment.
- No `EXTERNAL_WEB_LOADER_URL`, `WEB_LOADER_ENGINE=external`, or `:8899/search` reference remains.
- The SearXNG smoke returns at least one result.
- The Open WebUI stream shows a `sources` event with `type: "web_search"` and returns assistant content.

## LiteLLM Web Search Reset Checks (Mini)
Readiness and model checks:
```bash
curl -fsS http://127.0.0.1:4000/health/readiness | jq .
curl -fsS http://127.0.0.1:4000/health/readiness | jq -r '.success_callbacks[]' | rg 'WebsearchSchemaGuardrail'

source /home/christopherbailey/homelab-llm/layer-gateway/litellm-orch/config/env.local
curl -fsS -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" \
  http://127.0.0.1:4000/v1/models | jq -r '.data[].id' | sort
```

Generic search-tool smoke:
```bash
source /home/christopherbailey/homelab-llm/layer-gateway/litellm-orch/config/env.local
curl -fsS -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" \
  -H "Content-Type: application/json" \
  http://127.0.0.1:4000/v1/search/searxng-search \
  -d '{"query":"openwebui searxng","max_results":2}' | jq .
```

Pass guidance:
- `WebsearchSchemaGuardrail` is absent from readiness callbacks.
- `/v1/models` does not include `fast-research`.
- `/v1/search/searxng-search` still works for direct callers and MCP tools.

## Legacy Path Removal Checks (Mini)
Service removal and active-surface grep:
```bash
systemctl is-active open-webui.service litellm-orch.service searxng.service
systemctl is-enabled websearch-orch.service
systemctl status websearch-orch.service --no-pager

rg -n --hidden --glob '!.git' --glob '!.venv/**' --glob '!docs/journal/**' --glob '!docs/archive/**' --glob '!docs/_core/consistency_audit_2026-03.md' \
  'websearch_schema_guardrail|<source id=|web_answer(\\.schema\\.json)?|EXTERNAL_WEB_LOADER_URL|SEARXNG_QUERY_URL=http://127.0.0.1:8899/search\\?q=<query>|WEB_LOADER_ENGINE=external|QUERY_GUARD_ENABLED|TRUST_POLICY_ENABLED|RERANK_ENABLED|CITATION_CONTRACT_ENABLED|fast-research' \
  /home/christopherbailey/homelab-llm
```

Pass guidance:
- `websearch-orch.service` is disabled or not found.
- Active repo surfaces do not depend on the removed custom middleware or legacy path markers.

## LiteLLM Search Proxy (Mini)
```bash
curl -fsS http://127.0.0.1:4000/v1/search/searxng-search \
  -H "Authorization: Bearer $LITELLM_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query":"openvino llm","max_results":3}' | jq .
```

## MCP web.fetch (Mini, stdio)
```bash
cd /home/christopherbailey/homelab-llm/layer-tools/mcp-tools/web-fetch
uv venv .venv
uv pip install -e .
.venv/bin/python3 scripts/demo_client.py --url https://example.com --print-clean-text
```

## MCP search.web (Mini, stdio)
```bash
cd /home/christopherbailey/homelab-llm/layer-tools/mcp-tools/web-fetch
.venv/bin/python3 scripts/demo_client.py --tool search.web --query "openvino llm" --max-results 3
```

## TinyAgents (Mini, once wired)
Run the agent with a known MCP tool and confirm tool output is reflected in the
response.

## MCP registry + TinyAgents env (MVP)
```bash
sudo cp /home/christopherbailey/homelab-llm/platform/ops/templates/mcp-registry.json /etc/homelab-llm/mcp-registry.json
sudo cp /home/christopherbailey/homelab-llm/platform/ops/templates/tiny-agents.env /etc/homelab-llm/tiny-agents.env
```

## OpenVINO model control (ovctl)
```bash
/home/christopherbailey/homelab-llm/platform/ops/scripts/ovctl list
/home/christopherbailey/homelab-llm/platform/ops/scripts/ovctl profiles
/home/christopherbailey/homelab-llm/platform/ops/scripts/ovctl warm-profile ov-only-expanded
/home/christopherbailey/homelab-llm/platform/ops/scripts/ovctl status
```

## ONNX evaluation (route + summarize)
```bash
platform/ops/.venv-onnx/bin/python /home/christopherbailey/homelab-llm/platform/ops/scripts/onnx_eval.py
```

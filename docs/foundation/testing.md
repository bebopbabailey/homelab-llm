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
```

Notes:
- `mlxctl ensure` takes a Hugging Face repo id (example: `mlx-community/Qwen3-4B-Instruct-2507-gabliterated-mxfp4`).
  Use `mlxctl list` to discover canonical `mlx-*` model ids.
- `mlxctl verify` checks registry defaults and also validates (on gateway hosts) that
  served MLX handles in `layer-gateway/registry/handles.jsonl` exist in the Studio registry.

Expanded runtime inspection:
```bash
mlxctl status --checks
mlxctl status --checks --json
```

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
mlxctl reconcile
```

## MLX lanes (Studio)
After reboot or launchd restart, confirm active `mlxctl` assignments are serving
`/v1/models` (current default active inference listener is `8100`).
Note: `GET /v1/models` on the Studio may return a local filesystem snapshot path
as the model `id`. Use `mlxctl status` for canonical model/port mapping.
```bash
curl -fsS http://127.0.0.1:8100/v1/models | jq .
# Optional (if assigned): 8101/8102/etc.
# curl -fsS http://127.0.0.1:8101/v1/models | jq .
# curl -fsS http://127.0.0.1:8102/v1/models | jq .
```

## Studio scheduling policy (Mini -> Studio)
Policy source of truth:
- `platform/ops/templates/studio_scheduling_policy.json`
- `docs/foundation/studio-scheduling-policy.md`

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
ssh studio "sudo -n plutil -convert json -o - /Library/LaunchDaemons/com.bebop.mlx-launch.plist | jq '{ProcessType, Nice, LowPriorityIO, LowPriorityBackgroundIO}'"
ssh studio "sudo -n plutil -convert json -o - /Library/LaunchDaemons/com.bebop.optillm-proxy.plist | jq '{ProcessType, Nice, LowPriorityIO, LowPriorityBackgroundIO}'"
# Fallback if JSON conversion is unavailable:
ssh studio "sudo -n /usr/libexec/PlistBuddy -c 'Print :ProcessType' /Library/LaunchDaemons/com.bebop.mlx-launch.plist"
ssh studio "sudo -n /usr/libexec/PlistBuddy -c 'Print :ProcessType' /Library/LaunchDaemons/com.bebop.optillm-proxy.plist"
```

Staged apply order:
1) `com.bebop.optillm-proxy` via:
   `uv run python platform/ops/scripts/enforce_studio_launchd_policy.py --host studio --apply --managed-label com.bebop.optillm-proxy --json`
2) validate
3) `com.bebop.mlx-launch` via:
   `uv run python platform/ops/scripts/enforce_studio_launchd_policy.py --host studio --apply --managed-label com.bebop.mlx-launch --json`
4) full strict audit

Runtime lineage check expectation:
- port `8100` listener is `vllm serve`
- process ancestry includes `com.bebop.mlx-launch` launcher lineage

Verify GPT‑OSS content channel is present (requires adequate max_tokens):
```bash
curl -fsS http://127.0.0.1:8100/v1/chat/completions \
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

2) End-user test in Open WebUI:
- Open the UI normally.
- Ensure web search is enabled for the chat.
- Send each printed prompt as a separate message (keep `[PHASEA-001:Qxx]` prefix intact).

3) Score from logs:
```bash
cd /home/christopherbailey/homelab-llm
python3 scripts/openwebui_phase_a_baseline.py score --run-id PHASEA-001 --since "45 minutes ago"
```

4) Fresh proof check (most recent activity only):
```bash
sudo journalctl -u open-webui.service --since "2 minutes ago" --no-pager \
  | rg -n 'OWUI_SEARXNG_RAW_JSON|source id=|web search|loader|fetch'
```

Pass guidance:
- `searx_rate_limit_or_429_errors == 0`
- `cases_seen_in_openwebui_logs == cases_total`
- `cases_with_source_blocks == cases_total`

If pass criteria fail, fix retrieval/extraction baseline first and re-run Phase A.

## websearch-orch hygiene proxy (Mini)
Service checks:
```bash
systemctl status websearch-orch.service --no-pager
curl -fsS "http://127.0.0.1:8899/health" | jq .
```

Search checks:
```bash
curl -fsS "http://127.0.0.1:8899/search?q=evidence-based+wok+tips&format=json" \
  | jq '{count:(.results|length), unresponsive_engines}'
```

Open WebUI wiring check:
```bash
systemctl show open-webui.service -p Environment --no-pager \
  | rg 'SEARXNG_QUERY_URL=http://127.0.0.1:8899/search\\?q=<query>'
```

Recent hygiene logs:
```bash
journalctl -u websearch-orch.service --since "10 minutes ago" --no-pager
```

Phase 2 calibration checks:
```bash
curl -fsS -X POST http://127.0.0.1:8899/web_loader \
  -H 'Content-Type: application/json' \
  -d '{"urls":["https://en.wikipedia.org/wiki/Wok","https://www.seriouseats.com/wok-skills-5117305","https://www.thekitchn.com/how-to-stir-fry-22916393"]}' \
  | jq '[.[].metadata | {source, char_count, raw_char_count, doc_char_truncated, budget_char_truncated}]'

journalctl -u websearch-orch.service --since "10 minutes ago" --no-pager \
  | rg -n 'web_loader urls=|raw_chars=|doc_caps=|budget_caps=|budget_drops='
```

Calibration pass guidance:
- `raw_chars` should be higher than `chars` when caps are active.
- `budget_drops` should typically remain `0` for normal 3-6 source queries.
- `budget_caps` may be `>0` on noisy pages; this is expected and indicates guardrails are active.
- If `budget_drops` stays high, first reduce `EXTERNAL_WEB_LOADER_MAX_URLS` or
  enable fair-share via `EXTERNAL_WEB_LOADER_MIN_PER_DOC_TEXT_CHARS` before
  raising total budget further.

Phase 2 tightening checks (query guard + trust policy):
```bash
curl -fsS "http://127.0.0.1:8899/search?q=Instrument+methods+used+in+NASA+Chang%E2%80%99e-6+to+detect+water&format=json" \
  | jq '{query_guard, trust_summary, citation_contract, quality_signals, first_result:(.results[0] // {}) | {url, orch_trust_tier, orch_source_id}}'

journalctl -u websearch-orch.service --since "10 minutes ago" --no-pager \
  | rg -n 'guarded_query=|query_action=|conflicts=|trust=|citation_map_status=|citation_mapped=|dedupe_drops=|domain_cap_drops='
```

Tightening pass guidance:
- `query_action` should be `sanitize` when entity conflicts are detected.
- `trust_summary.trust_drops` should remain small/non-zero only for weak domains.
- Result entries should include `orch_trust_tier` and `orch_source_id`.
- `citation_contract.citation_map_status` should be `ready` for grounded runs.
- `citation_contract.allowed_urls` should contain only non-placeholder HTTP(S) URLs.
- `quality_signals.dedupe_drops` and `quality_signals.domain_cap_drops` should be non-zero on noisy queries.

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

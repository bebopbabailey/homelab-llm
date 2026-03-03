# Runbook: websearch-orch

## Runtime dependency sync
```bash
uv venv /home/christopherbailey/homelab-llm/layer-tools/websearch-orch/.venv
uv pip install --python /home/christopherbailey/homelab-llm/layer-tools/websearch-orch/.venv/bin/python -r /home/christopherbailey/homelab-llm/layer-tools/websearch-orch/requirements.txt
```

## Start/stop
```bash
sudo systemctl start websearch-orch.service
sudo systemctl stop websearch-orch.service
sudo systemctl restart websearch-orch.service
```

## Logs
```bash
journalctl -u websearch-orch.service -f
```

## Health
```bash
curl -fsS http://127.0.0.1:8899/health | jq .
```

## Search smoke test
```bash
curl -fsS "http://127.0.0.1:8899/search?q=evidence-based+wok+tips&format=json" | jq '.results | length'
```

## External web-loader smoke test (Phase 1)
```bash
curl -fsS -X POST http://127.0.0.1:8899/web_loader \
  -H 'Content-Type: application/json' \
  -d '{"urls":["https://en.wikipedia.org/wiki/Wok"]}' \
  | jq '.[0].metadata'
```

## Reranker verification
```bash
journalctl -u websearch-orch.service --since "10 min ago" --no-pager | rg -n "rerank enabled|rerank=True|rerank=False|rerank failed|top_scores="
```

## Phase 2 calibration verification
```bash
journalctl -u websearch-orch.service --since "10 min ago" --no-pager \
  | rg -n "web_loader urls=|raw_chars=|doc_caps=|budget_caps=|budget_drops="
```

## Phase 2 quality tightening verification
```bash
journalctl -u websearch-orch.service --since "10 min ago" --no-pager \
  | rg -n "guarded_query=|query_action=|conflicts=|trust=|citation_map_status=|citation_mapped=|grounding_status=|grounding_allowed_urls=|dedupe_drops=|domain_cap_drops="
```

Recommended initial env values in `/etc/homelab-llm/websearch-orch.env`:
- `EXTERNAL_WEB_LOADER_MAX_TEXT_CHARS=2800`
- `EXTERNAL_WEB_LOADER_MAX_TOTAL_TEXT_CHARS=18000`
- `EXTERNAL_WEB_LOADER_MAX_URLS=10`
- `EXTERNAL_WEB_LOADER_MIN_PER_DOC_TEXT_CHARS=700`
- `QUERY_GUARD_ENABLED=true`
- `QUERY_ENTITY_CONFLICT_ACTION=sanitize`
- `TRUST_POLICY_ENABLED=true`
- `TRUST_DROP_BELOW_SCORE=0`
- `MIN_RESULT_CONTENT_CHARS=160`
- `MAX_SOURCES_PER_DOMAIN=2`
- `CITATION_CONTRACT_ENABLED=true`
- `MIN_GROUNDED_SOURCES=2`
- `SOURCE_TITLE_DEDUP_ENABLED=true`
- `RERANK_ENABLED=true`

## DSPy citation-fidelity pilot (offline, learning-first)
This does not change live `websearch-orch` request handling.

Optional dependency install:
```bash
uv pip install --python /home/christopherbailey/homelab-llm/layer-tools/websearch-orch/.venv/bin/python \
  -r /home/christopherbailey/homelab-llm/layer-tools/websearch-orch/requirements-dspy-pilot.txt
```

Contract + dataset checks:
```bash
cd /home/christopherbailey/homelab-llm
uv run python scripts/dspy_citation_fidelity.py print-contract
uv run python scripts/dspy_citation_fidelity.py validate-dataset \
  --dataset layer-tools/websearch-orch/dspy_pilot/data/citation_fidelity.sample.jsonl
```

Metric smoke with deterministic backend:
```bash
uv run python scripts/dspy_citation_fidelity.py eval \
  --backend mock \
  --dataset layer-tools/websearch-orch/dspy_pilot/data/citation_fidelity.sample.jsonl \
  --report-out /tmp/dspy_citation_mock_report.json
```

Real DSPy eval against local OpenAI-compatible gateway:
```bash
export LITELLM_MASTER_KEY='<your-key>'
uv run python scripts/dspy_citation_fidelity.py eval \
  --backend dspy \
  --dataset layer-tools/websearch-orch/dspy_pilot/data/citation_fidelity.sample.jsonl \
  --model openai/fast \
  --api-base http://127.0.0.1:4000/v1 \
  --api-key-env LITELLM_MASTER_KEY \
  --report-out /tmp/dspy_citation_dspy_report.json
```

Compile + compare:
```bash
export LITELLM_MASTER_KEY='<your-key>'
uv run python scripts/dspy_citation_fidelity.py compile \
  --backend dspy \
  --train-dataset layer-tools/websearch-orch/dspy_pilot/data/citation_fidelity.sample.jsonl \
  --dev-dataset layer-tools/websearch-orch/dspy_pilot/data/citation_fidelity.sample.jsonl \
  --model openai/fast \
  --api-base http://127.0.0.1:4000/v1 \
  --api-key-env LITELLM_MASTER_KEY \
  --optimizer bootstrap \
  --num-trials 8 \
  --artifact-dir /tmp/dspy-citation-artifacts
```

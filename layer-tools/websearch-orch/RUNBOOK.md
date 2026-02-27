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

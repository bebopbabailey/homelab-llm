# 11-TEST_PLAN_SMOKES

Copy/paste commands to validate the platform. Adjust hostnames if running from a remote machine.
If you have DNS/hosts for `mini`, replace `127.0.0.1` with `mini` or `192.168.1.71`.

## LiteLLM gateway health
```bash
curl -fsS http://127.0.0.1:4000/health | jq .
```
Expected: JSON with `healthy_count` and `unhealthy_count` fields.
Failure hints: LiteLLM service down, env vars missing, or upstream unavailable.

## LiteLLM model list
```bash
curl -fsS http://127.0.0.1:4000/v1/models | jq -e '.data | length > 0'
```
Expected: list of `jerry-*` and `lil-jerry` model names.
Failure hints: LiteLLM config/env not loaded or service not running.

## LiteLLM chat completion (via MLX)
```bash
curl -fsS http://127.0.0.1:4000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"jerry-weak","messages":[{"role":"user","content":"ping"}],"max_tokens":16}' \
  | jq -e '.choices | length > 0'
```
Expected: non-empty `choices` array.
Failure hints: MLX backend down or LiteLLM routing misconfigured.

## Open WebUI connectivity
```bash
curl -fsS http://127.0.0.1:3000/ | head -n 1
```
Expected: HTML response (not empty).
Failure hints: Open WebUI service down or bound to a different port.

## Open WebUI health
```bash
curl -fsS http://127.0.0.1:3000/health | jq .
```
Expected: JSON response (observed `{"status":true}` via curl).
Failure hints: Open WebUI service down or health endpoint disabled.

## OpenVINO backend (direct)
```bash
curl -fsS http://127.0.0.1:9000/health | jq .
```
Expected: JSON with `status` and `device` fields.
Failure hints: OpenVINO service down or model registry path invalid.

## OpenVINO backend (via LiteLLM)
```bash
curl -fsS http://127.0.0.1:4000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"lil-jerry","messages":[{"role":"user","content":"ping"}],"max_tokens":16}' \
  | jq -e '.choices | length > 0'
```
Expected: non-empty `choices` array.
Failure hints: OpenVINO backend down or LiteLLM routing misconfigured.

## Studio MLX backend reachability (direct)
Use the base URLs from `config/env.local` (host confirmed as 192.168.1.72 by owner):
```bash
curl -fsS http://192.168.1.72:8100/v1/models | jq .
curl -fsS http://192.168.1.72:8101/v1/models | jq .
curl -fsS http://192.168.1.72:8102/v1/models | jq .
curl -fsS http://192.168.1.72:8103/v1/models | jq .
curl -fsS http://192.168.1.72:8109/v1/models | jq .
```
Expected: JSON model lists from each MLX server.
Failure hints: Studio servers not running, firewall blocks, or host IP differs.

# OptiLLM Proxy — Service Specification

## Service name
`optillm-proxy`

---

## Purpose

Runs OptiLLM as a **localhost-only OpenAI-compatible inference proxy** that applies inference-time optimization strategies before forwarding requests upstream to LiteLLM or MLX endpoints.

End-user clients must never access this service directly.

---

## Network & exposure

| Property | Value |
|--------|------|
| Bind address | 127.0.0.1 |
| Port | 4020 |
| External access | Forbidden |
| TLS | Not required (localhost only) |

---

## API surface

OpenAI-compatible endpoints under `/v1`.

Minimum required:
- `POST /v1/chat/completions`
- `GET /v1/models`

---

## Upstream dependency

| Item | Value |
|----|------|
| Upstream type | OpenAI-compatible API |
| Upstream service | LiteLLM or MLX |
| Upstream base URL | http://127.0.0.1:<LITELLM_PORT>/v1 or http://<studio>:<mlx-port>/v1 |

---

## Authentication

### OptiLLM proxy auth
-- Controlled via `--optillm-api-key` (do not set `OPTILLM_API_KEY` env)
- LiteLLM must include:
```
Authorization: Bearer <OPTILLM_API_KEY>
```
Missing this header returns `Invalid Authorization header` (even on localhost).

### Upstream auth
- Provided via `OPENAI_API_KEY` (or equivalent LiteLLM config)
- Used only for OptiLLM → upstream calls

Important: setting `OPTILLM_API_KEY` in the environment triggers OptiLLM's
local inference mode. Use the flag instead.

---

## Model & strategy handling

- Base models must be valid LiteLLM model names
- Strategy selection uses request-body fields (primary) or prompt tags (secondary).
- Supported request-body field: `optillm_approach`.
- Optional request-body field: `optillm_base_model` (overrides the upstream model used by OptiLLM).
- Usage reporting: `prompt_tokens` is estimated using `tiktoken` (cl100k_base) when available; falls back to a rough char-based estimate.

---

## Wiring note
- OptiLLM is not wired into LiteLLM by default.
- Clients that want OptiLLM should call `http://127.0.0.1:4020/v1` directly and
  include `optillm_approach` in the request body.
- Deprecated: routing all MLX handles through OptiLLM via `router-mlx-*` entries.

---

## Planned registry
- Service-level JSONL registry for OptiLLM ensembles (planned):
  `layer-gateway/optillm-proxy/registry/ensembles.jsonl`
- Source of truth for selectors, model membership, and purpose tags.

---

## Runtime configuration (minimum)

Expected external configuration (env file, not committed):

- `OPENAI_API_KEY` (used by OptiLLM when calling LiteLLM)
Example env file path (systemd): `/etc/optillm-proxy/env`.

Runtime flags (systemd `ExecStart` should pass explicitly):
- `--host 127.0.0.1`
- `--port 4020`
- `--base-url <upstream OpenAI-compatible endpoint>`
- `--approach none`
- `--model <base_model>` (example: `qwen3-235b-a22b-instruct-2507-6bit`)
- `--plugins-dir <path>` (local plugin overrides)
- `--optillm-api-key <key>` (proxy auth)

Exact variable names depend on pinned OptiLLM version.

### router_meta configuration
`router_meta` routes between opti-proxy and opti-local based on env policy:
- `ROUTER_META_LOCAL_ONLY` (comma-separated approaches, default: bon,moa,mcts,pvg,cot_decoding,entropy_decoding,deepconf,thinkdeeper,autothink)
- `ROUTER_META_PROXY_ONLY` (comma-separated, optional)
- `ROUTER_META_DEFAULT_DESTINATION` (proxy|local, default: proxy)
- `ROUTER_META_FALLBACK` (none|re2|cot_reflection|error, default: none)

Loop protection:
- Incoming `X-Opti-Hop` or `X-Opti-From` headers disable re-routing.
- `ROUTER_META_LOCAL_URL` (default `http://127.0.0.1:4040/v1`)
- `ROUTER_META_PROXY_URL` (default `http://127.0.0.1:4020/v1`)
- `ROUTER_META_LOCAL_MODEL` (required for local-only routes)
- `ROUTER_META_LOCAL_AUTH` / `ROUTER_META_PROXY_AUTH` (optional auth overrides)

---

## Process model

| Property | Requirement |
|-------|-------------|
| Execution | Long-running service |
| Restart | Automatic on failure |
| Logging | STDOUT / journald |
| Privileges | Non-root |

### Approach logging
- OptiLLM logs the selected approaches at INFO level:
  - `Using approach(es) [...]`
  - See `RUNBOOK.md` for a grep example.

---

## Health checks

Preferred:
```
GET /health
```

Fallback:
```
GET /v1/models
```

HTTP 200 + valid JSON indicates healthy.

---

## Performance characteristics

- Increased latency (multiple upstream calls)
- Increased token usage
- Intended for deep reasoning and planning
- Not for low-latency chat
- Router model cache (proxy user): `~/.cache/huggingface/hub`
- `web_search` uses **SearXNG** when `SEARXNG_API_BASE` is set in `/etc/optillm-proxy/env`.
  Local override: `layer-gateway/optillm-proxy/optillm/plugins/web_search_plugin.py`.
  If unset, the plugin falls back to its built-in Selenium/Google path.

## Technique selection (request-body field)
OptiLLM chooses strategies based on `optillm_approach`:
- `moa`: Mixture-of-Agents (strong reasoning, higher latency)
- `bon`: best-of-n sampling (faster than MoA, moderate gains)
- `plansearch`: planning/search (slower, good for multi-step tasks)
- `self_consistency`: consistency voting (slower, robust)
- `web_search`: inject SearXNG results into the prompt before answering

Example:
```json
{"model":"mlx-gpt-oss-120b-mxfp4-q4","messages":[{"role":"user","content":"ping"}],"optillm_approach":"bon"}
```

---

## Versioning

OptiLLM must be pinned to an explicit version/tag/commit.
Upgrades must be deliberate and validated.

## Install (uv-only)

No Docker installs are allowed in this repo.

```bash
cd /home/christopherbailey/homelab-llm/layer-gateway/optillm-proxy
uv venv .venv
uv sync
```

Pinned release:
- `optillm==0.3.12`
- Pin lives in `pyproject.toml`

## Proxy provider config
OptiLLM proxy plugin loads providers from:
`/home/christopherbailey/.optillm/proxy_config.yaml`.

This should point to the configured upstream (LiteLLM or MLX), e.g.:
```yaml
providers:
  - name: litellm
    base_url: http://127.0.0.1:4000/v1
    api_key: dummy
```

---

## Out of scope

- Model training or fine-tuning
- Direct client access
- MCP integration
- Automatic model discovery

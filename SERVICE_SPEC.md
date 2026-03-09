# OptiLLM Proxy — Service Specification

## Service name
`optillm-proxy`

---

## Purpose

Runs OptiLLM as an OpenAI-compatible inference proxy that applies proxy-safe
optimization strategies before forwarding requests upstream to an OpenAI-compatible
backend (currently Mini LiteLLM via tailnet TCP forward).

End-user clients must never access this service directly.

---

## Network & exposure

| Property | Value |
|--------|------|
| Host | Mac Studio (launchd) |
| Bind address | 0.0.0.0 |
| Port | 4020 |
| External access | LAN-exposed (auth required); intended caller is LiteLLM `boost` |
| TLS | Not required (LAN; protected by bearer auth) |

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
| Upstream service | LiteLLM on Mini (localhost-bound, reached via tailnet TCP forward) |
| Upstream base URL | http://100.69.99.60:4443/v1 |

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
- Usage reporting: `prompt_tokens` is estimated using `tiktoken` (cl100k_base) when available; falls back to a rough char-based estimate.
- `boost-plan` follows upstream stock `optillm==0.3.12` `plansearch` behavior.
- `boost-plan-trio` is provided by the local `plansearchtrio` plugin and is the preferred deliberate planning lane.
- `boost-plan` remains the upstream baseline and fallback comparator.
- Trio is intentionally not the universal low-latency default.

---

## Wiring note
- Clients should stay LiteLLM-only. This service is used via the LiteLLM `boost` handle.
- Requests must include `optillm_approach` in the request body to select a technique.
- Deprecated: routing all MLX handles through OptiLLM via `router-mlx-*` entries.
- For OpenCode deterministic profiles, LiteLLM can select approach via model prefix
  (`<approach>-openai/<alias>`), avoiding request-body coupling.

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
- `--host 0.0.0.0`
- `--port 4020`
- `--base-url <upstream OpenAI-compatible endpoint>`
- `--approach none`
- `--model <base_model>` (example: `qwen3-235b-a22b-instruct-2507-6bit`)
- `--plugins-dir <path>` (local plugin overrides)
- `--optillm-api-key <key>` (proxy auth)

Deployment contract:
- Install path is `uv sync --frozen` from this repo checkout.
- Studio deploy is exact-SHA only.
- Deploy-time patching is not part of the runtime contract.

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

Studio launchd identity:
- Label: `com.bebop.optillm-proxy`
- Domain: `system`
- Plist path: `/Library/LaunchDaemons/com.bebop.optillm-proxy.plist`
- Working directory must be `/Users/thestudio/optillm-proxy` so local plugins
  resolve from `optillm/plugins`.
- Do not force `--approach` at launch for deterministic prefixed aliases; allow
  request/model-prefix approach selection.

Scheduling classification (Studio policy):
- Lane: `inference`
- Required plist key: `ProcessType = Interactive`
- Must not set background throttles (`LowPriorityIO`,
  `LowPriorityBackgroundIO`) or positive `Nice`.
- Canonical policy reference: `docs/foundation/studio-scheduling-policy.md`

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

Deterministic alias mapping (LiteLLM -> OptiLLM model prefix):
- `boost-plan` -> `plansearch-deep`
- `boost-plan-trio` -> `plansearchtrio-deep` (canary)
- `boost-plan-verify` -> `self_consistency-deep`
- `boost-ideate` -> `moa-deep`
- `boost-fastdraft` -> `bon-fast`

Planner policy:
- `boost-plan-trio` is preferred for deliberate planning and coding workflows
  where completeness matters more than raw latency.
- `boost-plan` remains the stock upstream baseline and fallback.
- Trio is intentionally higher-latency and richer-output than baseline and
  should not be treated as the universal low-latency default.
- Trio deep synthesis/rewrite stages can use stage-scoped reasoning effort:
  - `plansearchtrio_reasoning_effort_synthesis` (default `high`)
  - `plansearchtrio_reasoning_effort_rewrite` (default `high`)
  - Allowed values: `low|medium|high` (or `off|none` to disable)
  - Applied only when the call is on the configured `deep` model; earlier stages remain unchanged.
  - If a backend rejects `reasoning_effort`, trio retries that stage once without it.

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


## Studio deployment (source of truth = Mini)
- Development and commits happen on the Mini repo.
- Studio deploy is exact-SHA into `/Users/thestudio/optillm-proxy` plus launchd restart.
- Use `scripts/deploy_studio.sh` from the Mini to deploy + smoke test.

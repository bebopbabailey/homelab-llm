# OptiLLM Proxy — Overview & Usage

## What this service is

**OptiLLM** is an **OpenAI API-compatible optimizing inference proxy**. It sits in front of an OpenAI-compatible upstream (in this homelab, upstream is **LiteLLM or MLX**) and applies **inference-time strategies** (e.g., Mixture-of-Agents, planning/search, best-of-n) to improve reasoning and coding outputs.

This service behaves like “just another OpenAI-compatible provider” from LiteLLM’s point of view.

---

## Placement in the homelab

**LAN-first gateway upstream. No direct end-user client access.**

Client(s) → LiteLLM (gateway) → OptiLLM (Studio LAN) → LiteLLM (Mini LAN) → Real backends

OptiLLM binds to the Studio LAN IP `192.168.1.72` so LiteLLM can reach it
directly without a tailnet bridge.

---

## API compatibility

OptiLLM exposes standard OpenAI-style endpoints under `/v1`.

Required endpoints:
- `POST /v1/chat/completions`
- `GET /v1/models` (used for health/verification if `/health` is unavailable)

Any OpenAI-compatible client (including LiteLLM) can talk to OptiLLM by pointing `base_url` at its `/v1` endpoint.

---

## How optimization strategies are selected

OptiLLM supports multiple mechanisms. For this repo, **request-body selection is the primary method** (no alias explosion).

### Request-body selection (primary)

Include an `optillm_approach` field in the request body when calling OptiLLM
directly. This is the preferred, most ergonomic method and works from Open WebUI
custom params, curl, iOS Shortcuts, and any OpenAI-compatible client.

Example (raw HTTP):
```json
{
  "model": "mlx-gpt-oss-120b-mxfp4-q4",
  "messages": [{"role": "user", "content": "Write a plan."}],
  "optillm_approach": "bon"
}
```

### router_meta (proxy-to-local split)

`router_meta` is a custom plugin that predicts an approach with ModernBERT and
then routes either to:
- **optillm-proxy** (proxy-safe approaches), or
Local-only approaches: `bon`, `moa`, `mcts`, `pvg`, `cot_decoding`,
`entropy_decoding`, `deepconf`, `thinkdeeper`, `autothink`.

It forwards the full request payload and adds `optillm_meta` to the response.
Set it by request body:
```json
{"model":"mlx-gpt-oss-120b-mxfp4-q4","messages":[{"role":"user","content":"ping"}],"optillm_approach":"router_meta"}
```

Environment knobs (proxy instance):
- `ROUTER_META_LOCAL_URL` (default `http://127.0.0.1:4040/v1`)
- `ROUTER_META_PROXY_URL` (default `http://127.0.0.1:4020/v1`)
- `ROUTER_META_LOCAL_MODEL` (required for local-only routes)
- `ROUTER_META_LOCAL_AUTH` / `ROUTER_META_PROXY_AUTH` (optional auth overrides)

### Prompt tag selection (secondary)

OptiLLM also supports prompt tags in the message content. Use this only when a client
cannot add extra JSON fields.
Example tag:
```
<optillm_approach>bon</optillm_approach>
```

### Model-name prefixing (supported, not used)

OptiLLM can parse approach prefixes in model names, but this repo avoids it to keep
handles stable and prevent alias sprawl.

---

## Authentication model

There are **two separate authentication concerns**.

### 1) OptiLLM proxy authentication
- The current Studio deployment does not require backend bearer auth.
- Protect access with the dedicated Studio LAN bind and the LiteLLM-only caller contract.

### 2) Upstream authentication
- Used when OptiLLM calls the upstream (LiteLLM or MLX)
- Usually provided via `OPENAI_API_KEY` (or equivalent LiteLLM config)
- This is unrelated to any proxy-side listener auth.

## Proxy provider config (required)
OptiLLM's proxy plugin reads its provider list from:
```
~/.optillm/proxy_config.yaml
```

For this homelab, it should point to the configured upstream (LiteLLM or MLX):
```yaml
providers:
  - name: litellm
    base_url: http://192.168.1.71:4000/v1
    api_key: dummy
```

---

## Install and run (uv-only)

This repo does not allow Docker installs. Use `uv` and run OptiLLM as the
Studio launchd service described in the service docs.

```bash
cd /home/christopherbailey/homelab-llm/layer-gateway/optillm-proxy
uv venv .venv
uv sync
```

Run manually (for quick verification):

```bash
OPENAI_API_KEY="<litellm-proxy-or-upstream-key>" \
uv run optillm \
  --host 192.168.1.72 \
  --port 4020 \
  --base-url http://192.168.1.71:4000/v1 \
  --approach none \
  --model <base-model>
```

Notes:
- `OPENAI_API_KEY` is used by OptiLLM when calling the upstream (LiteLLM or MLX).
- `--base-url` points at LiteLLM or directly at an MLX OpenAI-compatible endpoint.
- OptiLLM local (Studio) uses `/Users/thestudio/models/hf/hub` and pins
  `transformers<5` for router compatibility.

## Locked runtime (durability)

OptiLLM is pinned from PyPI and deployed to Studio by exact git SHA from this
repo. See `RUNBOOK.md` and `platform/ops/runtime-lock.json` for the locked
contract.

## Router model (internal)
- The `router` plugin uses an internal classifier model (not exposed via LiteLLM).
- Cached under `~/.cache/huggingface/hub` for the OptiLLM service user:
  - `codelion/optillm-modernbert-large` (router head)
  - `answerdotai/ModernBERT-large` (base encoder)

## Deprecated wiring
- Routing all MLX handles through OptiLLM via `router-mlx-*` entries in LiteLLM
  is deprecated. Current practice is direct MLX routing in LiteLLM and explicit
  OptiLLM calls only when needed.

## Technique selection (request-body field)
OptiLLM chooses strategies based on `optillm_approach`:
- `moa`: Mixture-of-Agents (strong reasoning, higher latency)
- `bon`: best-of-n sampling (faster than MoA, moderate gains)
- `plansearch`: planning/search (slower, good for multi-step tasks)
- `plansearchtrio`: canary staged fast/main/deep planner plugin (parallel candidate generation)
- `self_consistency`: consistency voting (slower, robust)
- `web_search`: run SearXNG search first (requires `SEARXNG_API_BASE`)

Example:
```json
{"model":"mlx-gpt-oss-120b-mxfp4-q4","messages":[{"role":"user","content":"ping"}],"optillm_approach":"moa"}
```

## router_meta routing policy
`router_meta` keeps the routing policy in env vars so it can change without code edits:
- `ROUTER_META_LOCAL_ONLY` (comma-separated approaches, default: bon,moa,mcts,pvg)
- `ROUTER_META_PROXY_ONLY` (comma-separated, optional)
- `ROUTER_META_DEFAULT_DESTINATION` (proxy|local, default: proxy)
- `ROUTER_META_FALLBACK` (none|re2|cot_reflection|error, default: none)

Loop protection:
- Incoming `X-Opti-Hop` or `X-Opti-From` headers disable re-routing.

## Ensemble Matrix (v0)
See `ENSEMBLES.md` for the initial OptiLLM ensemble matrix used for evaluation.

## Planned registry (service-level)
This service will own a JSONL registry for OptiLLM ensembles (planned):
- `layer-gateway/optillm-proxy/registry/ensembles.jsonl`
- Source of truth for OptiLLM selectors and ensemble membership.

---

## Verification checklist

- OptiLLM responds to `/v1/chat/completions` on localhost
- Requests without `Authorization` fail (if auth enabled)
- Requests via LiteLLM alias reach OptiLLM
- OptiLLM makes multiple upstream calls to LiteLLM
- No routing loops occur


## Dev → Deploy (Mini → Studio)
- **Source of truth**: Mini repo (`layer-gateway/optillm-proxy`).
- **Deploy target**: Studio clone at `/Users/thestudio/optillm-proxy`.
- **Deploy helper**: `scripts/deploy_studio.sh` (pulls, uv sync, launchd restart, smoke test; optional bench).

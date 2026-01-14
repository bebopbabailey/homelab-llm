# OptiLLM Proxy — Overview & Usage

## What this service is

**OptiLLM** is an **OpenAI API-compatible optimizing inference proxy**. It sits in front of an OpenAI-compatible upstream (in this homelab, upstream is **LiteLLM**) and applies **inference-time strategies** (e.g., Mixture-of-Agents, planning/search, best-of-n) to improve reasoning and coding outputs.

This service behaves like “just another OpenAI-compatible provider” from LiteLLM’s point of view.

---

## Placement in the homelab

**Local-only proxy. No direct client access.**

Client(s) → LiteLLM (gateway) → OptiLLM (localhost-only) → LiteLLM (upstream) → Real backends

OptiLLM must bind to `127.0.0.1` only. External binding is intentionally out of scope.

---

## API compatibility

OptiLLM exposes standard OpenAI-style endpoints under `/v1`.

Required endpoints:
- `POST /v1/chat/completions`
- `GET /v1/models` (used for health/verification if `/health` is unavailable)

Any OpenAI-compatible client (including LiteLLM) can talk to OptiLLM by pointing `base_url` at its `/v1` endpoint.

---

## How optimization strategies are selected

OptiLLM supports multiple mechanisms. For this repo, **model-name prefixing is the primary method**.

### Model-name prefix convention

Format:
```
<approach>-<base_model>
```

Example:
```
moa-jerry-chat
```

Meaning:
- `moa` → Mixture-of-Agents strategy
- `jerry-chat` → base model used upstream

OptiLLM strips the prefix internally before calling upstream.

Clients should never see or select these prefixed names directly.

---

## Authentication model

There are **two separate authentication concerns**.

### 1) OptiLLM proxy authentication
- Protects access *to OptiLLM itself*
- **Use `--optillm-api-key`** (recommended)
- Requests must include:
```
Authorization: Bearer <OPTILLM_API_KEY>
```

### 2) Upstream authentication
- Used when OptiLLM calls LiteLLM
- Usually provided via `OPENAI_API_KEY` (or equivalent LiteLLM config)
- This is unrelated to `OPTILLM_API_KEY`

Important: setting `OPTILLM_API_KEY` in the environment triggers OptiLLM's
**local inference mode**. Do not set it when using a remote upstream (LiteLLM).
Use the `--optillm-api-key` flag instead.

## Proxy provider config (required)
OptiLLM's proxy plugin reads its provider list from:
```
~/.optillm/proxy_config.yaml
```

For this homelab, it must point **only** to LiteLLM:
```yaml
providers:
  - name: litellm
    base_url: http://127.0.0.1:4000/v1
    api_key: dummy
```

---

## Install and run (uv-only)

This repo does not allow Docker installs. Use `uv` to install a pinned OptiLLM
version and run it as a local service.

```bash
cd /home/christopherbailey/homelab-llm/layer-gateway/optillm-proxy
uv venv .venv
uv pip install optillm==0.3.12
```

Run manually (for quick verification):

```bash
OPENAI_API_KEY="<litellm-proxy-or-upstream-key>" \
uv run optillm \
  --host 127.0.0.1 \
  --port 4020 \
  --base-url http://127.0.0.1:4000/v1 \
  --approach proxy \
  --model jerry-xl \
  --optillm-api-key "<optillm-proxy-key>"
```

Notes:
- `OPENAI_API_KEY` is used by OptiLLM when calling the LiteLLM upstream.
- `--optillm-api-key` protects the OptiLLM proxy itself.
- `--base-url` must point at the LiteLLM gateway.

## Loop-avoidance rule (critical)

Because OptiLLM calls back into LiteLLM, routing must avoid infinite loops.

Required invariant:
- LiteLLM → OptiLLM: **prefixed model name** (e.g., `moa-jerry-chat`)
- OptiLLM → LiteLLM (upstream): **base model only** (e.g., `jerry-chat`)

LiteLLM must never route the base model back to OptiLLM.

---

## Recommended initial use case: development planning assistant

Expose **one clean alias** to clients:
```
optillm-jerry-xl
```

Behind the scenes:
- LiteLLM maps `optillm-jerry-xl` → OptiLLM
- LiteLLM sends `model = openai/moa-jerry-xl` (or other OptiLLM prefixed model)
- OptiLLM applies the chosen strategy and calls upstream with `jerry-xl`

This yields higher-quality plans with minimal system complexity.

## Technique selection (model prefixes)
OptiLLM chooses strategies based on the model prefix:
- `moa-<base>`: Mixture-of-Agents (strong reasoning, higher latency)
- `bon-<base>`: best-of-n sampling (faster than MoA, moderate gains)
- `plansearch-<base>`: planning/search (slower, good for multi-step tasks)
- `self_consistency-<base>`: consistency voting (slower, robust)

Example:
```
OPTILLM_JERRY_XL_MODEL=openai/bon-jerry-xl
```

---

## Verification checklist

- OptiLLM responds to `/v1/chat/completions` on localhost
- Requests without `Authorization` fail (if auth enabled)
- Requests via LiteLLM alias reach OptiLLM
- OptiLLM makes multiple upstream calls to LiteLLM
- No routing loops occur

# OptiLLM Proxy — Service Specification

## Service name
`optillm-proxy`

---

## Purpose

Runs OptiLLM as a **localhost-only OpenAI-compatible inference proxy** that applies inference-time optimization strategies before forwarding requests upstream to LiteLLM.

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
| Upstream service | LiteLLM |
| Upstream base URL | http://127.0.0.1:<LITELLM_PORT>/v1 |

---

## Authentication

### OptiLLM proxy auth
-- Controlled via `--optillm-api-key` (do not set `OPTILLM_API_KEY` env)
- LiteLLM must include:
```
Authorization: Bearer <OPTILLM_API_KEY>
```

### Upstream auth
- Provided via `OPENAI_API_KEY` (or equivalent LiteLLM config)
- Used only for OptiLLM → LiteLLM calls

Important: setting `OPTILLM_API_KEY` in the environment triggers OptiLLM's
local inference mode. Use the flag instead.

---

## Model & strategy handling

- Base models must be valid LiteLLM model names
- Strategy selection uses model-name prefixes:
```
<approach>-<base_model>
```

Example:
```
moa-jerry-xl
```

OptiLLM strips the prefix before upstream calls.

---

## Loop-avoidance invariant

- LiteLLM → OptiLLM: prefixed model name
- OptiLLM → LiteLLM: base model name only

Breaking this rule can cause infinite routing loops.

---

## Runtime configuration (minimum)

Expected external configuration (env file, not committed):

- `OPENAI_API_KEY` (used by OptiLLM when calling LiteLLM)
Example env file path (systemd): `/etc/optillm-proxy/env`.

Runtime flags (systemd `ExecStart` should pass explicitly):
- `--host 127.0.0.1`
- `--port 4020`
- `--base-url http://127.0.0.1:4000/v1`
- `--approach proxy`
- `--model <base_model>` (example: `jerry-xl`)
- `--optillm-api-key <key>` (proxy auth)

Exact variable names depend on pinned OptiLLM version.

---

## Process model

| Property | Requirement |
|-------|-------------|
| Execution | Long-running service |
| Restart | Automatic on failure |
| Logging | STDOUT / journald |
| Privileges | Non-root |

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

## Versioning

OptiLLM must be pinned to an explicit version/tag/commit.
Upgrades must be deliberate and validated.

## Install (uv-only)

No Docker installs are allowed in this repo.

```bash
cd /home/christopherbailey/homelab-llm/layer-gateway/optillm-proxy
uv venv .venv
uv pip install optillm==0.3.12
```

## Proxy provider config
OptiLLM proxy plugin loads providers from:
`/home/christopherbailey/.optillm/proxy_config.yaml`.

This must point to LiteLLM only:
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

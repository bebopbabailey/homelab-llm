# OptiLLM Local — Service Specification

## Service name
`optillm-local`

---

## Purpose
CUDA-backed **local inference** for OptiLLM on the Orin AGX. This is a standard
OpenAI-compatible backend reachable via LiteLLM.

---

## Network & exposure

| Property | Value |
|--------|------|
| Host | Orin AGX |
| Bind | 0.0.0.0 |
| Port | 4040 |
| External access | LAN only (no public exposure) |
| TLS | Not required (LAN) |

---

## API surface
OpenAI-compatible endpoints under `/v1`.

Required:
- `POST /v1/chat/completions`
- `GET /v1/models`

---

## Authentication
- OptiLLM local **requires** `OPTILLM_API_KEY`.
- All clients must send:
```
Authorization: Bearer <OPTILLM_API_KEY>
```

---

## Model handling
- Model is a HuggingFace model ID passed as `--model` (e.g. `meta-llama/…`).
- Local mode supports LoRAs via `model+adapter1+adapter2` (OptiLLM convention).

---

## Runtime configuration (expected)
**Env file (Orin):** `/etc/optillm-local/env`

Minimum env keys:
- `OPTILLM_API_KEY`
- `OPTILLM_MODEL`
- `HF_HOME` (recommended: `/opt/homelab/.cache/huggingface`)

Optional:
- `TRANSFORMERS_CACHE`
- `TORCH_HOME`
- `CUDA_VISIBLE_DEVICES`

---

## Process model
| Property | Requirement |
|-------|-------------|
| Execution | systemd service |
| Restart | automatic |
| Logging | journald |
| Privileges | non-root (user: christopherbailey) |

---

## Health checks
Preferred:
```
GET /v1/models
```

---

## Deployment
- **Source of truth:** Mini monorepo (`layer-inference/optillm-local`).
- **Deploy target:** Orin monorepo clone at `/opt/homelab/optillm-local`.
- **Service dir:** `/opt/homelab/optillm-local/layer-inference/optillm-local`.
- **Deploy helper:** `platform/ops/scripts/deploy-optillm-local-orin.sh`.

---

## Constraints
- Inference layer only (no routing logic).
- Do not bind to public interfaces.
- Do not mix CV/STT/TTS in this service.

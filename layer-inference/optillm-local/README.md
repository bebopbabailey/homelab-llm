# OptiLLM Local (Orin) — Overview

OptiLLM Local is a **CUDA-backed, OpenAI-compatible** inference service running on the
Jetson Orin AGX. It is treated as a **standard inference backend** and is accessed via
LiteLLM on the Mini.

- **Host:** Orin
- **Port:** 4040
- **Bind:** 0.0.0.0 (LAN only)
- **Auth:** `OPTILLM_API_KEY`
- **Repo root (Orin):** `/opt/homelab/optillm-local`
- **Service dir (Orin):** `/opt/homelab/optillm-local/layer-inference/optillm-local`

## Quick smoke test
```bash
curl -fsS http://127.0.0.1:4040/v1/models \
  -H "Authorization: Bearer $OPTILLM_API_KEY" | jq .
```

## Deployment model
- **Source of truth:** Mini monorepo (`layer-inference/optillm-local`).
- **Deploy target:** Orin monorepo clone at `/opt/homelab/optillm-local`.
- **Deploy helper:** `platform/ops/scripts/deploy-optillm-local-orin.sh`.

## Notes
- This service is **inference layer** (not gateway).
- CV/STT/TTS are **separate services**.

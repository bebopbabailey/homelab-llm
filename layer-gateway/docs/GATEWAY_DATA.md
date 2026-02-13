# Gateway Layer Data (DB‑Equivalent Snapshot)

This document captures the data the future system DB would store for the Gateway
layer. It is the current human‑readable source of truth.

## Services (Gateway layer)
| Service | Role | Bind | Port | Exposure | Health/Status | Systemd Unit | Env/Config | Notes |
|---|---|---|---|---|---|---|---|---|
| LiteLLM (litellm-orch) | Primary gateway/router | 0.0.0.0 | 4000 | LAN | `/health`, `/health/readiness`, `/health/liveliness` | `/etc/systemd/system/litellm-orch.service` | `layer-gateway/litellm-orch/config/router.yaml`, `layer-gateway/litellm-orch/config/env.local` | Clients must call LiteLLM only. |
| OptiLLM proxy | Optimization proxy behind LiteLLM | 127.0.0.1 | 4020 | Local only | none documented | `/etc/systemd/system/optillm-proxy.service` | `/etc/optillm-proxy/env`, `~/.optillm/proxy_config.yaml` | Upstream may be LiteLLM or MLX; avoid routing loops. |
| System monitor | Health/telemetry aggregator | (planned) | (planned) | Local only | N/A | (planned) | (planned) | Read‑only monitor; escalates via DB bulletin. |

## Ports (Gateway layer)
- **4000** — LiteLLM (LAN)
- **4020** — OptiLLM (localhost only)

## Contracts
- Client → **LiteLLM only** (`http://<mini>:4000/v1`).
- OptiLLM must not be exposed directly; it may call LiteLLM or MLX upstream depending on config.
- Gateway never runs inference.
- Showroom/backroom rule: only models present on Mini/Studio get handles.
- Studio OptiLLM local uses HF cache at `/Users/thestudio/models/hf/hub` (HF token required for gated pulls).

## Health checks (read‑only)
```bash
curl -sS http://127.0.0.1:4000/health
curl -sS http://127.0.0.1:4000/health/readiness
curl -sS http://127.0.0.1:4000/health/liveliness
```

## Escalation model (current)
- Monitor is **read‑only**.
- Monitor escalates by writing a bulletin entry (planned DB table).
- Root or layer/service agents perform restarts.

## Planned DB tables (Gateway slice)
- `services` (gateway entries)
- `ports` (bindings + exposure)
- `health_checks` (urls + last status)
- `alerts` / `bulletin` (escalations)
- `dependencies` (gateway ↔ inference/tools)

## Ownership
- Layer owner: Gateway agent
- Service owners: `litellm-orch`, `optillm-proxy`

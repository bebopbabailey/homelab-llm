# 2026-02-09 — Reality snapshot (Mini + Studio)

Purpose: capture a dated evidence snapshot for the high-risk claim families in
`docs/_core/CONSISTENCY_DOD.md` and compare against canonical docs.

This snapshot is **evidence**, not canon.

## Mini (Ubuntu) — evidence

### systemd units (ports/binds)

LiteLLM:
- Unit: `/etc/systemd/system/litellm-orch.service`
- ExecStart (override):
  - `--host 127.0.0.1 --port 4000 --detailed_debug`

Open WebUI:
- Unit: `/etc/systemd/system/open-webui.service`
- ExecStart:
  - `--host 127.0.0.1 --port 3000`

Prometheus:
- Unit: `/usr/lib/systemd/system/prometheus.service`

Grafana:
- Unit: `/usr/lib/systemd/system/grafana-server.service`

OpenVINO:
- Unit exists and is enabled: `ov-server.service`

OptiLLM proxy:
- Not present on Mini (no listener on `:4020`; no `optillm-proxy.service`).

### Listening sockets (selected)
Observed listeners:
- `127.0.0.1:4000` (litellm)
- `127.0.0.1:3000` (open-webui)
- `127.0.0.1:9090` (prometheus)
- `127.0.0.1:3001` (grafana)
- `127.0.0.1:8888` (searxng)
- `0.0.0.0:9000` (OpenVINO; python)

### Health / API behavior

Open WebUI:
- `GET http://127.0.0.1:3000/health` => `{ "status": true }`

LiteLLM:
- `GET http://127.0.0.1:4000/health` => **401** (auth required)
- `GET http://127.0.0.1:4000/v1/models` => **401** (auth required)
- `GET http://127.0.0.1:4000/health/readiness` => returns JSON status document

OpenVINO:
- `GET http://127.0.0.1:9000/health` => JSON: `{status:"ok", device:"GPU", models:9, ...}`

Prometheus:
- `GET http://127.0.0.1:9090/-/ready` => `Prometheus Server is Ready.`

Grafana:
- `GET http://127.0.0.1:3001/api/health` => JSON health response

## Studio (macOS) — evidence

### OptiLLM proxy (Studio)
- Listener: `0.0.0.0:4020` (observed via `lsof`)
- `GET http://127.0.0.1:4020/v1/models` returns an OpenAI list payload.

### MLX ports (mlxctl status)
Active listeners:
- `8100` listening — `mlx-gpt-oss-120b-mxfp4-q4`
- `8101` listening — `mlx-qwen3-next-80b-mxfp4-a3b-instruct`
- `8102` listening — `mlx-gpt-oss-20b-mxfp4-q4`
- `8103` listening — `pchamart-schematron8b-mlx-8bit`

Ports `8104+` observed idle (through `8139`).

### Bind evidence (lsof)
`lsof` shows `python3.1` listening on `*:<port>` for 8100–8103 (0.0.0.0 bind).

### /v1/models behavior
Note: `GET /v1/models` returns a **filesystem snapshot path** as the model ID
for these servers, e.g.:
- `/Users/thestudio/models/hf/models--mlx-community--gpt-oss-120b-MXFP4-Q4/snapshots/...`

This differs from the `mlx-*` handle names shown by `mlxctl`.

## Initial drift notes (from this snapshot)

1) **Mini LiteLLM /health returns 401**.
   Some docs imply unauthenticated health probes.

2) **OptiLLM proxy (4020) appears not running / not installed** on Mini.
   OptiLLM proxy runs on the Studio and is reached via LiteLLM `boost`.

3) **Studio /v1/models returns snapshot path IDs**, not `mlx-*` IDs.
   Any docs that claim /v1/models returns `mlx-*` need to be conditional:
   - `mlxctl` is the canonical model_id source,
   - /v1/models is transport-level and may differ.

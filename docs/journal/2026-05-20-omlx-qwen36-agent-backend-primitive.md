# 2026-05-20 - oMLX Qwen3.6 agent backend primitive

## Objective
Build a framework-neutral agent backend primitive around
`mlx-community/Qwen3.6-27B-OptiQ-4bit` using Studio oMLX `0.3.6`, bypassing the
failed vLLM-Metal/`8101` path and avoiding LiteLLM, OpenHands, Open WebUI, and
native MCP promotion in this slice.

## Result
The direct Studio oMLX backend is usable on the approved experimental LAN bind
`192.168.1.72:8120`, and the Mini-local sidecar is usable on
`127.0.0.1:4022`.

The implementation supersedes the failed `qwen36-mlx-coding-specialist` lane.
That lane's journal evidence was salvaged before pruning in master commit
`d8509f2bba5709e67711b34b0b5857ba1931a12e`.

No LiteLLM alias was added. No OpenHands acceptance was run. No public daily
alias was promoted. Native oMLX MCP remains deferred because the installed oMLX
runtime does not include the `mcp` package.

## Studio Runtime
- Host/port: `192.168.1.72:8120`
- Launchd label: `com.bebop.mlx-omni.8120`
- Launchd policy: `ProcessType=Interactive`, no background throttles
- Runtime: `/opt/homebrew/bin/omlx`
- oMLX version: `0.3.6`
- MLX version: `0.31.1`
- `mlx-lm` version: `0.31.2`
- `mlx-vlm` version: `0.4.4`
- Transformers version: `5.3.0`
- Model id: `omlx-qwen36-27b-optiq-4bit`
- Model source: `mlx-community/Qwen3.6-27B-OptiQ-4bit`
- Snapshot reused:
  `/Users/thestudio/models/hf/models--mlx-community--Qwen3.6-27B-OptiQ-4bit/snapshots/c8e1b620b9be2c03fd15fde261e25c9be8c664b7`
- Model symlink:
  `/Users/thestudio/models/omlx-agent/omlx-qwen36-27b-optiq-4bit`
- Base path: `/Users/thestudio/.omlx-qwen36-agent`
- Settings file:
  `/Users/thestudio/.omlx-qwen36-agent/model_settings.json`
- Context target: `32768`
- Runtime limits: `75%` max process memory, `4` max concurrent requests,
  `64GB` paged SSD cache, `8GB` hot cache
- Mode controls: `model_type_override="llm"`, no VLM path, thinking disabled
  through `enable_thinking=false` and forced chat-template kwargs

Disk preflight showed about `3.3 TiB` free on `/Users/thestudio`; no second model
download was needed.

## Direct Backend Gates
The direct backend passed the primitive gates:

| Gate | Result |
| --- | --- |
| `/v1/models` | returned `omlx-qwen36-27b-optiq-4bit` |
| plain chat/system adherence | `omlx-qwen36-ok` in `2.47s` |
| 8K context sanity | `ctx8-ok` in `19.24s` |
| 32K context sanity | `ctx32-ok` in `83.06s` |
| `tool_choice=auto` | structured OpenAI-compatible `tool_calls` returned |
| named/constrained tool | structured `noop` tool call returned |
| concurrent small requests | three requests completed with intact outputs |
| repeated-prefix probe | first run `17.26s`, second run `3.02s` |

The repeated-prefix response did not expose explicit cached-token accounting, but
the latency drop is usable evidence that the oMLX cache path is active.

GPT-OSS on `8126` stayed healthy and untouched during this lane.

## Mini Sidecar
The new `omlx-agent-gateway` sidecar is intentionally minimal:

- Bind: `127.0.0.1:4022`
- Upstream: `http://192.168.1.72:8120/v1`
- Public model id: `omlx-qwen36-27b-optiq-4bit`
- Endpoints:
  - `GET /health`
  - `GET /v1/models`
  - `GET /v1/model/info`
  - `POST /v1/chat/completions`
- Behavior:
  - pass through chat/tool requests
  - pass through streaming server-sent events for agent clients
  - normalize only the public/backend model id
  - keep backend API key in `/etc/homelab-llm/omlx-agent-gateway.secret.env`

Runtime sidecar probes passed from a direct worktree run:

| Gate | Result |
| --- | --- |
| `/health` | returned `status=ok`, bind `127.0.0.1:4022` |
| `/v1/models` | returned `omlx-qwen36-27b-optiq-4bit` |
| `/v1/model/info` | advertised chat, system messages, function calling, 32K input/output |
| plain chat | `sidecar-ok` in `0.66s` |
| tool call | structured `noop` tool call in `1.62s` |
| concurrent small requests | three requests completed in `0.56s`, `1.12s`, `1.68s` |
| stream passthrough | server-sent-event passthrough validated after the Pi smoke exposed `stream=true` as required |
| LAN bind check | `192.168.1.71:4022` refused connection |

The tracked systemd unit was added. Initial live activation exposed a stripped
systemd environment issue: `uv` was not on `PATH`. The runner now uses the known
absolute Mini `uv` path, and the live sidecar is active under
`omlx-agent-gateway.service` from the linked worktree with the same
`/etc/homelab-llm` env files. After merge/closeout, reinstall the tracked unit
so it points at the canonical primary repo path instead of the temporary
worktree path.

## Decision
Proceed with oMLX as the Qwen3.6 backend primitive. Compared with the failed
vLLM-Metal path, this stack loaded the exact MLX artifact, respected 32K context,
returned structured tool calls, survived concurrent small requests, and presented
a minimal framework-neutral localhost sidecar.

Follow-up work should make service durability boring: either fix the Mini
`systemctl` hang and install the tracked unit after merge, or create a minimal
runtime controller for this oMLX lane. Do not repair the bloated `mlxctl` path
for this lane.

## Rollback
- Studio backend:
  `sudo launchctl bootout system/com.bebop.mlx-omni.8120`
- Mini direct sidecar:
  `sudo systemctl stop omlx-agent-gateway.service`
- Mini systemd artifacts if needed:
  remove `/etc/systemd/system/omlx-agent-gateway.service` and
  `/etc/systemd/system/multi-user.target.wants/omlx-agent-gateway.service`

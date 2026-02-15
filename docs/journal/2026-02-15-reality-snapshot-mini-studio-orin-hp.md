# Reality Snapshot (Mini + Studio + Orin + HP)

Date: 2026-02-15

Purpose: capture a minimal, repeatable evidence snapshot so canonical docs can be kept consistent.
Do not include secrets.

## Mini (themini, Ubuntu 24.04)
- Listeners (expected):
  - LiteLLM: `127.0.0.1:4000`
  - Open WebUI: `127.0.0.1:3000`
  - Grafana: `127.0.0.1:3001`
  - Prometheus: `127.0.0.1:9090`
  - SearXNG: `127.0.0.1:8888`
  - OpenVINO: `0.0.0.0:9000`
- `platform/ops/scripts/healthcheck.sh` passes (auth-gated LiteLLM endpoints).

## Studio (thestudio.local, macOS)
- MLX canonical endpoint: Omni `:8100` (`com.bebop.mlx-omni.8100`).
- OptiLLM proxy: `:4020` (`com.bebop.optillm-proxy`).
- Legacy per-port MLX launcher is disabled: `com.bebop.mlx-launch`.
- Per-port listeners `8101/8102/8103/8109` are free.

## Orin (theorin, Jetson Orin AGX)
- No OptiLLM-local listener (port `4040` is free).
- Offload mount is present at `/mnt/seagate` via sshfs to Mini:
  `christopherbailey@192.168.1.71:/mnt/seagate/orin-offload`.

## HP DietPi (ryans-place)
- Home Assistant is listening on `:8123` and `home-assistant.service` is active.


# 2026-03-31 — OpenHands managed tailnet service promotion

## Summary
- `hands.tailfd1400.ts.net` was returning `502` because `svc:hands` still
  proxied to `http://127.0.0.1:4031` while no OpenHands runtime was listening.
- Promoted OpenHands on the Mini from a manual/operator-launched Docker session
  to a repo-managed `systemd` + Docker service.
- Preserved the network boundary:
  - local bind stays `127.0.0.1:4031`
  - remote operator URL stays `https://hands.tailfd1400.ts.net/`
  - no LAN exposure added
- Added `/etc/openhands/env` as a non-secret runtime env file and codified the
  host unit in `platform/ops/systemd/openhands.service`.
- Updated the OpenHands service bundle, canonical docs, and Mini ops scripts to
  the managed-runtime contract.
- Residual follow-up: the runtime sandbox image is still not cached, so first
  sandbox task execution remains a separate explicit step.

## Evidence before the change
```bash
curl -i --max-time 10 http://127.0.0.1:4031/
tailscale serve status --json | jq '.Services["svc:hands"]'
ssh orin 'curl -ki --max-time 10 https://hands.tailfd1400.ts.net/'
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'
systemctl list-unit-files | rg 'openhands|4031'
```

Observed:
- local `127.0.0.1:4031` returned connection refused
- `svc:hands` still mapped to `http://127.0.0.1:4031`
- remote tailnet root returned `HTTP/2 502`
- no `openhands-app` container was running
- no managed `openhands.service` existed

## Runtime implementation
- Added repo-managed unit:
  `platform/ops/systemd/openhands.service`
- Expanded non-secret env template:
  `platform/ops/templates/openhands.env.example`
- Installed host runtime files:
  - `/etc/systemd/system/openhands.service`
  - `/etc/openhands/env`
- Enabled the service:
  `sudo systemctl enable --now openhands.service`

## Validation
```bash
systemctl is-enabled openhands.service
systemctl is-active openhands.service
ss -ltnp | rg ':4031'
curl -fsSI http://127.0.0.1:4031/
curl -sS --connect-timeout 2 http://192.168.1.71:4031/ >/dev/null
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}' | rg 'openhands-app'
docker inspect openhands-app --format '{{json .HostConfig.Binds}}'
docker inspect openhands-app --format '{{json .Config.Env}}' | jq -r '.[]' | rg '^SANDBOX_VOLUMES='
tailscale serve status --json | jq '.Services["svc:hands"]'
ssh orin 'curl -kI --max-time 10 https://hands.tailfd1400.ts.net/'
```

Expected/observed success criteria:
- `openhands.service` is enabled and active
- `127.0.0.1:4031` is listening
- local root responds
- `192.168.1.71:4031` remains closed
- `openhands-app` is running
- bind list includes only Docker socket and persistence path
- `SANDBOX_VOLUMES` carries the disposable workspace contract for future sandbox launches
- remote tailnet root returns `HTTP/2 200`

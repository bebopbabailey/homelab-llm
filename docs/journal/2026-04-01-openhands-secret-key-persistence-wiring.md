# 2026-04-01 — OpenHands secret-key persistence wiring

## Why this exists
The managed OpenHands service on the Mini was reachable through
`https://hands.tailfd1400.ts.net/`, but restart-persistent secret handling was
incomplete.

## Observed issue
- `/etc/openhands/secret.env` existed on the host as `0600 root:root`
- `openhands.service` still loaded only `/etc/openhands/env`
- the running `openhands-app` container did not have `OH_SECRET_KEY`
- restart logs still showed:
  `OH_SECRET_KEY was not defined. Secrets will not be persisted between restarts.`

## Root cause
The host-side secret file had been created, but the repo-managed and installed
systemd unit had not been updated to load it. The Docker launch also did not
pass `OH_SECRET_KEY` through to the container.

Typing `EnvironmentFile=/etc/openhands/secret.env` at the shell prompt did
nothing; it did not edit the unit file.

## Contract after the fix
- `/etc/openhands/env` remains non-secret runtime config only
- `/etc/openhands/secret.env` is the dedicated root-only companion file for
  `OH_SECRET_KEY`
- the repo-managed unit loads both files
- Docker receives `OH_SECRET_KEY` via `--env OH_SECRET_KEY`
- no bind, port, LAN exposure, or tailnet exposure changed

## Validation contract
- `systemctl show openhands.service -p EnvironmentFiles` lists both env files
- `docker exec openhands-app python3 -c 'import os; print("present" if os.getenv("OH_SECRET_KEY") else "missing")'`
  prints `present`
- post-restart `journalctl -u openhands.service` no longer shows the
  `OH_SECRET_KEY was not defined` warning
- local `http://127.0.0.1:4031/` and remote
  `https://hands.tailfd1400.ts.net/` remain healthy

## Residual note
Users with Docker-level access on the Mini can inspect container state broadly.
That is acceptable under the current trust model because Docker access is
already a highly privileged boundary.

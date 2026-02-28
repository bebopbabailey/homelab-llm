# Diagnostics (Read‑Only)

Use these to gather facts without changing system state.

## Service status (Mini)
```bash
systemctl status litellm-orch.service open-webui.service ov-server.service searxng.service grafana-server.service prometheus.service --no-pager
```

## Logs (Mini)
```bash
journalctl -u litellm-orch.service -n 200 --no-pager
journalctl -u open-webui.service -n 200 --no-pager
journalctl -u ov-server.service -n 200 --no-pager
journalctl -u searxng.service -n 200 --no-pager
journalctl -u grafana-server.service -n 200 --no-pager
journalctl -u prometheus.service -n 200 --no-pager
```

## Health checks (Mini)
```bash
curl -sS http://127.0.0.1:4000/health/readiness -H "Authorization: Bearer $LITELLM_MASTER_KEY"
curl -sS http://127.0.0.1:3000/health
curl -sS http://127.0.0.1:9000/health
```

## Ports  
```bash
ss -lntp
```

## Studio scheduling policy (Mini -> Studio)
Local deterministic policy check:
```bash
uv run python platform/ops/scripts/validate_studio_policy.py --json
uv run python platform/ops/scripts/audit_studio_scheduling.py --policy-only --json
```

Remote read-only audit:
```bash
uv run python platform/ops/scripts/enforce_studio_launchd_policy.py --host studio --json
uv run python platform/ops/scripts/audit_studio_scheduling.py --host studio --json
```

References:
- `docs/foundation/studio-scheduling-policy.md`

## Submodules
```bash
git submodule status
```

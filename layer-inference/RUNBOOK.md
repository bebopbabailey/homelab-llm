# Inference Layer Runbook

Scope: inference backend health checks and safe restarts (host-specific).

## OpenVINO server (Mini)
```bash
sudo systemctl restart ov-server.service
journalctl -u ov-server.service -n 200 --no-pager
curl -fsS http://127.0.0.1:9000/health | jq .
```

## MLX lanes (Studio)
Read-only checks on Studio:
```bash
# Required active listener checks (team lanes)
ssh studio "curl -fsS http://127.0.0.1:8100/v1/models | jq ."
ssh studio "curl -fsS http://127.0.0.1:8101/v1/models | jq ."
ssh studio "curl -fsS http://127.0.0.1:8102/v1/models | jq ."

ssh studio "mlxctl status"
ssh studio "mlxctl status --checks"
ssh studio "mlxctl verify"
ssh studio "mlxctl reconcile --json"
./platform/ops/scripts/mlxctl studio-cli-sha
```

Mini-side LAN reachability checks:
```bash
for p in 8100 8101 8102; do
  curl -fsS "http://192.168.1.72:${p}/v1/models" | jq .
done
```

Reconcile contract:
- `mlxctl reconcile` is dry-run by default.
- Use `mlxctl reconcile --apply` only when stale assignment candidates are confirmed.

Team-lane boot path now uses per-lane launchd labels
(`com.bebop.mlx-lane.8100/.8101/.8102`) to launch `vllm-metal` (`vllm serve`)
for assigned `8100-8119` lanes.
```bash
# 1) Restart managed lane labels from registry assignments
./platform/ops/scripts/mlxctl sync-studio-cli
./platform/ops/scripts/mlxctl mlx-launch-stop --ports 8100,8101,8102
./platform/ops/scripts/mlxctl mlx-launch-start

# 1b) If lanes are disabled/unloaded after reboot/crash, repair assigned lanes
./platform/ops/scripts/mlxctl repair-lanes --json
./platform/ops/scripts/mlxctl repair-lanes --apply --json

# 2) Validate runtime family + listeners
ssh studio "mlxctl status --checks"
ssh studio "lsof -nP -iTCP:8100-8102 -sTCP:LISTEN"
ssh studio "sudo launchctl print system/com.bebop.mlx-lane.8102 | sed -n '1,80p'"

# Interpretation:
# `listener_visible=false` can still be healthy under root-owned launchd lanes.
# Prefer lane state in `mlxctl status --checks --json` for desired vs actual truth.
# For load/readiness transitions, `/v1/chat/completions` is the primary readiness proof
# and `/v1/models` is only the served-model identity check.

# 3) Validate rendered vLLM args (main lane auto-tool)
./platform/ops/scripts/mlxctl vllm-capabilities --json
./platform/ops/scripts/mlxctl vllm-render --ports 8101 --validate --json
ssh studio "ps -eo pid,command | rg -- '--port 8101|enable-auto-tool-choice|tool-call-parser'"
ssh studio "python3 - <<'PY'
import json, urllib.request
payload={
  'model':'mlx-llama-3-3-70b-4bit-instruct',
  'messages':[{'role':'user','content':'Use the noop tool once, then stop.'}],
  'tools':[{'type':'function','function':{'name':'noop','description':'noop','parameters':{'type':'object','properties':{}}}}],
  'tool_choice':'auto',
  'stream':False,
  'max_tokens':128
}
req=urllib.request.Request(
  'http://127.0.0.1:8101/v1/chat/completions',
  data=json.dumps(payload).encode(),
  headers={'Content-Type':'application/json'},
  method='POST'
)
with urllib.request.urlopen(req, timeout=60) as r:
  body=json.loads(r.read().decode())
print(json.dumps(body['choices'][0]['message'], indent=2))
PY"
# For `8101`, success means structured `tool_calls`, not raw `<tool_call>` text.
```

Load safety contract:
- `mlxctl load` updates lane `desired_target` immediately.
- A healthy lane is not torn down until preflight passes in the serving venv.
- A candidate is only marked as serving after two consecutive readiness passes
  with no restart between them.
- Failed loads keep `actual_serving_target` unchanged when the old lane is still
  serving, or explicitly mark the lane down when in-place cutover fails.

Scoped lane restart safety:
- `mlx-launch-start --ports ...` refuses partial assigned-team-lane scope.
- Use `--allow-partial` only for intentional single-lane interventions.

Quality gate (from repo host with Studio network access):
```bash
uv run python platform/ops/scripts/mlx_quality_gate.py --host thestudio.tailfd1400.ts.net --json
```

## Studio SSH preflight + lock-state handling
Use this preflight before any long vLLM-metal run.

```bash
ssh -o BatchMode=yes -o IdentitiesOnly=yes -o ControlMaster=no -o ControlPath=none studio "echo ssh-preflight-ok"
```

If preflight fails, classify by stderr text:
- `This system is locked...` -> `LOCKED` (host booted but needs local unlock/login).
- `Permission denied (publickey,...)` -> `AUTH_REJECTED` (key/auth path not accepted yet).
- `timed out` / `No route to host` -> `HOST_DOWN` (reboot/unreachable).
- `broken pipe` -> `TRANSPORT_ERROR` (session/socket instability; retry preflight and avoid multiplexing).

Operational defaults for automation:
- Use non-multiplexed SSH for `studio` (`ControlMaster=no`, `ControlPath=none`).
- Keep `BatchMode=yes` + `IdentitiesOnly=yes` on automation commands.
- Treat `LOCKED` as a hard stop until local unlock completes.

FileVault policy:
- `studio` currently runs with `FileVault: On`.
- After some reboots/crash cycles, local unlock may be required before remote automation is reliable.

## Historical 812x Tuning (Archived)
Legacy `8120/8121/8122` campaign procedures are archived and are not the
canonical production runtime path.

Use:
- `docs/archive/2026-03-layer-inference-812x-experimental-tuning-history.md`

Canonical runtime operations for Studio lanes remain in this runbook and in:
- `docs/foundation/mlx-registry.md`
- `docs/foundation/studio-scheduling-policy.md`

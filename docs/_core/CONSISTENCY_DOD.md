# Consistency Definition of Done (DoD)

This document defines what “documentation is consistent” means for this repo.
It is written to be **actionable by agents** and repeatable over time.

When the system changes (routing, ports, bindings, auth, registries), this DoD
is the checklist that prevents drift.

## Scope

This DoD applies to **canonical operational docs** only:

- `docs/PLATFORM_DOSSIER.md`
- `docs/foundation/topology.md`
- `docs/INTEGRATIONS.md`
- `docs/foundation/testing.md`
- `TOPOLOGY.md`

Supporting governance:

- `docs/_core/SOURCES_OF_TRUTH.md`
- `docs/_core/CHANGE_RULES.md`

Out of scope (not required to be runtime-accurate):

- `docs/journal/*` (append-only evidence)
- `docs/archive/*` (historical)
- `docs/deprecated/*`
- `next-projects/*` (planning)

## Consistency “Done” Criteria

Documentation is considered **consistent** when all of the following are true:

1. **No critical/high contradictions** exist between the canonical docs in scope
   and authoritative evidence sources.
2. Every **high-risk claim family** (below) has:
   - a named evidence source,
   - a deterministic check command,
   - and an expected signal.
3. Any remaining mismatches are recorded as claim IDs in the dated audit ledger
   (`docs/_core/consistency_audit_YYYY-MM.md`) with a disposition:
   - `fix_now`
   - `defer`
   - `accepted`
4. After changes, `docs/_core/CHANGE_RULES.md` is still true (no undocumented
   update obligations).

## High-risk claim families

These are the claims most likely to cause operational incidents or unsafe agent
actions if they drift.

### A) Ports, binds, and exposure

Evidence sources (preferred order):
- systemd unit `ExecStart` flags (authoritative for binds/ports)
- `/etc/*env` EnvironmentFile values
- live health endpoints

Checks (Mini examples; adapt per host):
```bash
# bindings/ports (Mini)
sudo systemctl cat litellm-orch.service | sed -n '1,200p'
sudo systemctl cat open-webui.service | sed -n '1,200p'

# liveness
curl -fsS http://127.0.0.1:4000/v1/models | jq -r '.data[].id' | head
curl -fsS http://127.0.0.1:3000/health | jq .
```

Expected signals:
- bind addresses and ports match canonical docs
- any LAN exposure is explicitly documented as “approved/maintenance-only”

### B) Auth requirements

Evidence sources:
- `/etc/*env` files (do not commit)
- documented client requirements

Checks:
```bash
# confirm auth-gated endpoints behave as documented
curl -fsS http://127.0.0.1:4000/v1/models -H "Authorization: Bearer $LITELLM_API_KEY" | jq -r '.data[0].id'
```

Expected signals:
- canonical docs describe which keys are required and where they live

### C) Routing/aliases/handles and model inventory

Evidence sources:
- `layer-gateway/litellm-orch/config/router.yaml`
- `layer-gateway/registry/handles.jsonl`
- `scripts/validate_handles.py`

Checks:
```bash
python3 scripts/validate_handles.py

curl -fsS http://127.0.0.1:4000/v1/models \
  -H "Authorization: Bearer $LITELLM_API_KEY" \
  | jq -r '.data[].id' | sort | head -n 50
```

Expected signals:
- documented aliases exist in router/config
- `/v1/models` aligns with what docs claim is active

#### Boost lane reachability (Mini → Studio)

Evidence sources:
- `layer-gateway/litellm-orch/config/router.yaml` (`model_name: boost` uses `OPTILLM_API_BASE`)
- Studio listener on `:4020`

Checks:
```bash
# on Studio
curl -fsS http://127.0.0.1:4020/v1/models -H "Authorization: Bearer dummy" | jq -r '.object'

# on Mini: confirm the `boost` handle is present in LiteLLM model list
curl -fsS http://127.0.0.1:4000/v1/models \
  -H "Authorization: Bearer $LITELLM_API_KEY" \
  | jq -r '.data[].id' | rg '^boost$'
```

Expected signals:
- Studio OptiLLM responds on `:4020`
- LiteLLM exposes the `boost` handle

### D) MLX control plane (Studio)

Evidence sources:
- `docs/foundation/mlx-registry.md`
- `platform/ops/scripts/mlxctl`

Checks:
```bash
# on Studio
mlxctl status
mlxctl list
```

Expected signals:
- docs describe MLX ports and “only mlxctl” rule accurately

### E) “Deprecated direction” guardrails

If a technology is “maintenance-only” or “not supported going forward” (e.g.
OpenVINO in your current roadmap), canonical docs must:
- explicitly state the posture (maintenance-only vs active)
- not instruct new builds/evaluations unless they are marked archived/deprecated

## Severity rubric

- **critical**: unsafe guidance (could cause exposure/port changes/secrets leak) or
  contradictions affecting operator actions
- **high**: contradictions about binds/ports/auth/routing that could break clients
- **medium**: inconsistent but not operationally dangerous (naming, phrasing)
- **low**: historical/support drift

## Recording drift

When drift is found:
1) Add or update a row in the dated audit ledger:
   - `docs/_core/consistency_audit_2026-02.md` (or current month)
2) Fix docs or defer with explicit rationale.
3) If the drift was caused by a class of change (routing, ports), update
   `docs/_core/CHANGE_RULES.md` so it can’t recur silently.

## Monthly manual audit (recommended)

To prevent drift, run a **manual** monthly review (no scheduled automation) and
record findings in a dated ledger.

1) Copy the prior ledger forward:
   - Create `docs/_core/consistency_audit_YYYY-MM.md` for the current month.
2) Capture a short evidence snapshot (append-only):
   - Add a dated note under `docs/journal/` (e.g. `docs/journal/YYYY-MM-DD-reality-snapshot-*.md`).
3) Reconcile canonical docs:
   - Fix contradictions or explicitly defer them in the ledger.

Suggested checks (run on the relevant host):
```bash
# Mini: routing + handles + auth expectations
python3 scripts/validate_handles.py

curl -fsS http://127.0.0.1:4000/v1/models \
  -H "Authorization: Bearer $LITELLM_API_KEY" \
  | jq -r '.data[].id' | sort | head -n 80

curl -fsS http://127.0.0.1:4000/health/readiness | jq .

# Studio: OptiLLM proxy lane + MLX controller
curl -fsS http://127.0.0.1:4020/v1/models \
  -H "Authorization: Bearer $OPTILLM_API_KEY" \
  | jq -r '.object'

mlxctl status
```

Expected outcome:
- Canonical docs in scope remain accurate:
  `docs/PLATFORM_DOSSIER.md`, `docs/foundation/topology.md`,
  `docs/INTEGRATIONS.md`, `docs/foundation/testing.md`, `TOPOLOGY.md`.
- Any mismatches are captured as claim IDs in the monthly ledger with a clear
  disposition.

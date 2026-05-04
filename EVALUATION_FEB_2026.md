# Evaluation — February 2026

**Scope**: Full monorepo read-only audit — documentation-vs-reality drift, DOCS_CONTRACT compliance, and autonomous-agent readiness assessment.

**Date**: 2026-02-18
**Method**: Static analysis of all files in the repository (submodules not initialized; findings limited to monorepo content).

---

## Table of Contents

1. [Documentation Drift (Current)](#1-documentation-drift-current)
2. [DOCS_CONTRACT Compliance](#2-docs_contract-compliance)
3. [Security Observations](#3-security-observations)
4. [Autonomous Agent Readiness — What's Already Strong](#4-autonomous-agent-readiness--whats-already-strong)
5. [Autonomous Agent Readiness — Gaps and Recommendations](#5-autonomous-agent-readiness--gaps-and-recommendations)
6. [Prioritised Roadmap](#6-prioritised-roadmap)

---

## 1. Documentation Drift (Current)

### 1.1 Critical: LiteLLM binding address conflict

| Source | Claim |
|--------|-------|
| `TOPOLOGY.md` (root, line 6) | `127.0.0.1:4000` |
| `docs/PLATFORM_DOSSIER.md` (port table, line 22) | bind `127.0.0.1` |
| `docs/PLATFORM_DOSSIER.md` (exposure section, line 76) | "Local-only: LiteLLM 4000 (tailnet HTTPS)" |
| `docs/foundation/topology.md` (port table, line 44) | base URL `http://127.0.0.1:4000` |
| `layer-gateway/docs/GATEWAY_DATA.md` (line 9) | bind `0.0.0.0`, port 4000, exposure **LAN** |
| `platform/ops/systemd/litellm-orch.service` (line 11) | `--host 0.0.0.0 --port 4000` |

**Verdict**: The systemd unit binds `0.0.0.0` (LAN-reachable). GATEWAY_DATA.md is correct; the other four documents claim `127.0.0.1`. If LAN exposure is intentional (Tailscale Serve forwards into it), the authoritative docs should state `0.0.0.0` + "access controlled via Tailscale ACLs". If LAN exposure is unintended, the systemd unit should be changed to `127.0.0.1`.

### 1.2 High: OptiLLM proxy — repo systemd unit ≠ documented Studio deployment

| Source | Host | Bind | Upstream |
|--------|------|------|----------|
| `platform/ops/systemd/optillm-proxy.service` | Mini (implied by 127.0.0.1 upstream) | `127.0.0.1:4020` | `http://127.0.0.1:4000/v1` (LiteLLM) |
| `docs/PLATFORM_DOSSIER.md` (lines 27, 51-55) | **Studio** | `0.0.0.0:4020` | `http://192.168.1.72:8100/v1` (MLX Omni) |
| `TOPOLOGY.md` (root, line 17) | Studio | `0.0.0.0:4020` | — |
| `layer-gateway/docs/GATEWAY_DATA.md` (line 10) | — | `127.0.0.1:4020` | "may be LiteLLM or MLX" |

**Verdict**: The systemd file in the repo describes a Mini-local variant (`--base-url http://127.0.0.1:4000/v1`). The live Studio deployment described in PLATFORM_DOSSIER uses launchd with `--base-url http://192.168.1.72:8100/v1` (MLX upstream). Either the systemd file is stale/superseded, or there are two different deployment modes. Either way the repo artifact does not match the documented runtime.

### 1.3 High: Root `TOPOLOGY.md` missing Orin host

`docs/foundation/topology.md` and `docs/PLATFORM_DOSSIER.md` both document the Orin AGX (voice services, edge inference, offload mount). Root `TOPOLOGY.md` lists only Mini and Studio — it should include Orin and DietPi (Home Assistant) to match the authoritative sources.

### 1.4 Medium: `healthcheck.sh` — OptiLLM check targets wrong host

`platform/ops/scripts/healthcheck.sh` line 73 checks `http://127.0.0.1:4020/v1/models` (localhost on Mini). Per PLATFORM_DOSSIER the live OptiLLM proxy runs on Studio (`192.168.1.72:4020`). If run on Mini, this check would always fail unless the stale Mini-local systemd deployment is also active.

### 1.5 Medium: foundation/topology.md line 4 — OptiLLM listed under Mini

`docs/foundation/topology.md` line 4 lists "OptiLLM" among Mini services. PLATFORM_DOSSIER and TOPOLOGY.md place OptiLLM on Studio. This line should be corrected or clarified (e.g., "OptiLLM proxy runs on Studio, routed via LiteLLM boost on Mini").

### 1.6 Low: `DIAGNOSTICS.md` service name `ov-server`

DIAGNOSTICS.md references systemd unit `ov-server`. Confirm the actual unit is named `ov-server.service` on the Mini; PLATFORM_DOSSIER references `/etc/systemd/system/ov-server.service`, so it is likely correct but worth a runtime spot-check.

### 1.7 Low: Grafana metrics names unvalidated

`layer-interface/grafana/dashboards/litellm-overview.json` references PromQL metrics like `litellm_proxy_total_requests_metric_total`. These names should be validated against the actual LiteLLM Prometheus export (the metric naming convention has changed between LiteLLM releases).

### 1.8 Info: Stale references to `/home/christopherbailey/homelab-llm/...`

Multiple layer-level docs reference the absolute path `/home/christopherbailey/homelab-llm/CONSTRAINTS.md` (e.g. `layer-gateway/CONSTRAINTS.md`, `layer-interface/CONSTRAINTS.md`). These are correct for the Mini runtime but not for any CI or alternate checkout. Acceptable for a homelab but a portability concern for agents running in sandboxed environments.

---

## 2. DOCS_CONTRACT Compliance

**Contract** (`DOCS_CONTRACT.md`): Each service directory must contain README.md, SERVICE_SPEC.md, ARCHITECTURE.md, AGENTS.md, RUNBOOK.md, TASKS.md.

### Fully compliant (all 6 required files present)

| Service directory | Notes |
|---|---|
| `layer-gateway/optillm-local/` | Placeholder (not active) |
| `layer-gateway/system-monitor/` | Placeholder (not deployed) |
| `layer-gateway/tiny-agents/` | Active MVP with source code |
| `layer-inference/optillm-local/` | Deferred |
| `layer-inference/orin-llm-server/` | Documentation-only |
| `layer-interface/grafana/` | Active + config in repo |
| `layer-interface/open-webui/` | Active |
| `layer-interface/voice-gateway/` | Design phase |
| `layer-data/content-extract/` | Design phase with full schema |
| `layer-data/vector-db/` | Placeholder |

### Missing documentation (submodule directories — empty in checkout)

| Service directory | Submodule repo | Issue |
|---|---|---|
| `layer-gateway/litellm-orch/` | `bebopbabailey/litellm-orch` | No docs visible without `git submodule update --init` |
| `layer-gateway/optillm-proxy/` | `bebopbabailey/optillm-proxy` | Same |
| `layer-inference/ov-llm-server/` | `bebopbabailey/ov-llm-server` | Same |
| `layer-tools/mcp-tools/` | `bebopbabailey/mcp-tools` | Same |
| `layer-tools/searxng/` | `bebopbabailey/searxng` | Same |

**Impact**: Any agent cloning this monorepo without submodule init will have zero visibility into the five most critical runtime services. This is the single largest gap for autonomous operation.

### Partial compliance

| Directory | Present | Missing |
|---|---|---|
| `layer-tools/prometheus/` | README, SERVICE_SPEC, ARCHITECTURE, AGENTS, RUNBOOK, TASKS | — (fully compliant, but no CONSTRAINTS.md or DEPENDENCIES.md at service level) |
| `layer-data/registry/` | README, lexicon.jsonl | SERVICE_SPEC, ARCHITECTURE, AGENTS, RUNBOOK, TASKS (may be acceptable — registry is data, not a service) |

---

## 3. Security Observations

### 3.1 Hardcoded database credential

`platform/ops/scripts/deprecated/sync-benny-prompts` line 7 contains:
```
DB_URL = "postgresql://litellm:blue3232@127.0.0.1:5432/litellm"
```
Although the file is in `deprecated/`, the password is in git history. **Recommendation**: Rotate the PostgreSQL password if the database is still in use, and add the file to `.gitignore` or remove it.

### 3.2 Dummy API key in systemd unit

`platform/ops/systemd/optillm-proxy.service` line 10 contains `--optillm-api-key dummy`. This is a placeholder but could be misleading. Confirm the live deployment uses a real key via the env file.

### 3.3 LiteLLM LAN binding (see §1.1)

If `0.0.0.0:4000` is intentional, ensure firewall rules or Tailscale ACLs prevent unintended LAN access. If not intentional, bind to `127.0.0.1`.

---

## 4. Autonomous Agent Readiness — What's Already Strong

The repo is significantly ahead of most homelab projects in terms of agent-readiness. Existing strengths:

| Capability | Evidence |
|---|---|
| **Layered architecture** | 5 layers with explicit boundaries (Interface, Gateway, Inference, Tools, Data) |
| **Per-scope AGENTS.md** | 13 AGENTS.md files defining permissions, scope, and non-negotiables per role |
| **Sandbox permissions** | `SANDBOX_PERMISSIONS.md` — role-based read/write/execute matrix |
| **Incident flow** | `INCIDENT_FLOW.md` — root-agent triage → smallest-responsible-agent fix → root validates |
| **Docs contract** | `DOCS_CONTRACT.md` — minimum doc set per directory level |
| **Read-only diagnostics** | `DIAGNOSTICS.md` — safe health-gathering commands for any agent |
| **Change rules** | `docs/_core/CHANGE_RULES.md` — "if X changes, update Y" gates |
| **Consistency audit method** | `docs/_core/CONSISTENCY_DOD.md` — severity rubric, claim families, monthly cadence |
| **Completed audit** | `docs/_core/consistency_audit_2026-02.md` — 27 claims reconciled |
| **Operational controllers** | `mlxctl` (MLX) and `ovctl` (OpenVINO) — agent-callable CLIs |
| **Lexicon registry** | `layer-data/registry/lexicon.jsonl` — deterministic term normalisation |
| **Model handles registry** | `layer-gateway/registry/handles.jsonl` — JSONL with schema validation |
| **Handle validator** | `scripts/validate_handles.py` — schema + collision checks |
| **Foundation docs** | Thorough onboarding material for both humans and agents |
| **Journal** | Append-only timestamped discovery/experiment log |
| **Codex skill** | `.codex/skills/homelab-durability/SKILL.md` — enforcement rules for Codex agents |
| **TinyAgents MVP** | First autonomy layer with MCP tool integration and LiteLLM-only constraint |
| **Sources of truth hierarchy** | `docs/_core/SOURCES_OF_TRUTH.md` — authoritative → operational → planning → historical |

---

## 5. Autonomous Agent Readiness — Gaps and Recommendations

### 5.1 Machine-Readable Service Registry (HIGH PRIORITY)

**Current state**: Service metadata is scattered across Markdown tables (PLATFORM_DOSSIER, GATEWAY_DATA, topology.md). Agents must parse prose to discover endpoints, ports, and health checks.

**Recommendation**: Create a single `platform/registry/services.json` (or JSONL) with structured entries:
```json
{
  "service_id": "litellm-orch",
  "layer": "gateway",
  "host": "mini",
  "bind": "0.0.0.0",
  "port": 4000,
  "health_endpoint": "/health/readiness",
  "auth_required": true,
  "systemd_unit": "litellm-orch.service",
  "managed_by": "systemd",
  "status": "active"
}
```
This becomes the single source of truth for service discovery. Docs can be generated from it.

### 5.2 Submodule Visibility for Agents (HIGH PRIORITY)

**Current state**: 5 core runtime services (litellm-orch, optillm-proxy, ov-llm-server, mcp-tools, searxng) are git submodules. A fresh clone has empty directories.

**Recommendation** (pick one):
- **Option A**: Add a post-clone hook or `Makefile` target: `make init` runs `git submodule update --init --recursive`.
- **Option B**: Mirror essential service-level docs (SERVICE_SPEC.md, AGENTS.md) into the monorepo as read-only copies.
- **Option C**: Add a CI step that validates submodule content and generates a combined docs artifact.

### 5.3 Automated Drift Detection (HIGH PRIORITY)

**Current state**: Drift detection is manual (monthly audit per CONSISTENCY_DOD.md). The Feb 2026 audit found 27 claims to reconcile.

**Recommendation**: Build a `scripts/drift_check.py` that:
- Reads the machine-readable service registry (§5.1).
- For each service: attempts `curl` to health endpoint, compares bind/port claims against systemd/launchd unit files present in the repo.
- Compares TOPOLOGY.md / PLATFORM_DOSSIER.md port tables against the registry.
- Outputs a JSON report of mismatches.
- Can be run by any agent or cron.

### 5.4 Idempotent Deployment and Rollback (MEDIUM PRIORITY)

**Current state**: `platform/ops/scripts/redeploy.sh` does `git pull → uv sync → restart`. No idempotency guarantee, no rollback procedure, no dry-run mode.

**Recommendation**:
- Add `--dry-run` flag to redeploy.sh.
- Record pre-deploy state (git SHA, service status) to `/var/log/homelab-llm/deploys/`.
- Add `rollback.sh` that reverts to the last recorded SHA and restarts.
- Document the deploy/rollback cycle in a RUNBOOK.

### 5.5 System Monitor Service (MEDIUM PRIORITY)

**Current state**: `layer-gateway/system-monitor/` is fully documented (SERVICE_SPEC, ARCHITECTURE, AGENTS, RUNBOOK, TASKS) but has zero implementation. Tasks list 5 pending items.

**Recommendation**: Implement the minimal monitoring API (the first task in TASKS.md):
- `GET /health` — own health.
- `GET /status` — aggregated health of all services (calls each health endpoint).
- SQLite store for incident history.
- This is the nucleus for self-healing: agents query `/status` instead of running ad-hoc curl commands.

### 5.6 Structured Error Taxonomy (MEDIUM PRIORITY)

**Current state**: No error codes or categories. Voice Gateway SERVICE_SPEC mentions `error_code` in its JSONL log schema but no taxonomy exists.

**Recommendation**: Define `platform/registry/error_codes.json`:
```json
{
  "E001": {"category": "health", "message": "Service unreachable", "severity": "critical"},
  "E002": {"category": "health", "message": "Health endpoint returned non-200", "severity": "high"},
  "E003": {"category": "config", "message": "Bind address mismatch", "severity": "medium"}
}
```
Agents can reference this to classify failures and select recovery strategies.

### 5.7 CI/CD Pipeline (MEDIUM PRIORITY)

**Current state**: No `.github/workflows/` directory. No CI.

**Recommendation**: Start with a minimal GitHub Actions workflow:
1. `validate_handles.py` runs on every PR.
2. `drift_check.py` (§5.3) runs on a schedule (weekly).
3. Submodule init + doc presence check on every PR.
4. Optionally: markdown lint, broken-link check.

### 5.8 Self-Healing Runbooks (LOW PRIORITY, HIGH IMPACT)

**Current state**: Runbooks are human-readable Markdown. An agent can read them but cannot execute a structured recovery plan.

**Recommendation**: Supplement each RUNBOOK.md with a machine-readable `runbook.yaml`:
```yaml
service: litellm-orch
checks:
  - name: health_readiness
    command: "curl -fsS -H 'Authorization: Bearer $LITELLM_MASTER_KEY' http://127.0.0.1:4000/health/readiness"
    expect: "status_code: 200"
recovery:
  - name: restart
    command: "sudo systemctl restart litellm-orch.service"
    max_attempts: 2
    cooldown_seconds: 10
    verify: health_readiness
```
Agents parse YAML directly for recovery orchestration.

### 5.9 Cross-Host Health Aggregation (LOW PRIORITY)

**Current state**: `healthcheck.sh` checks Mini-local services + one Studio endpoint (MLX 8100). No Orin checks. No DietPi checks.

**Recommendation**: Extend healthcheck.sh (or the system monitor) to check all hosts:
- Studio: MLX 8100, OptiLLM 4020
- Orin: Voice Gateway (when deployed)
- DietPi: Home Assistant 8123

### 5.10 Configuration Validation (LOW PRIORITY)

**Current state**: No automated validation that env files, router.yaml, or registry files are internally consistent.

**Recommendation**: Add `scripts/validate_config.py` that:
- Checks model handles in `handles.jsonl` against models referenced in `router.yaml` (requires submodule).
- Checks ports in systemd units against the service registry.
- Checks env file paths exist on the expected host (where possible).

---

## 6. Prioritised Roadmap

### Phase 1 — Fix Documentation Drift (immediate, ≤1 day)

- [ ] Resolve LiteLLM bind address conflict (§1.1): update TOPOLOGY.md, PLATFORM_DOSSIER.md, and foundation/topology.md to state `0.0.0.0` if intentional, or change the systemd unit to `127.0.0.1`.
- [ ] Resolve OptiLLM proxy systemd unit drift (§1.2): either update/remove the stale Mini systemd file or annotate it as "alternate local-dev deployment."
- [ ] Add Orin + DietPi to root `TOPOLOGY.md` (§1.3).
- [ ] Fix `healthcheck.sh` OptiLLM target (§1.4).
- [ ] Clarify OptiLLM host in `docs/foundation/topology.md` line 4 (§1.5).
- [ ] Rotate the exposed PostgreSQL password and/or remove the deprecated script (§3.1).

### Phase 2 — Machine-Readable Foundations (1–2 weeks)

- [ ] Create `platform/registry/services.json` — machine-readable service registry (§5.1).
- [ ] Add submodule init automation or mirrored docs (§5.2).
- [ ] Build `scripts/drift_check.py` — automated drift detection (§5.3).
- [ ] Add minimal CI pipeline: handle validation + drift check + doc presence (§5.7).

### Phase 3 — Self-Healing Nucleus (2–4 weeks)

- [ ] Implement system monitor MVP: `/health`, `/status`, SQLite store (§5.5).
- [ ] Define error taxonomy (§5.6).
- [ ] Add idempotent deploy + rollback scripts (§5.4).
- [ ] Supplement runbooks with machine-readable `runbook.yaml` (§5.8).

### Phase 4 — Full Autonomous Readiness (1–3 months)

- [ ] Cross-host health aggregation (§5.9).
- [ ] Configuration validation automation (§5.10).
- [ ] TinyAgents integration: agent calls system monitor `/status`, selects recovery from `runbook.yaml`, executes within sandbox permissions.
- [ ] Scheduled autonomous health sweeps (TinyAgents + cron or systemd timer).
- [ ] Incident replay: agents can replay past incidents from SQLite log to validate recovery procedures.

---

## Summary

**Documentation quality**: High overall. The Feb 2026 consistency audit resolved 27 claims. Remaining drift is concentrated in 3–4 specific port/binding conflicts and one stale systemd unit.

**Agent-readiness**: The governance layer (AGENTS.md, SANDBOX_PERMISSIONS, INCIDENT_FLOW, DOCS_CONTRACT, CHANGE_RULES, CONSISTENCY_DOD) is exceptionally well-developed. The primary gaps are:
1. Machine-readable service data (agents shouldn't parse Markdown tables).
2. Submodule visibility (5 core services invisible in a fresh clone).
3. Automated drift detection (currently manual).
4. System monitor implementation (fully spec'd, zero code).

**Estimated effort to Phase 2 completion**: ~2 weeks of focused work. Phase 3 adds the self-healing nucleus. Phase 4 closes the loop for fully autonomous operation.

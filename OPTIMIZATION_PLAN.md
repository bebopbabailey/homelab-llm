# Studio Scheduling Policy Plan (Live Snapshot Baseline)

## Summary
Implement a uniform Studio scheduling policy with two semantic lanes:
- Inference lane for owned inference services (`com.bebop.mlx-launch`, `com.bebop.optillm-proxy`) so launchd does not treat them as background-throttled.
- Utility/background lane for all non-inference Studio work (deploy, maintenance, ad-hoc) via a single taskpolicy wrapper.
- Add a repo-run audit path to prove label state, lane classification, plist policy keys, and listener/process behavior.

This plan uses **live Studio state as authoritative** (decision locked), **patches plists in place** (decision locked), and **excludes Ollama entirely** (decision locked).

## Current State Summary
- Given inventory (from your prompt): enabled `com.bebop.mlx-launch`, `com.bebop.optillm-proxy`, `com.ollama.server`; several legacy labels disabled.
- Repo discovery:
  - Studio launchd/SSH chokepoints are currently:
    - [platform/ops/scripts/mlxctl](/home/christopherbailey/homelab-llm/platform/ops/scripts/mlxctl)
    - [layer-gateway/optillm-proxy/scripts/deploy_studio.sh](/home/christopherbailey/homelab-llm/layer-gateway/optillm-proxy/scripts/deploy_studio.sh)
  - No version-controlled `.plist` templates exist for `com.bebop.mlx-launch` or `com.bebop.optillm-proxy`.
  - `mlxctl` controls start/stop/restart and writes Omni plists (`com.bebop.mlx-omni.*`), but does not currently template/manage the canonical `com.bebop.mlx-launch` plist.
- Live Studio snapshot (read-only, 2026-02-27):
  - `com.bebop.mlx-launch` and `com.bebop.optillm-proxy` are running.
  - Their installed plists currently have missing `ProcessType`, `Nice`, `LowPriorityIO`, `LowPriorityBackgroundIO`.
  - Port `8100` is currently served by `vllm serve` (child process under `com.bebop.mlx-launch`).

## Target Policy
- Lane 1: **Inference lane** (for owned inference services only).
  - Launchd key: `ProcessType = Interactive`.
  - Do not set background clamps (`LowPriorityIO`, `LowPriorityBackgroundIO`) on these labels.
  - Do not apply positive `Nice` to inference labels.
- Lane 2: **Utility lane** (everything else run on Studio by repo automation).
  - Default execution wrapper uses `taskpolicy` utility/background clamp:
    - `taskpolicy -c utility -d throttle -g throttle -b`
    - plus `nice` for non-inference utility jobs.
  - For any owned non-inference launchd jobs (if/when present), set:
    - `ProcessType = Background`
    - `Nice = 10`
    - `LowPriorityIO = true`
    - `LowPriorityBackgroundIO = true`
- Explicit no-core-pinning stance:
  - No P/E core affinity APIs or pinning in this task.
  - Policy is semantic scheduling/QoS via launchd/taskpolicy and runtime audits.

## Public Interfaces / Contracts Added
- New standard wrapper command (shared by deploy/ops scripts):
  - `platform/ops/scripts/studio_run_utility.sh --host <studio> [--sudo] -- "<command>"`
- New policy enforcer command:
  - `platform/ops/scripts/studio_launchd_policy.py --host <studio> [--check|--apply] [--json]`
- New audit command:
  - `platform/ops/scripts/audit_studio_scheduling.py --host <studio> [--json] [--policy-only]`
- New policy manifest file (single source of scheduling truth):
  - `platform/ops/templates/studio_scheduling_policy.json`

## Plan Steps
1. **Pre-change declaration (required by AGENTS.md)**  
   Goal: enforce Studio scheduling lanes + observability only (no architecture redesign, no Docker changes).  
   Intended files:
   - [platform/ops/templates/studio_scheduling_policy.json](/home/christopherbailey/homelab-llm/platform/ops/templates/studio_scheduling_policy.json) (new)
   - [platform/ops/scripts/studio_run_utility.sh](/home/christopherbailey/homelab-llm/platform/ops/scripts/studio_run_utility.sh) (new)
   - [platform/ops/scripts/studio_launchd_policy.py](/home/christopherbailey/homelab-llm/platform/ops/scripts/studio_launchd_policy.py) (new)
   - [platform/ops/scripts/audit_studio_scheduling.py](/home/christopherbailey/homelab-llm/platform/ops/scripts/audit_studio_scheduling.py) (new)
   - [platform/ops/scripts/mlxctl](/home/christopherbailey/homelab-llm/platform/ops/scripts/mlxctl) (update)
   - [layer-gateway/optillm-proxy/scripts/deploy_studio.sh](/home/christopherbailey/homelab-llm/layer-gateway/optillm-proxy/scripts/deploy_studio.sh) (update)
   - Docs listed in Steps 7–8.
   Verification mode: **FULL** (local deterministic checks + live Studio validation).

2. **Discovery freeze and managed-label allowlist** (depends on 1)  
   Create policy manifest with:
   - `inference_labels`: `com.bebop.mlx-launch`, `com.bebop.optillm-proxy`
   - `background_launchd_labels`: empty initially (explicitly empty)
   - `ignore_labels`: any out-of-scope labels (including Ollama)
   - required key values per lane.  
   This becomes the canonical scheduling contract used by enforcer + audit.

3. **Add single standard utility wrapper** (depends on 2)  
   Implement [studio_run_utility.sh](/home/christopherbailey/homelab-llm/platform/ops/scripts/studio_run_utility.sh):
   - Non-interactive SSH defaults (`BatchMode`, no ControlMaster).
   - Runs remote command under utility clamp (`taskpolicy` flags above).
   - Supports `--sudo` for root-required maintenance operations.
   - Logs command context safely (no secret echo).

4. **Add launchd policy enforcer (patch-in-place)** (depends on 2)  
   Implement [studio_launchd_policy.py](/home/christopherbailey/homelab-llm/platform/ops/scripts/studio_launchd_policy.py):
   - Read manifest.
   - For each managed label, backup installed plist before mutation.
   - Apply required key mutations using remote `plutil`/`PlistBuddy`.
   - Enforce inference labels (`ProcessType=Interactive`, remove background keys).
   - Enforce background labels when list is non-empty.
   - Restart sequence per label:
     - `launchctl bootout system /Library/LaunchDaemons/<label>.plist || true`
     - `launchctl bootstrap system /Library/LaunchDaemons/<label>.plist`
     - `launchctl kickstart -k system/<label>`
   - Provide `--check` mode (no mutation) and `--apply` mode.

5. **Wire utility wrapper into Studio chokepoints** (depends on 3)  
   Update [mlxctl](/home/christopherbailey/homelab-llm/platform/ops/scripts/mlxctl):
   - Route non-inference remote maintenance/deploy operations through the shared wrapper by default.
   - Keep `com.bebop.mlx-launch` lifecycle behavior intact (do not remove or bypass it).
   Update [deploy_studio.sh](/home/christopherbailey/homelab-llm/layer-gateway/optillm-proxy/scripts/deploy_studio.sh):
   - Use shared utility wrapper for pull/sync/bench paths.
   - Keep launchd restart flow.
   - Correct default label drift to `com.bebop.optillm-proxy` (currently mismatched in script docs).

6. **Add audit tool (repo-run from Mini)** (depends on 2, 4, 5)  
   Implement [audit_studio_scheduling.py](/home/christopherbailey/homelab-llm/platform/ops/scripts/audit_studio_scheduling.py) to report:
   - Enabled/disabled status for managed labels.
   - Effective lane classification from manifest.
   - Installed plist key values (`ProcessType`, `Nice`, `LowPriorityIO`, `LowPriorityBackgroundIO`).
   - `launchctl print` status for managed labels.
   - Listener owner on `8100`.
   - CPU/GPU verification command set and rubric for “good”.
   Output:
   - Human table + `--json`.
   - `--policy-only` deterministic mode for CI/local contract checks without Studio SSH.

7. **Documentation placement (DOCS_CONTRACT-aligned, minimal + enforceable)** (depends on 6)  
   Add canonical policy doc:
   - [docs/foundation/studio-scheduling-policy.md](/home/christopherbailey/homelab-llm/docs/foundation/studio-scheduling-policy.md) (new).  
   Update cross-links and operational docs:
   - [TOPOLOGY.md](/home/christopherbailey/homelab-llm/TOPOLOGY.md)
   - [CONSTRAINTS.md](/home/christopherbailey/homelab-llm/CONSTRAINTS.md)
   - [DIAGNOSTICS.md](/home/christopherbailey/homelab-llm/DIAGNOSTICS.md)
   - [docs/foundation/topology.md](/home/christopherbailey/homelab-llm/docs/foundation/topology.md)
   - [docs/foundation/testing.md](/home/christopherbailey/homelab-llm/docs/foundation/testing.md)
   - [docs/PLATFORM_DOSSIER.md](/home/christopherbailey/homelab-llm/docs/PLATFORM_DOSSIER.md)
   Service docs affected by runtime behavior:
   - [layer-gateway/optillm-proxy/SERVICE_SPEC.md](/home/christopherbailey/homelab-llm/layer-gateway/optillm-proxy/SERVICE_SPEC.md)
   - [layer-gateway/optillm-proxy/RUNBOOK.md](/home/christopherbailey/homelab-llm/layer-gateway/optillm-proxy/RUNBOOK.md)
   Planning tracker update:
   - [NOW.md](/home/christopherbailey/homelab-llm/NOW.md)

8. **Submodule coordination and rollout order** (depends on 7)  
   Because `optillm-proxy` is a submodule:
   - Commit submodule file changes in submodule first.
   - Then update monorepo submodule pointer.  
   Rollout order:
   - Apply/check policy on `com.bebop.optillm-proxy` first.
   - Validate.
   - Apply/check policy on `com.bebop.mlx-launch`.
   - Validate.
   - Run full audit and record result.

## Validation & Rollback
- **Deterministic local/CI checks**
  - `bash -n platform/ops/scripts/studio_run_utility.sh`
  - `uv run python -m py_compile platform/ops/scripts/studio_launchd_policy.py platform/ops/scripts/audit_studio_scheduling.py`
  - `uv run python platform/ops/scripts/audit_studio_scheduling.py --policy-only --json`
  - `rg -n "com.bebop.mlx-launch|com.bebop.optillm-proxy|ProcessType" platform/ops/templates/studio_scheduling_policy.json`
- **Manual Studio validation checklist**
  - `uv run python platform/ops/scripts/studio_launchd_policy.py --host studio --check --json`
  - `uv run python platform/ops/scripts/studio_launchd_policy.py --host studio --apply --json`
  - `uv run python platform/ops/scripts/audit_studio_scheduling.py --host studio --json`
  - `ssh studio "sudo plutil -extract ProcessType raw /Library/LaunchDaemons/com.bebop.mlx-launch.plist"`
  - `ssh studio "sudo plutil -extract ProcessType raw /Library/LaunchDaemons/com.bebop.optillm-proxy.plist"`
  - `ssh studio "sudo lsof -nP -iTCP:8100 -sTCP:LISTEN"`
  - CPU/GPU “good” verification commands:
    - `ssh studio "top -l 1 -o cpu -stats pid,command,cpu,mem | head -n 40"`
    - `ssh studio "sudo powermetrics --samplers tasks --show-process-gpu -n 1 | rg -n 'vllm|optillm|GPU|process'"`  
    Good looks like:
    - inference request load is dominated by inference processes,
    - no long-running utility/deploy jobs competing at high priority,
    - audit shows managed labels compliant with lane policy.
- **Rollback**
  - Restore backed up plists per label (`.bak.<timestamp>`).
  - Re-run bootout/bootstrap/kickstart for restored plists.
  - Run audit again; require compliance against pre-change snapshot.
  - If wrapper integration causes issues, temporarily bypass wrapper via env toggle and rerun only check-mode audits.

## Open Risks / Unknowns (and Resolution)
- **No repo-managed canonical plists today**: resolved by patch-in-place enforcer + manifest-backed audit (this task), with optional later template-canon follow-up.
- **Legacy/disabled labels exist on Studio** (`com.bebop.*` variants): resolved by explicit managed-label allowlist and audit visibility; no accidental policy writes to unmanaged labels.
- **Runtime/documentation drift is possible**: resolved by making `--check` audit mandatory before apply and by updating topology/testing/dossier docs in same change.
- **Submodule boundary for optillm-proxy**: resolved by explicit two-commit flow (submodule first, then monorepo pointer).
- **Ollama ambiguity in launchctl inventory**: resolved by explicit out-of-scope exclusion in manifest + docs.

## OS Documentation References
- `launchd.plist(5)` (`ProcessType`, `Nice`, `LowPriorityIO`, `LowPriorityBackgroundIO` semantics): https://www.manpagez.com/man/5/launchd.plist/
- `taskpolicy(8)` (`-c utility`, `-d throttle`, `-g throttle`, `-b`): https://manp.gs/mac/8/taskpolicy
- Apple QoS guidance (scheduler prioritization semantics): https://developer.apple.com/library/archive/documentation/Performance/Conceptual/power_efficiency_guidelines_osx/PrioritizeWorkAtTheTaskLevel.html
- Apple Silicon scheduling/no-core-pinning guidance (macOS scheduler + QoS intent, not core affinity APIs): https://developer.apple.com/videos/play/wwdc2020/10214/?time=223

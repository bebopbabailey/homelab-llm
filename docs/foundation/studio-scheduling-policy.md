# Studio Scheduling Policy (Strict Two-Lane)

## Purpose and scope
This policy standardizes how work is scheduled on the Mac Studio inference host.
It applies only to Studio launchd services we own and transient Studio commands
triggered by this repo's automation.

## Lane contract

### Inference lane (non-background)
Only these labels are inference lane:
- `com.bebop.mlx-lane.8100`
- `com.bebop.mlx-lane.8101`
- `com.bebop.mlx-lane.8102`
- `com.bebop.optillm-proxy`

Required launchd contract:
- `ProcessType = Interactive`
- `Nice` must be absent
- `LowPriorityIO` must be absent
- `LowPriorityBackgroundIO` must be absent

Why: `ProcessType=Interactive` is used intentionally because launchd documents
interactive jobs as having no resource limits; inference must not be
background-throttled.

### Utility lane (transient commands)
All non-inference transient Studio automation (deploy, maintenance, pulls,
builds, checks) must run through:
- `platform/ops/scripts/studio_run_utility.sh`

Wrapper behavior:
- `taskpolicy -c utility -d throttle -g throttle -b`
- plus `nice` adjustment (default `10`)

This keeps transient work from competing with inference.

## Strict mode (fail-closed)
Policy source of truth:
- `platform/ops/templates/studio_scheduling_policy.json`

Rules:
- Owned namespaces are allowlist-enforced (`com.bebop.*`, `com.deploy.*`).
- Any owned Studio label not listed in `managed_labels` or `retired_labels` is
  a violation.
- Default unmanaged handling is `quarantine`:
  - `launchctl disable` + `launchctl bootout` (best effort)
  - move plist from `/Library/LaunchDaemons` to
    `/Library/LaunchDaemons/.quarantine/<label>.plist.<UTC_TIMESTAMP>`
  - never delete plist files

## Tooling
- Policy schema validation:
  - `platform/ops/scripts/validate_studio_policy.py`
- Policy check/apply enforcer:
  - `platform/ops/scripts/enforce_studio_launchd_policy.py`
- Policy and runtime audit:
  - `platform/ops/scripts/audit_studio_scheduling.py`

## Operations

Canonical operator sequence for Studio scheduling checks is maintained in
`docs/foundation/testing.md` under the Studio scheduling section.

### Local deterministic checks (Mini)
```bash
uv run python platform/ops/scripts/validate_studio_policy.py --json
uv run python platform/ops/scripts/audit_studio_scheduling.py --policy-only --json
```

### Remote check (Studio, no mutation)
```bash
uv run python platform/ops/scripts/enforce_studio_launchd_policy.py --host studio --json
uv run python platform/ops/scripts/audit_studio_scheduling.py --host studio --json
```

### Staged apply
1. Apply/check `com.bebop.optillm-proxy` first:
   `uv run python platform/ops/scripts/enforce_studio_launchd_policy.py --host studio --apply --managed-label com.bebop.optillm-proxy --json`
2. Validate health and policy status.
3. Apply/check MLX lane labels second:
   - `uv run python platform/ops/scripts/enforce_studio_launchd_policy.py --host studio --apply --managed-label com.bebop.mlx-lane.8100 --json`
   - `uv run python platform/ops/scripts/enforce_studio_launchd_policy.py --host studio --apply --managed-label com.bebop.mlx-lane.8101 --json`
   - `uv run python platform/ops/scripts/enforce_studio_launchd_policy.py --host studio --apply --managed-label com.bebop.mlx-lane.8102 --json`
4. Run full strict audit and archive output.
5. Optional: enforce retired-label quarantine in apply mode with `--include-retired`.

### Rollback
For each changed managed label:
1. Restore backup plist (`.bak.scheduling-policy.<timestamp>`).
2. `plutil -lint` restored plist.
3. `launchctl bootout` then `bootstrap` then `kickstart`.
4. Re-run strict audit; rollback is complete only when audit passes.

For quarantined unmanaged labels:
1. Move plist back from `/Library/LaunchDaemons/.quarantine/` to
   `/Library/LaunchDaemons/<label>.plist`.
2. `launchctl enable system/<label>`.
3. `launchctl bootstrap` then optional `kickstart`.
4. Re-run strict audit.

## Adding a new Studio service
1. Confirm the service is truly persistent and launchd-managed.
2. Add label to policy manifest with explicit lane and plist path.
3. Define required/forbidden keys by lane (or reuse lane defaults).
4. Run validator + policy-only audit.
5. Run remote check/apply and strict audit.
6. Update service docs (`SERVICE_SPEC.md`, `RUNBOOK.md`) and platform docs.

## Observability checklist
- `launchctl print-disabled system` for enabled/disabled label state.
- `launchctl print system/<label>` for loaded/running state.
- robust plist key evidence:
  - `sudo plutil -convert json -o - /Library/LaunchDaemons/<label>.plist`
  - fallback: `sudo /usr/libexec/PlistBuddy -c "Print :<Key>" /Library/LaunchDaemons/<label>.plist`
  - quick human spot-check: `sudo plutil -p /Library/LaunchDaemons/<label>.plist | rg 'ProcessType|Nice|LowPriorityIO|LowPriorityBackgroundIO'`
- `lsof -nP -iTCP:8100-8102 -sTCP:LISTEN` + `ps` ancestry for listener ownership.
- `top` and `powermetrics` spot checks for utility-vs-inference behavior.

## References
- `launchd.plist(5)` (ProcessType/Nice/LowPriority* semantics):
  - https://www.manpagez.com/man/5/launchd.plist/
- `taskpolicy(8)` (utility/background class, throttle, inheritance):
  - https://manp.gs/mac/8/taskpolicy
- Apple QoS and scheduling intent guidance (priority semantics, not core pinning):
  - https://developer.apple.com/library/archive/documentation/Performance/Conceptual/power_efficiency_guidelines_osx/PrioritizeWorkAtTheTaskLevel.html
  - https://developer.apple.com/videos/play/wwdc2020/10214/

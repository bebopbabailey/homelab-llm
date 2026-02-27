# 2026-02-27 — Studio SSH lock/reboot blockage and harness hardening

## Summary
Repeated `ssh studio` failures during vLLM-metal tuning were not a single SSH config bug.
They were a combined failure mode:
- host instability/reboots under load,
- post-reboot lock state with FileVault enabled,
- and brittle multiplexed SSH sessions during churn.

We hardened both the client path and the tuning harness so failures classify clearly as `LOCKED`, `AUTH_REJECTED`, `HOST_DOWN`, or `TRANSPORT_ERROR`.

## High-signal findings
- `studio` reboot history showed multiple recent reboots in short succession.
- panic reports exist in `/Library/Logs/DiagnosticReports/` including watchdog/panic reset strings.
- `FileVault is On` on `studio`; after some reboot sequences, remote sessions can fail until local unlock/login is completed.
- SSH daemon settings were already key-only and correct (`PubkeyAuthentication yes`, password/kbdinteractive disabled).
- The local `studio` SSH profile on Mini still used multiplexing (`ControlMaster auto`), which increased fragility (`broken pipe` style failures) during host churn.

## Changes made
1. Mini SSH client profile for `studio`
- Switched to deterministic non-multiplexed mode in `~/.ssh/config`:
  - `ControlMaster no`
  - `ControlPath none`
  - `ControlPersist no`

2. Tuning harness hardening
- Updated `layer-inference/optillm-local/scripts/run_vllm_metal_lane_tuning.py`:
  - SSH calls now enforce non-multiplexed options.
  - Added structured timeout handling in command execution.
  - Added SSH preflight gate before each candidate.
  - Added classification for host/auth/lock transport failures.
  - Added per-candidate report fields:
    - `preflight_ok`
    - `host_state`
    - `ssh_error_class`

3. Operational runbook update
- Added preflight + lock-state decision section to `layer-inference/RUNBOOK.md`.

## Current policy
- Keep FileVault enabled on `studio` (security-first default).
- Treat post-reboot lock state as an explicit operational step: local unlock before long automated sweeps.

## Follow-up
- Run a focused `metal-test-deep` (`8122`) recheck on `max_model_len=65536` after a stable preflight window.
- If host reboot/panic recurs under the same load pattern, classify as host stability boundary (not purely SSH).

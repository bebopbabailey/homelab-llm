# 2026-04-16 — Joint Qwen-Agent trial prep

## Summary
- Prepared a small SWE-bench-style Python micro bugfix repo for the first joint
  OpenHands/Codex trial.
- Wrote explicit operator instructions into the OpenHands runbook for driving
  the OpenHands UI against the direct `qwen-agent-proxy` path.
- Chose the direct sidecar path as the official provider contract for the trial:
  `http://host.docker.internal:4021/v1` with model
  `qwen-agent-coder-next-shadow`.

## Benchmark repo
- Path:
  `/home/christopherbailey/openhands-experimental/phase-a-workspace/swebench-micro-001-config-merge`
- Contract:
  - stdlib-only Python repo
  - one real bug in config merging
  - failing `unittest` baseline
  - clean reset point saved as `benchmark-baseline`
  - current baseline commit: `41495f6`

## Task definition
- Fix the config merge bug so nested overrides merge recursively instead of
  replacing whole nested dictionaries.
- Do not mutate the input base config.
- Validate with:
  `python3 -m unittest`

## Intended comparison flow
1. Run OpenHands on the benchmark repo from the failing baseline.
2. Save summary, diff, and test output.
3. Reset the repo to `benchmark-baseline`.
4. Run Codex on the exact same task.

## Notes
- No task execution was performed in this prep slice.
- The existing trivial `scratch-repo` remains untouched.

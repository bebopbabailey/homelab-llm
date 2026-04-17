# Tasks: OpenHands (Mini Phase A)

- [x] Add the Phase A docs bundle and canonical doc updates.
- [x] Promote OpenHands to a repo-managed `systemd` + Docker runtime on `127.0.0.1:4031`.
- [x] Verify the managed runtime on `127.0.0.1:4031` and `https://hands.tailfd1400.ts.net/`.
- [ ] Verify only the disposable workspace is mounted into `/workspace` during a
  sandboxed task run.
- [x] Prepare one scratch-repo target with a failing stdlib `unittest`.
- [x] Prepare one SWE-bench-style micro bugfix repo with a clean reset point for
  the joint Qwen-Agent trial.
- [ ] Run one OpenHands trial loop on the micro bugfix repo:
  `plan -> patch -> validate -> summarize`.
- [ ] Reset the benchmark repo and run the matching Codex loop on the same task.
- [x] Keep LiteLLM handoff documented but unimplemented until policy is ready.

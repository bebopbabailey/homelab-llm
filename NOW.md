# NOW

Active
- Harden repo lane lifecycle so `start_effort.py` is transactional,
  `closeout_effort.py` can land a finished lane, and stale metadata becomes
  visible
- Add deterministic submodule pin diagnostics so local-only gitlink pins fail
  cleanly instead of leaving half-broken linked worktrees
- Align the coding-agent docs, tests, and repo-hygiene workflow with the full
  start/closeout lifecycle


NEXT UP
- Re-test the docs hardening workflow from a freshly scoped linked worktree
  after the lifecycle hardening lands.

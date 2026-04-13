# NOW

Active
- Move the next edge service batch into live `services/` paths.
- Retire `optillm-local` into `experiments/legacy/` without archiving it out of
  the repo.
- Update registry, repo-owned units, docs, and path-sensitive tests so the
  mixed-root migration remains deterministic.

NEXT UP
- Land this batch, then plan the final control-plane and data moves around
  `litellm-orch`, `optillm-proxy`, and `vector-db`.

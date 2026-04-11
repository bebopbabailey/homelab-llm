# OptiLLM Ensembles (v0 Matrix)

This matrix reflects the **current, wired** OptiLLM proxy handles. It is intentionally
minimal while we validate end-to-end routing and default MLX boot behavior.

## Default MLX Ensemble (boot)
- _None currently registered._ Pending new MLX model set.

## Active OptiLLM Handles (router-only)
- _None currently registered._ Handles will be reintroduced once MLX models are staged.

## Notes
- Handles are the **user-facing entry points**; techniques are selected per-request
  via `optillm_approach`.
- We use **router-only** selectors by default; the router decides any heavier technique.
- This matrix will be updated after the new MLX models are downloaded and registered.

# 2026-04-19 — Qwen production retirement and GPT MLX shadow probe

## Summary
- Retired the Qwen/vLLM `main` lane from the active production surface.
- Removed active LiteLLM routing and production-facing docs that still treated
  Qwen as a live public lane.
- Repointed the Studio OptiLLM proxy from `main` to `deep`.
- Disabled the Mini `qwen-agent-proxy.service`.
- Retired the Studio `8101` Qwen production lane through the supported
  `mlxctl unload 8101` path, using a temporary repo-rooted Studio bundle to
  avoid the bare `/Users/thestudio/bin/mlxctl` import-time repo-root bug.
- Probed whether LM Studio could host a separate GPT MLX shadow server on
  `8130` while keeping the live `8126` GPT service up.

## What changed
- LiteLLM active aliases are now:
  - `fast`
  - `deep`
  - `code-reasoning`
  - utility aliases only (`task-transcribe`, `task-transcribe-vivid`,
    `task-json`, `chatgpt-5`)
- `main` and `code-qwen-agent` are removed from the active `/v1/models` surface.
- `fast -> deep` is now the active resilience baseline.
- Studio OptiLLM now runs with `--model deep`.
- Studio `8101` is now idle and disabled.

## Runtime proof
- Mini LiteLLM:
  - `/health/readiness` returned healthy after regenerating Prisma client
    artifacts in the worktree venv.
  - `/v1/models` no longer exposed `main` or `code-qwen-agent`.
  - a mock fallback request against `fast` returned the `deep` backend model id,
    proving `fast -> deep`.
- Studio OptiLLM:
  - launchd `com.bebop.optillm-proxy` now runs `--model deep`.
  - `/v1/models` on `4020` exposes only the GPT-family surface.
- Studio MLX retirement:
  - `mlxctl` status shows `8101` as `idle`, `listener_visible=false`,
    `launchd_disabled=true`.

## GPT MLX shadow result
- The current LM Studio headless control surface did **not** provide an
  isolated second server.
- Starting a shadow server on `8130` under a separate throwaway `HOME` changed
  the global server from `8126` to `8130`.
- Restoring `8126` immediately returned the incumbent GPT service to normal.
- Result: there is **no active LM Studio + MLX GPT candidate service** after
  this effort. A later MLX GPT effort needs a different isolation approach or a
  prove-then-cutover plan that accepts temporary displacement of the incumbent.

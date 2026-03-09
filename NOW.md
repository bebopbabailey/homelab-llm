# NOW

Active
- OptiLLM drift cleanup + runtime lock:
  - Remove deploy-time patching and git-sourced OptiLLM from `layer-gateway/optillm-proxy`.
  - Make Studio deploy exact-SHA and reproducible with `uv sync --frozen`.
  - Add runtime lock, validator, and canon docs for the current LiteLLM + vLLM-metal baseline.

NEXT UP
- Finish the runtime-lock/doc pass after the optillm-proxy drift cleanup validates on Studio.

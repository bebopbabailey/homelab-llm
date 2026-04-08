# NOW

Active
- Repair Mini LiteLLM Prisma/schema drift so `/key/generate` and `/v1/mcp/*`
  work again on the stable `1.83.4` runtime
- Keep the accepted gateway contract aligned to verified stable runtime truth:
  local canonical trio only, no broken ChatGPT public aliases
- Fail fast on future LiteLLM schema drift through the repo-managed systemd unit


NEXT UP
- Re-test ChatGPT and shared LiteLLM MCP behavior on a LiteLLM build that
  actually passes Mini runtime validation, then decide whether those lanes can
  re-enter the public Open WebUI contract.

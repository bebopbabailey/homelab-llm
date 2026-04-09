# AGENTS — llama-cpp-server

## Scope
- Repo-owned GPT serving boundary for the active `llmster`/llama.cpp lanes on
  the Studio.

## Read First
- `SERVICE_SPEC.md`
- `CONSTRAINTS.md`
- `RUNBOOK.md`

## Runtime Reality
- `fast` and `deep` are currently live on the Studio `llmster` service on
  `8126`.
- Public clients must continue to call LiteLLM only.

## Change Guardrails
- Keep `llmster` explicit in the architecture for GPT lanes.
- Do not document fallback or rollback paths that depend on retired `8100` or
  `8102` GPT lanes.
- Do not introduce direct client-to-Studio GPT paths.

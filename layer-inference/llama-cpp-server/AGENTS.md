# AGENTS — llama-cpp-server

## Scope
- Repo-owned GPT serving boundary for future `llmster`/llama.cpp lanes on the Studio.
- This service is documentation-first until the rollout slices explicitly activate it.

## Read First
- `SERVICE_SPEC.md`
- `CONSTRAINTS.md`
- `RUNBOOK.md`

## Runtime Reality
- `fast` is currently live on the Studio `llmster` service on `8126`.
- Public clients must continue to call LiteLLM only.
- Approved rollout target is a shared Studio listener on `192.168.1.72:8126`
  with loaded identifiers for `llmster-gpt-oss-20b-mxfp4-gguf` and later
  `llmster-gpt-oss-120b-mxfp4-gguf`.

## Change Guardrails
- Keep `llmster` explicit in the architecture for GPT lanes.
- Do not claim this service is live without a launched label, validation output,
  and canonical doc updates.
- Do not introduce direct client-to-Studio GPT paths.

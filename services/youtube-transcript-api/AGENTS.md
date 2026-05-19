# Agent Guidance: youtube-transcript-api

## Scope
Keep this service as the localhost-only OpenAI-compatible acquisition boundary
for source-faithful YouTube timed text.

## Read First
- `SERVICE_SPEC.md`
- `CONSTRAINTS.md`
- `RUNBOOK.md`

## Guardrails
- Do not add summarization, cleanup, translation, vector indexing, or follow-up
  chat behavior here.
- Do not expose this service directly on LAN; LiteLLM is the public route.
- Preserve plain transcript text as the default chat-completion assistant
  content.

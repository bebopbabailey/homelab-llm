# Agent Guidance: websearch-orch

## Scope
- Localhost-only hygiene proxy for Open WebUI web search.
- Optional local semantic reranking (fail-open).
- Keep behavior deterministic and reversible.

## Runtime
- Managed by systemd: `/etc/systemd/system/websearch-orch.service`
- Env: `/etc/homelab-llm/websearch-orch.env`

## Guardrails
- Do not expose externally.
- Preserve SearXNG-compatible JSON response shape for Open WebUI.

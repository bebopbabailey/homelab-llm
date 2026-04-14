# NOW

Active
- Shift the Mini gateway and Open WebUI human-chat path to a responses-first
  LiteLLM contract.
- Keep `chatgpt-5` live as the subscription-backed ChatGPT lane, but enforce it
  as responses-only at the gateway.
- Revalidate `main`, `deep`, `fast`, and `chatgpt-5` through `/v1/responses`,
  then close docs drift against the accepted contract.

NEXT UP
- If Open WebUI cannot stably consume the responses-first LiteLLM connection,
  isolate the exact connection-setting gap and stage the narrowest possible UI
  config follow-up.

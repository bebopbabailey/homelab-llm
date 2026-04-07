# NOW

Active
- Add an additive LiteLLM ChatGPT subscription lane for Open WebUI through the existing LiteLLM `/v1` gateway
- Keep the local canonical trio `fast`, `main`, and `deep` unchanged while exposing opt-in cloud aliases
- Upgrade `layer-gateway/litellm-orch` to a LiteLLM release that supports the `chatgpt/...` provider route


NEXT UP
- Validate the new ChatGPT aliases in the dedicated worktree, then promote and smoke-test them on the live Mini runtime.

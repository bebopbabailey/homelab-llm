# NOW

Active
- Restore `litellm-orch` on the Mini after the service-root move stranded the
  installed systemd unit and local runtime artifacts.
- Reintroduce operator-only ChatGPT aliases at the LiteLLM gateway without
  changing the public `main` / `deep` / `fast` contract.
- Revalidate the recovered LiteLLM runtime, then close any remaining docs drift
  against the accepted gateway contract.

NEXT UP
- If the pinned LiteLLM baseline still fails real `chatgpt/...` inference after
  recovery, stage a narrow package upgrade for `services/litellm-orch`.

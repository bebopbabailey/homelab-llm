# NOW

Active
- Move the experimental `chatgpt-5` lane off the raw ChatGPT backend and onto
  the Mini-local `ccproxy-api` Codex sidecar.
- Restore Open WebUI to a Chat Completions-first LiteLLM path for human chat.
- Revalidate the `chatgpt-5` lane in Open WebUI and codify the new experimental
  localhost-sidecar contract.

NEXT UP
- If the Codex-backed sidecar still shows behavioral gaps in Open WebUI, lock
  the exact unsupported feature set and narrow the lane contract further.

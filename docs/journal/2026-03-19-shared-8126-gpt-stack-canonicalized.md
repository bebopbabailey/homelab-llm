# 2026-03-19 — Shared `8126` GPT stack canonicalized

## Summary
- Replaced the live Studio `8126` launchd contract with the repo-owned thin
  daemon-aware wrapper.
- Made the owned `8126` service auto-load both canonical GPT models:
  `llmster-gpt-oss-20b-mxfp4-gguf` and
  `llmster-gpt-oss-120b-mxfp4-gguf`.
- Retired the temporary LiteLLM alias `deep-canary`.
- Codified `fast` and `deep` as the canonical shared GPT runtime stack on
  `8126`.

## Service contract change
- Previous live drift:
  - direct `/Users/thestudio/.lmstudio/bin/lms server start --bind 192.168.1.72 --port 8126`
  - no deployed wrapper script on Studio
  - no explicit repo-owned deep auto-load on restart
- New canonical contract:
  - repo-owned `llmster_ensure_server.py`
  - pinned versioned LM Studio binary
  - explicit dual `--load-spec`
  - restart-proof shared residency for `fast` + `deep`

## Validation
- Studio `8126` restarted from the new owned plist contract.
- `lms ps --json` showed both canonical GPT identifiers after restart.
- `8126 /v1/models` showed both canonical GPT identifiers after restart.
- Public LiteLLM `/v1/models` returned the stable public aliases:
  - `deep`
  - `fast`
  - `main`
- Public `fast` and `deep` both answered cleanly after the restart-proof change.

## Locked public contract
- LiteLLM remains the public control plane.
- Public GPT aliases remain:
  - `fast`
  - `deep`
- Public GPT lanes remain Chat Completions-first.
- `deep` constrained tool contract remains:
  - `required` strong
  - named forced-tool choice unsupported and non-blocking on the current
    backend path
- No active temporary GPT rollout aliases remain in the public gateway surface.

## Follow-up
- Observe the shared `8126` dual-load posture.
- Retire old MLX GPT rollback lanes and stale GPT artifacts after the
  follow-up cleanup window if no regression appears.

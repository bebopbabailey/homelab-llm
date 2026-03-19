# MAIN 8101 Closeout Report — 2026-03-18

## Executive decision
`main` is accepted as the canonical public lane on Studio `8101`, and the `main` backend-hardening project is closed.

This report records the final accepted `main` contract, the known accepted limitations, the dormant recovery posture for legacy shadow/fallback work, and the transition of active backend effort to GPT-family `llmster` work for `fast` and `deep`.

## Final accepted public `main` contract
`main` is accepted for:
- non-stream `tool_choice="auto"`
- long-context sanity
- bounded concurrency
- branch-style concurrency and suitability

`main` remains the public canary lane on canonical Studio `8101`.

## Accepted limitations
The following are accepted limitations on the current runtime and are not active closeout blockers:
- structured outputs are outside the accepted public `main` contract
- `tool_choice="required"` is unsupported and non-blocking
- named forced-tool choice is unsupported and non-blocking

## Structured-output disposition
The final structured-output protocol validation showed that structured outputs remain broken on canonical `8101` for the current non-stream request paths that were tested.

Validated failure modes:
- direct OpenAI-compatible `response_format` failed
- direct vLLM-native `structured_outputs.json` failed
- LiteLLM `response_format` failed identically

Shared observed failure:
- assistant `content` returned `{"error":"No schema provided to match against."}`

That result is preserved as accepted backend truth, but it is no longer treated as an active blocker for closing `main`.

Primary evidence:
- [MAIN_8101_STRUCTURED_OUTPUT_PROTOCOL_VALIDATION_REPORT_2026-03-18.md](/home/christopherbailey/homelab-llm/MAIN_8101_STRUCTURED_OUTPUT_PROTOCOL_VALIDATION_REPORT_2026-03-18.md)
- [2026-03-18-main-8101-structured-output-protocol-validation.md](/home/christopherbailey/homelab-llm/docs/journal/2026-03-18-main-8101-structured-output-protocol-validation.md)

## Tool-use disposition
`main` is accepted for non-stream `tool_choice="auto"` with the existing narrow LiteLLM `main`-only post-call cleanup for recoverable raw `<tool_call>` output.

Primary evidence:
- [2026-03-18-qwen-main-acceptance-codified-with-posthook.md](/home/christopherbailey/homelab-llm/docs/journal/2026-03-18-qwen-main-acceptance-codified-with-posthook.md)

## Dormant recovery posture
Legacy `main`/helper shadow and fallback concepts are preserved only as dormant recovery metadata and approved recovery space:
- `8123`
- `8124`
- `8125`

These are not part of the active public alias surface and are no longer part of the active rollout narrative. Historical reports are retained for recovery context and review, not as an instruction to continue rollout work there.

## Transition to active work
With `main` closed, active backend effort moves fully to GPT-family `llmster` work:
- `fast` is live on `8126`
- `deep` is the next rollout target

The next active program is GPT-lane hardening, observation, and `deep` migration. Any future `main` runtime investigation would require a new explicitly named project rather than reopening this one by default.

## Review set
Recommended review order for another associate:
1. [MAIN_8101_STRUCTURED_OUTPUT_PROTOCOL_VALIDATION_REPORT_2026-03-18.md](/home/christopherbailey/homelab-llm/MAIN_8101_STRUCTURED_OUTPUT_PROTOCOL_VALIDATION_REPORT_2026-03-18.md)
2. [2026-03-18-main-8101-structured-output-protocol-validation.md](/home/christopherbailey/homelab-llm/docs/journal/2026-03-18-main-8101-structured-output-protocol-validation.md)
3. [2026-03-18-qwen-main-acceptance-codified-with-posthook.md](/home/christopherbailey/homelab-llm/docs/journal/2026-03-18-qwen-main-acceptance-codified-with-posthook.md)
4. [2026-03-18-main-closeout-and-gpt-transition.md](/home/christopherbailey/homelab-llm/docs/journal/2026-03-18-main-closeout-and-gpt-transition.md)

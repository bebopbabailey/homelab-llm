# NOW

Active
- Run the bounded GPT-OSS 20B LiteLLM day-2 operations confidence soak on the kept experimental lane:
  - prove `metal-test-gptoss20b-enforce` stays stable and observable over a modest sequence of spaced requests
  - confirm ordinary text, synthesis, noop-tool, and retrieval/follow-up flows stay clean under the guardrail
  - classify whether the lane is ready for a canonical-`fast` promotion-planning pass

NEXT UP
- Keep the lane experimental only unless the soak is clean enough to justify designing a controlled promotion plan toward canonical `fast`.

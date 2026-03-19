# 2026-03-18 — Qwen `main` auto-tool path hardened on `8101` with narrow LiteLLM post-call cleanup

## Summary
- Re-validated canonical `main` on Studio `8101` against the narrowed public
  hardening focus:
  - non-stream `tool_choice="auto"`
  - long-context sanity
  - concurrency
- Direct `8101` results split cleanly:
  - repo-standard noop `tool_choice="auto"` probe: native PASS (`10/10`)
  - stricter single-tool argument-bearing `tool_choice="auto"` probe: semantic
    but raw/recoverable (`10/10`)
- Kept the locked runtime shape unchanged:
  - `hermes`
  - no forced `xgrammar`
  - no explicit chat template
  - no reasoning parser
  - `--generation-config vllm`
  - `--max-model-len 32768`
- Added a narrow LiteLLM post-call success hook for `main` only, non-stream
  only, `tool_choice="auto"` only, and only for the strict single-block raw
  `<tool_call>...</tool_call>` recovery case.
- Confirmed that `tool_choice="required"` and named forced-tool semantics remain
  unsupported and non-blocking for public `main`.
- Re-checked the exact `response_format.json_schema` structured-output request
  shape and found that it is still failing on the current backend path under
  both direct and LiteLLM probes, so full `main` acceptance was not truthfully
  codified in this pass.

## Direct backend results
- `/v1/models`: PASS
- noop `tool_choice="auto"`: native PASS (`10/10`)
- argument-bearing single-tool `tool_choice="auto"`: semantic but
  raw/recoverable (`10/10`)
- long-context sanity: PASS (`3/3`)
- generic concurrency: stable recheck in this slice with zero crash, listener
  loss, `5xx`, or timeout
- shared-prefix branch probe: stable recheck in this slice with zero crash,
  listener loss, `5xx`, or timeout
- `response_format.json_schema` structured outputs: FAIL on the current backend
  path (`"No schema provided to match against."`)

## Gateway contract result
- LiteLLM `main` now preserves the clean public client contract for non-stream
  `tool_choice="auto"` on both the simple noop and stricter argument-bearing
  single-tool probes.
- the final live integration uses a narrow `post_call` guardrail on LiteLLM's
  success-hook path because a plain callback return did not affect
  client-visible responses on this LiteLLM build
- The narrow post-call hook is not a generic parser replacement:
  - it does not touch streaming
  - it does not touch `fast` or `deep`
  - it does not touch forced-tool semantics

## Contract decision
- Public `main` auto-tool hardening is accepted on the basis of:
  - non-stream auto tool use
  - long-context sanity
  - bounded concurrency
  - shared-prefix branch-style concurrency
- `tool_choice="required"` is not a blocker
- named forced-tool choice is not a blocker
- exact `response_format.json_schema` structured outputs remain an open
  hardening item before full contract codification

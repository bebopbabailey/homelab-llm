# 2026-03-18 — Canonical `8101` structured-output protocol validation

## Summary
- This entry closes the open structured-output question left in
  `2026-03-18-qwen-main-acceptance-codified-with-posthook.md`.
- Ran the narrow non-stream structured-output validation slice against canonical
  `main` on Studio `8101` with no backend flag changes, no alias changes, and
  no tool-work expansion.
- Tested three paths with the same minimal schema and prompt:
  - direct `8101` exact documented OpenAI-compatible
    `response_format.type="json_schema"` shape
  - direct `8101` vLLM-native `structured_outputs.json` shape
  - LiteLLM `main` with the same exact documented `response_format` shape
- All three paths failed the same way:
  - HTTP status stayed `200`
  - assistant `message.content` was the JSON string
    `{"error":"No schema provided to match against."}`
  - the response did not satisfy the requested schema
- A direct `8101` tie-breaker rerun with `strict: true` under
  `response_format.json_schema` produced the same result.

## Direct `8101` results
- `/v1/models`: PASS
- exact documented `response_format.json_schema` path: FAIL (`0/5`)
- exact vLLM-native `structured_outputs.json` path: FAIL (`0/5`)
- tie-breaker `response_format.json_schema.strict=true`: FAIL (`0/2`)

Representative direct response shape:
```json
{
  "choices": [
    {
      "message": {
        "role": "assistant",
        "content": "{\n  \"error\": \"No schema provided to match against.\"\n}"
      },
      "finish_reason": "stop"
    }
  ]
}
```

Interpretation:
- this is not an HTTP transport failure
- this is not a LiteLLM-only failure
- this is a semantic structured-output failure on the current backend path

## LiteLLM `main` results
- readiness: PASS
- `/v1/models`: PASS
- exact documented `response_format.json_schema` path through LiteLLM: FAIL
  (`0/5`)
- LiteLLM reproduced the same assistant content error string seen directly on
  `8101`

Interpretation:
- the current LiteLLM seam is not introducing a separate structured-output
  failure mode for this request family
- the existing `main` post-call cleanup hook is not the issue here; this pass
  stayed non-streaming and did not rely on tool-call repair behavior

## Backend log evidence
- Studio `vllm-8101.log` during the direct probes showed repeated
  `backend_xgrammar.py` FSM rejection errors and `scheduler.py` grammar
  rejection warnings while the API still returned `200`
- that matches the client-visible result: the backend emitted an error object as
  assistant content instead of satisfying the requested schema

## Decision
- The structured-output question for canonical `main` on `8101` is settled for
  the current runtime:
  - it is not just the OpenAI-compatible `response_format` wrapper
  - it is not just LiteLLM
  - both exact documented direct request paths currently fail on the backend
- Public `main` should therefore continue to exclude structured outputs from the
  accepted contract until a separate backend-specific debugging slice proves a
  fix.

## Narrow next step
- If structured outputs need to be pursued further for `main`, the next slice
  should be backend-specific evidence gathering on the current `8101` runtime.
- It should not reopen alias topology, parser choice, fallback architecture, or
  GPT-lane work.

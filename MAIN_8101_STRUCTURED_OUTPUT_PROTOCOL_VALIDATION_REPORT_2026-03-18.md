# Canonical `main` `8101` Structured-Output Protocol Validation Report

Date: `2026-03-18`
Scope: narrow protocol-validation pass only
Host path under test: Studio `192.168.1.72:8101`
Gateway comparison path: Mini LiteLLM `127.0.0.1:4000` -> `main`

## Executive Verdict
Structured outputs are currently broken on canonical `main` for the present
non-stream request families on `8101`.

This pass ruled out the two narrower theories that were still open:
- it is not only the OpenAI-compatible `response_format` wrapper
- it is not only the LiteLLM seam

Direct `8101` failed for both:
- exact documented OpenAI-compatible `response_format.type="json_schema"`
- exact vLLM-native `structured_outputs.json`

LiteLLM `main` reproduced the same failure text when given the same exact
documented `response_format` shape.

The shared failure mode was:
- HTTP status `200`
- assistant `message.content` containing:
  `{"error":"No schema provided to match against."}`
- schema validation failure on the caller side

The direct `strict: true` tie-breaker produced the same result.

## Objective
The pass was intentionally narrow:
- determine whether structured outputs on canonical `8101` are actually broken
- or determine whether the prior failure came from sending the wrong request
  shape

Out of scope:
- backend architecture changes
- alias changes
- parser changes
- tool-use changes
- FAST / DEEP / HELPER / `boost*`
- fallback implementation

## Current Runtime Truth Preserved
Nothing about backend architecture changed in this pass.

Preserved facts:
- canonical `main` remains on Studio `8101`
- `main` is still hardened enough for non-stream auto tool use
- LiteLLM `main` post-call cleanup for recoverable raw `<tool_call>` output is
  still live and was not part of this failure mode
- no backend flags were changed
- no service restarts or alias rewires were performed

## Request Shapes Tested
The pass used one minimal prompt and one minimal schema across all probes so the
only moving part was protocol shape.

Shared prompt:
```json
[
  {
    "role": "user",
    "content": "Return a JSON object that matches the schema exactly."
  }
]
```

Shared schema:
```json
{
  "type": "object",
  "properties": {
    "status": { "type": "string" }
  },
  "required": ["status"],
  "additionalProperties": false
}
```

### 1. Direct `8101` exact documented OpenAI-compatible `response_format`
Endpoint:
- `POST http://192.168.1.72:8101/v1/chat/completions`

Payload:
```json
{
  "model": "mlx-qwen3-next-80b-mxfp4-a3b-instruct",
  "messages": [
    {
      "role": "user",
      "content": "Return a JSON object that matches the schema exactly."
    }
  ],
  "response_format": {
    "type": "json_schema",
    "json_schema": {
      "name": "status_payload",
      "schema": {
        "type": "object",
        "properties": {
          "status": { "type": "string" }
        },
        "required": ["status"],
        "additionalProperties": false
      }
    }
  },
  "temperature": 0,
  "max_tokens": 128,
  "stream": false
}
```

### 2. Direct `8101` exact vLLM-native `structured_outputs.json`
Endpoint:
- `POST http://192.168.1.72:8101/v1/chat/completions`

Payload:
```json
{
  "model": "mlx-qwen3-next-80b-mxfp4-a3b-instruct",
  "messages": [
    {
      "role": "user",
      "content": "Return a JSON object that matches the schema exactly."
    }
  ],
  "structured_outputs": {
    "json": {
      "type": "object",
      "properties": {
        "status": { "type": "string" }
      },
      "required": ["status"],
      "additionalProperties": false
    }
  },
  "temperature": 0,
  "max_tokens": 128,
  "stream": false
}
```

### 3. LiteLLM `main` with the same exact OpenAI-compatible `response_format`
Endpoint:
- `POST http://127.0.0.1:4000/v1/chat/completions`

Payload:
```json
{
  "model": "main",
  "messages": [
    {
      "role": "user",
      "content": "Return a JSON object that matches the schema exactly."
    }
  ],
  "response_format": {
    "type": "json_schema",
    "json_schema": {
      "name": "status_payload",
      "schema": {
        "type": "object",
        "properties": {
          "status": { "type": "string" }
        },
        "required": ["status"],
        "additionalProperties": false
      }
    }
  },
  "temperature": 0,
  "max_tokens": 128,
  "stream": false
}
```

### 4. Tie-breaker only
Because older repo checks had included `strict: true`, one direct tie-breaker
rerun was performed with:
- the same direct `response_format` payload
- plus `response_format.json_schema.strict = true`

This was diagnostic only, not the primary truth probe.

## Validation Method
Run counts:
- direct `response_format`: `5`
- direct `structured_outputs.json`: `5`
- LiteLLM `response_format`: `5`
- direct `strict: true` tie-breaker: `2`

For each attempt, the pass captured:
- HTTP status
- raw response body
- assistant message content
- local JSON parse result
- local schema validation result

Success requirement for any structured-output path:
- HTTP `200`
- assistant content parses as JSON
- parsed content matches the requested schema
- zero timeout
- zero `5xx`

## Results
### Direct `8101` exact documented `response_format`
Result:
- `0/5` valid schema matches
- all `5/5` requests returned HTTP `200`
- all `5/5` responses returned assistant content:
  `{"error":"No schema provided to match against."}`

Representative body:
```json
{
  "id": "chatcmpl-aadab8c75f9272cc",
  "object": "chat.completion",
  "model": "mlx-qwen3-next-80b-mxfp4-a3b-instruct",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "{\n  \"error\": \"No schema provided to match against.\"\n}",
        "tool_calls": []
      },
      "finish_reason": "stop"
    }
  ]
}
```

Classification:
- semantic failure
- not an HTTP transport failure

### Direct `8101` exact `structured_outputs.json`
Result:
- `0/5` valid schema matches
- all `5/5` requests returned HTTP `200`
- all `5/5` responses returned the same assistant content:
  `{"error":"No schema provided to match against."}`

Classification:
- semantic failure
- same visible failure mode as the direct `response_format` path

### LiteLLM `main` exact documented `response_format`
Result:
- `0/5` valid schema matches
- all `5/5` requests returned HTTP `200`
- all `5/5` responses returned the same assistant content:
  `{"error":"No schema provided to match against."}`

Representative body:
```json
{
  "id": "chatcmpl-a783ee2b6ac4d3e1",
  "object": "chat.completion",
  "model": "mlx-qwen3-next-80b-mxfp4-a3b-instruct",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "{\n  \"error\": \"No schema provided to match against.\"\n}"
      },
      "finish_reason": "stop"
    }
  ]
}
```

Classification:
- same semantic failure reproduced through the gateway
- not a separate LiteLLM-only transport issue

### Direct `strict: true` tie-breaker
Result:
- `0/2`
- same assistant content error

Interpretation:
- the currently failing behavior is not explained by the presence or absence of
  `strict: true`

## Backend Log Findings
Studio `vllm-8101.log` showed repeated structured-decoding errors during the
direct probes:
- `backend_xgrammar.py` FSM advance failures
- scheduler grammar rejection warnings

Important detail:
- the API still returned HTTP `200`
- the backend emitted an error object as assistant content instead of enforcing
  the requested schema

That aligns with the client-visible behavior from both direct `8101` and
LiteLLM.

## Isolation Outcome
This pass successfully isolated the failing seam.

What was ruled out:
- “the prior request shape was only wrong because of the OpenAI wrapper”
- “LiteLLM is the only broken layer”

What remains true:
- both exact documented direct request families currently fail on the backend
- LiteLLM reproduces the same failure text, rather than introducing a distinct
  failure mode

So the current issue is best described as:
- a backend-path structured-output failure on canonical `8101`
- not merely an OpenAI-compatible wrapper mismatch
- not merely a LiteLLM passthrough bug

## Contract Implication
Structured outputs should remain out of the accepted public `main` contract for
the current runtime.

That means the current accepted `main` contract remains centered on:
- non-stream auto tool use
- long-context sanity
- bounded concurrency
- branch-style concurrency

And does not yet include:
- direct structured outputs
- LiteLLM `main` structured outputs

## Docs Updated In-Repo
The following repo truth was updated to match this pass:
- [NOW.md](/home/christopherbailey/homelab-llm/NOW.md)
- [runtime-lock.md](/home/christopherbailey/homelab-llm/docs/foundation/runtime-lock.md)
- [runtime-lock.json](/home/christopherbailey/homelab-llm/platform/ops/runtime-lock.json)
- [testing.md](/home/christopherbailey/homelab-llm/docs/foundation/testing.md)
- [index.md](/home/christopherbailey/homelab-llm/docs/journal/index.md)
- [2026-03-18-main-8101-structured-output-protocol-validation.md](/home/christopherbailey/homelab-llm/docs/journal/2026-03-18-main-8101-structured-output-protocol-validation.md)

## Recommended Next Slice
If structured outputs still matter for `main`, the next slice should be narrow
and backend-specific:
- keep canonical `main` on `8101`
- keep parser and lane topology unchanged
- gather backend-path evidence only for current structured decoding behavior
- do not reopen fallback, alias, GPT-lane, or architecture discussions inside
  that slice

If structured outputs are not immediately required for `main`, the practical
decision is simpler:
- keep them out of the accepted public contract for now
- stop treating the issue as a LiteLLM seam question
- continue other hardening work without misrepresenting current `main`
  capabilities

## Bottom Line
The structured-output question for canonical `main` on `8101` is settled for
the current runtime:
- direct exact documented `response_format`: fail
- direct exact `structured_outputs.json`: fail
- LiteLLM exact documented `response_format`: fail

The failure is real, backend-path visible, and currently not fixed by using the
documented alternative request shapes.

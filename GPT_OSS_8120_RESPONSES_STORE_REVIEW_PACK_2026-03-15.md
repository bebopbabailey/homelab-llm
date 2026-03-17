# GPT-OSS 20B `8120` Responses-Store Review Pack

Date: 2026-03-15  
Audience: associate / senior review  
Scope: isolated GPT-OSS 20B experimental rerun on Studio `8120` with Responses-store enabled, canonical trio untouched

## Executive Summary

This pass re-ran the non-canonical GPT-OSS 20B tool experiment on Studio
experimental port `8120`, using the same GPT-OSS `vllm serve` config as the
prior experiment plus:

- `VLLM_ENABLE_RESPONSES_API_STORE=1`

The purpose was to separate four possible failure classes that had previously
been conflated:

- store/config failure
- protocol-shape drift
- caller-contract incompatibility
- model-semantic failure

The result is much narrower than the earlier GPT-OSS report:

- Responses storage and retrieval now work cleanly.
- Follow-up continuation now works cleanly whenever the initial Responses turn
  emits a valid `function_call`.
- Deterministic Chat Completions with `temperature=0.0` and `stream=false`
  also behaved cleanly in this pass.
- The remaining failure is on the **initial Responses tool-emission step**:
  `2/10` noop-tool trials completed with reasoning-only output and no callable
  item.

That means the unresolved issue is no longer “Responses store is broken,” and
no longer the earlier default Chat Completions `500` / null-no-tool failure
shape. The remaining problem is initial-turn GPT-OSS 20B Responses reliability.

Current conclusion:

- GPT-OSS 20B tool use is **still not production-reliable** on this stack.
- `main` should remain the only production-approved tool-capable lane.
- `fast` should remain canonical GPT-OSS 20B plain-chat only.

## Mission and Constraints

This pass followed the narrowed remediation plan:

- keep the canonical trio untouched
- keep the work on experimental `8120`
- keep the requests non-streaming
- treat `/v1/responses` as the primary GPT-OSS backend truth path
- keep `/v1/chat/completions` as a compatibility probe, not the primary truth

No changes were made to:

- `deep` / `8100`
- `main` / `8101`
- `fast` / `8102`
- LiteLLM production aliases
- OpenCode production routing
- launchd-managed team lanes

## Current Runtime and Contract Context

Observed locally before the rerun:

- canonical trio remained:
  - `8100` -> GPT-OSS 120B
  - `8101` -> Llama 3.3
  - `8102` -> GPT-OSS 20B
- current production caller reality remained Chat Completions-centric
- the prior `8120` GPT-OSS experiment had already shown:
  - `/v1/responses` stronger than Chat Completions
  - but follow-up continuation failed because response storage was not enabled

Installed Studio runtime evidence from the active `vllm-metal` environment:

- `VLLM_ENABLE_RESPONSES_API_STORE` exists in installed `vllm/envs.py`
- `serving_responses.py` uses that env var to enable internal response storage
- installed runtime exposes:
  - `GET /v1/responses/{response_id}`
  - `POST /v1/responses`
  - `POST /v1/chat/completions`
- installed runtime supports `function_call_output`
- installed runtime does **not** expose `mcp_call_output`

That last point matters:

- if the initial Responses turn had returned `mcp_call` with no reusable
  `call_id`, the follow-up turn would have been unattemptable
- in this rerun, that specific drift did not occur

## Primary Source Alignment

This rerun should be interpreted against current upstream guidance:

- vLLM tool-calling docs: <https://docs.vllm.ai/en/latest/features/tool_calling/>
- vLLM OpenAI-compatible server docs: <https://docs.vllm.ai/en/latest/serving/openai_compatible_server/>
- OpenAI Harmony guide: <https://cookbook.openai.com/articles/openai-harmony>

The key upstream framing remains consistent with the local outcome:

- `/v1/responses` is the recommended GPT-OSS interface
- GPT-OSS tool use should be validated first on Responses, not inferred from a
  plain Chat Completions lane
- Chat Completions behavior can still be useful as a compatibility probe, but
  it is not the first source of truth for GPT-OSS tool capability

## Exact Experimental Runtime

Host:

- Studio

Bind:

- `127.0.0.1:8120`

Environment:

- `VLLM_METAL_MEMORY_FRACTION=auto`
- `VLLM_ENABLE_RESPONSES_API_STORE=1`

Exact argv:

```bash
/Users/thestudio/.venv-vllm-metal/bin/vllm serve \
  /Users/thestudio/models/hf/models--mlx-community--gpt-oss-20b-MXFP4-Q4/snapshots/f356f2747216d7e98fee755df25987459fc19089 \
  --served-model-name mlx-gpt-oss-20b-mxfp4-q4-exp-tools \
  --host 127.0.0.1 \
  --port 8120 \
  --max-model-len 32768 \
  --chat-template /opt/mlx-launch/templates/gpt-oss-20b-chat_template.jinja \
  --default-chat-template-kwargs '{"enable_thinking": false, "reasoning_effort": "low"}' \
  --enable-auto-tool-choice \
  --tool-call-parser openai \
  --no-async-scheduling
```

Observed runtime note from the live log:

- vLLM warns that enabling Responses-store may leak memory because stored
  responses are not removed until server termination

That warning is acceptable for this disposable experimental process and should
not be read as a production recommendation.

## Test Matrix

### Matrix A: `/v1/responses` noop tool, `10x`

Request shape:

```json
{
  "model": "mlx-gpt-oss-20b-mxfp4-q4-exp-tools",
  "input": "Use the noop tool exactly once, then stop.",
  "tools": [
    {
      "type": "function",
      "name": "noop",
      "description": "noop",
      "parameters": {"type": "object", "properties": {}}
    }
  ],
  "tool_choice": "auto",
  "store": true
}
```

Scoring:

- `shape_success`: any valid callable output item with parseable JSON args
- `broad_semantic_success`: `function_call` or `mcp_call`, correct `noop` name,
  args parse to `{}`
- `strict_protocol_clean_success`: `function_call` only, correct `noop` name,
  args parse to `{}`

### Stored-response retrieval

After each successful Matrix A run, retrieval was verified via:

- `GET /v1/responses/{response_id}`

This separated store/config behavior from model/tool behavior.

### Matrix B: `/v1/responses` follow-up tool-result turn, `10` paired trials

For attemptable trials, the follow-up used:

```json
{
  "model": "mlx-gpt-oss-20b-mxfp4-q4-exp-tools",
  "previous_response_id": "<response_id>",
  "input": [
    {
      "type": "function_call_output",
      "call_id": "<call_id>",
      "output": "{\"ok\":true}"
    }
  ]
}
```

Hard rule preserved:

- no `mcp_call_output` was invented

### Matrix C: `/v1/chat/completions` noop tool, `10x`

This was explicitly treated as a compatibility probe, not the primary backend
truth path.

Request shape:

```json
{
  "model": "mlx-gpt-oss-20b-mxfp4-q4-exp-tools",
  "messages": [{"role": "user", "content": "Use the noop tool exactly once, then stop."}],
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "noop",
        "description": "noop",
        "parameters": {"type": "object", "properties": {}}
      }
    }
  ],
  "tool_choice": "auto",
  "stream": false,
  "max_tokens": 256,
  "temperature": 0.0
}
```

## Scorecard

### Matrix A: initial Responses noop turn

- `shape_success_rate = 8/10`
- `broad_semantic_success_rate = 8/10`
- `strict_protocol_clean_success_rate = 8/10`

Observed shape:

- `8/10` returned clean `function_call` with:
  - `name = "noop"`
  - `arguments = "{}"`
- `0/10` returned `mcp_call`
- `2/10` returned reasoning-only output and no callable item

Interpretation:

- protocol-shape drift was **not** the issue in this pass
- initial tool emission remains the actual weak point

### Stored-response retrieval

- `stored_response_retrieval_success_rate = 10/10`

Observed shape:

- all ten retrieval calls returned `200`
- all ten retrieved the stored response object successfully
- no `404`
- no invalid-request error

Interpretation:

- response-store semantics are functioning on this stack when the env var is
  enabled
- the previous continuation failure should no longer be blamed on disabled
  store semantics in this rerun

### Matrix B: follow-up continuation

- `follow_up_attemptable_count = 8/10`
- `follow_up_shape_success_rate = 8/10`
- `follow_up_semantic_success_rate = 8/10`

Observed shape:

- all `8/8` attemptable follow-up trials succeeded
- successful follow-up returned terminal assistant output
- representative follow-up output was a simple assistant message: `"Okay."`

Why only `8/10` were attemptable:

- the two Matrix A reasoning-only failures had no callable item
- therefore there was no reusable `call_id`
- these two trials were blocked by initial model behavior, not by store failure

Interpretation:

- continuation now works when the initial tool turn is valid
- the continuation path itself is not the current blocker

### Matrix C: deterministic Chat Completions compatibility probe

- `shape_success_rate = 10/10`
- `semantic_success_rate = 10/10`
- `http_500_count = 0`
- `null_content_no_tool_count = 0`
- `null_content_with_valid_tool_count = 10`

Observed shape:

- all ten runs returned `200`
- all ten returned one valid `tool_call`
- all ten had:
  - `finish_reason = "tool_calls"`
  - `content = null`
  - reasoning fields present

Interpretation:

- under this exact deterministic config, the earlier Chat Completions failure
  pattern did not recur
- however, this remains a compatibility probe result, not the primary GPT-OSS
  backend truth result
- `content:null` remains part of the Chat Completions tool shape for this model
  and runtime in this configuration

## Failure Attribution

### 1. Store/config failures

Current result:

- none

Evidence:

- retrieval succeeded `10/10`
- no `404` on retrieval
- no invalid-request failures on retrieval
- follow-up continuation succeeded on every attemptable trial

Conclusion:

- this rerun rules out Responses-store configuration as the remaining blocker

### 2. Protocol-shape drift

Current result:

- none in successful Responses tool turns

Evidence:

- successful Matrix A turns returned `function_call`, not `mcp_call`
- a reusable `call_id` was present on all successful initial tool turns

Conclusion:

- Harmony/output-shape drift is not the dominant remaining problem in this pass

### 3. Caller-contract incompatibility

Current result:

- reduced but still relevant

Evidence:

- deterministic Chat Completions performed much better than before
- all ten deterministic Chat Completions runs returned valid tool calls
- but all ten still relied on `content:null` plus tool calls and reasoning fields

Conclusion:

- current deterministic Chat Completions can work as a tool-call shape on this
  stack
- but Responses remains the cleaner backend truth test for GPT-OSS
- Chat Completions should still be treated as a caller compatibility question,
  not the core backend source of truth

### 4. Model semantic failures

Current result:

- present

Evidence:

- `2/10` Matrix A trials returned only reasoning and no callable output item
- those failures happened despite:
  - correct tool flags
  - correct GPT chat-template kwargs
  - response storage enabled
  - clean retrieval support

Conclusion:

- the remaining unresolved issue is initial-turn GPT-OSS 20B tool-emission
  reliability on `/v1/responses`

## Representative Raw Evidence

The full per-trial ledger and representative request/response pairs are staged
in [SCRATCH_PAD.md](/home/christopherbailey/homelab-llm/SCRATCH_PAD.md).

Representative cases include:

- `a_fail`
  - initial `/v1/responses` noop request
  - `200 OK`
  - reasoning-only output
  - no callable item
- `b_success`
  - follow-up continuation using `previous_response_id` and
    `function_call_output`
  - `200 OK`
  - terminal assistant message returned
- `c_success`
  - deterministic `/v1/chat/completions` noop request
  - `200 OK`
  - valid `tool_calls`
  - `content = null`

## Operational Outcome

The experimental process was cleaned up after the run:

- pid file removed
- `8120` listener cleared

The canonical trio remained untouched throughout.

## Final Assessment

This pass materially clarified the problem.

The system is no longer failing at stored-response semantics.
The system is no longer failing at continuation once a valid tool turn exists.
The system is no longer showing the earlier deterministic Chat Completions
`500` / null-no-tool failure shape.

The remaining problem is now narrow and explicit:

- GPT-OSS 20B still fails to emit the initial tool call on `2/10` Responses
  noop trials, even with the documented tool flags and working response-store
  semantics.

That is why the final verdict remains:

- `GPT-OSS 20B tool use is still not reliable on current stack`

## Production Recommendation

Do not promote GPT-OSS 20B tool use into the production `fast` lane. Keep
`fast` plain-chat only and keep `main` as the only production-approved tool
lane. If further GPT-only work is desired, it should focus narrowly on the
initial `/v1/responses` tool-emission reliability problem rather than on
response-store semantics or lane-management behavior.

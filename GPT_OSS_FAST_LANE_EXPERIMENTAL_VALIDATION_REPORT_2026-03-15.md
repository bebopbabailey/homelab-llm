# GPT-OSS Fast-Lane Experimental Validation Report

Date: 2026-03-15  
Audience: senior review / associate follow-up  
Scope: experimental validation of GPT-OSS 20B tool use on the current Studio `vllm-metal` stack, without mutating the canonical trio

## Executive Summary

This experiment tested whether `mlx-community/gpt-oss-20b-MXFP4-Q4` can be made into a reliable tool-capable lane on the current Studio `vllm-metal` runtime when launched with the current upstream-documented GPT-OSS function-calling path.

The experiment was intentionally non-invasive:

- canonical `deep` / `main` / `fast` were left untouched
- no LiteLLM production alias changes were made
- no OpenCode production routing changes were made
- the test ran on Studio experimental port `8120`

The core result is:

- GPT-OSS 20B tool use improved materially when tested with:
  - `--enable-auto-tool-choice`
  - `--tool-call-parser openai`
  - the current GPT chat template
  - current GPT chat-template kwargs
- but it is still **not reliable enough** on the current stack to approve as a production tool lane

Why:

- `/v1/responses` is clearly stronger than the old plain-chat canonical `fast` path
- default `/v1/chat/completions` tool behavior is still inconsistent
- one repeated Chat Completions tool run returned `500`
- one repeated Chat Completions tool run returned `content: null` and no tool call
- `/v1/responses` follow-up tool-output continuation failed with `404 response_id not found`
- `Responses` also showed inconsistent output shape on 20B:
  - mostly `function_call`
  - one run emitted `mcp_call`

The final experimental verdict is:

- `GPT-OSS 20B tool use is still not reliable on current stack`

Current production policy should remain:

- `main` is the only production-approved tool-capable lane
- `fast` remains canonical GPT-OSS 20B, but plain-chat only

## Mission and Constraints

The experiment followed the approved implementation spec exactly:

- keep scope to GPT-OSS fast-lane experimental validation
- prefer primary-source evidence over assumptions
- do not mutate the canonical trio unless explicitly permitted
- do not rewrite the control plane
- determine whether the current `fast` weirdness is:
  - endpoint mismatch
  - missing function-calling flags
  - Chat Completions adapter bugs
  - or a genuinely non-viable GPT-OSS tool path on this stack

## Current Canonical State Before the Experiment

Observed locally before the experimental run:

- `deep` (`8100`) -> `mlx-gpt-oss-120b-mxfp4-q4`
- `main` (`8101`) -> `mlx-llama-3-3-70b-4bit-instruct`
- `fast` (`8102`) -> `mlx-gpt-oss-20b-mxfp4-q4`

Current production contract:

- `main` is the validated tool-capable lane
- `fast` is the small-model GPT-OSS lane
- repo-local OpenCode policy is still Chat Completions-centric
- no production caller contract was changed in this pass

## Primary Sources Reconciled

The experiment was grounded in these current upstream sources:

- vLLM tool-calling docs: <https://docs.vllm.ai/en/latest/features/tool_calling/>
- vLLM OpenAI-compatible server docs: <https://docs.vllm.ai/en/latest/serving/openai_compatible_server/>
- OpenAI Harmony guide: <https://cookbook.openai.com/articles/openai-harmony>

Relevant current issue threads reviewed for alignment with observed runtime behavior:

- <https://github.com/vllm-project/vllm/issues/22519>
- <https://github.com/vllm-project/vllm/issues/22284>
- <https://github.com/vllm-project/vllm/issues/26967>
- <https://github.com/vllm-project/vllm/issues/27641>
- <https://github.com/vllm-project/vllm/issues/24283>

These sources align with the current local evidence better than older GPT-OSS examples:

- the Responses path is the stronger GPT-OSS surface
- Chat Completions tool behavior remains a known sharp edge
- GPT-OSS output may still carry Harmony/reasoning semantics that need careful handling

## Phase 1 Diagnosis

## 1. What endpoint(s) were being used before this pass?

Current local evidence showed:

- the repo’s GPT-OSS review work had primarily been using `/v1/chat/completions`
- the matched 20B vs 120B noop evidence was collected on `/v1/chat/completions`
- repo-local OpenCode and LiteLLM docs are still oriented around Chat Completions for the relevant workflow

## 2. What caller contract actually matters?

Current local evidence points to:

- OpenCode via LiteLLM aliases
- current repo-local usage and docs remain Chat Completions-centric
- LiteLLM service spec does expose `/v1/responses`, but that is not yet the established production caller contract for `fast`

## 3. Can the current production caller consume Responses semantics?

Not established as production reality in this repo.

Observed local evidence:

- LiteLLM service spec documents `/v1/responses`
- but repo-local OpenCode defaults and worker routing assumptions are still built around Chat Completions semantics
- OpenHands route allowlisting explicitly restricts worker traffic to `/v1/chat/completions`

Practical conclusion for this pass:

- a Responses-only success would not be enough to approve GPT-OSS as the production `fast` tool lane

## 4. Does the current runtime expose any GPT reasoning parser?

Observed locally from `mlxctl vllm-capabilities --json`:

- `supports_reasoning_parser = true`
- `reasoning_parsers = []`

Therefore:

- no GPT-specific reasoning parser is currently exposed
- none was assumed or configured in this pass

## 5. Are current `gpt_oss_lane` semantics plain-chat-only?

Yes.

Observed locally from `platform/ops/mlx-runtime-profiles.json` and `vllm-render`:

- `tool_choice_mode = none`
- no tool parser
- current GPT chat-template kwargs preserved:
  - `enable_thinking = false`
  - `reasoning_effort = low`

That means the old canonical `fast` lane was not a true GPT-OSS function-calling lane.

## Repo-Tracked Change Made for the Experiment

One new experimental runtime profile was added:

- `gpt_oss_tools_experimental`

It is intentionally separate from the canonical GPT profile and does not auto-bind to canonical lanes.

Its exact defaults:

- `tool_choice_mode = auto`
- `tool_call_parser = openai`
- `reasoning_parser = null`
- `chat_template_mode = tokenizer`
- `trust_remote_code = false`
- `chat_template_strategy = tokenizer`
- `chat_template_kwargs = {"enable_thinking": false, "reasoning_effort": "low"}`
- `auto_tool_choice_policy = recommended`
- `reasoning_parser_policy = forbidden`
- `readiness_probe_mode = chat_tool_noop`
- `readiness_acceptance_predicate = noop_tool_call`
- `readiness_max_tokens = 256`

## Experimental Launch

## Host and port

- Host: Studio
- Port: `8120`
- Binding: `127.0.0.1`

## Exact experimental argv

Observed from the live process:

```bash
/Users/thestudio/.venv-vllm-metal/bin/python3 /Users/thestudio/.venv-vllm-metal/bin/vllm serve /Users/thestudio/models/hf/models--mlx-community--gpt-oss-20b-MXFP4-Q4/snapshots/f356f2747216d7e98fee755df25987459fc19089 --served-model-name mlx-gpt-oss-20b-mxfp4-q4-exp-tools --host 127.0.0.1 --port 8120 --max-model-len 32768 --chat-template /opt/mlx-launch/templates/gpt-oss-20b-chat_template.jinja --default-chat-template-kwargs {"enable_thinking": false, "reasoning_effort": "low"} --enable-auto-tool-choice --tool-call-parser openai --no-async-scheduling
```

Important properties:

- same GPT-OSS 20B family as canonical `fast`
- same GPT chat template as canonical `fast`
- same GPT chat-template kwargs as canonical `fast`
- only the documented tool-calling knobs were added:
  - `--enable-auto-tool-choice`
  - `--tool-call-parser openai`

No undocumented parser combinations were introduced first.

## Backend Matrix Executed

## Matrix A — plain chat sanity

### A1. Chat Completions, no tools, `include_reasoning=false`

Request:

```json
{
  "model": "mlx-gpt-oss-20b-mxfp4-q4-exp-tools",
  "messages": [
    {
      "role": "user",
      "content": "Reply with exactly: chat-ok"
    }
  ],
  "stream": false,
  "max_tokens": 64,
  "include_reasoning": false
}
```

Observed result:

- HTTP `200`
- assistant `content = "chat-ok"`
- `reasoning = null`
- `reasoning_content = null`

Conclusion:

- plain chat can be made clean enough on Chat Completions for this GPT-OSS canary when `include_reasoning=false`

### A2. Chat Completions, no tools, default reasoning behavior

Repeated three times.

Observed result each time:

- HTTP `200`
- assistant `content = "chat-ok"`
- `reasoning` and `reasoning_content` both present

Conclusion:

- plain chat is usable
- reasoning-field leakage remains in the default shape

## Matrix B — function-calling behavior

## B1. Responses API noop tool, repeated 5x

Observed results:

- all five calls returned HTTP `200`
- four runs returned a `function_call` for `noop` with `arguments = "{}"`
- one run returned `mcp_call` instead of `function_call`

Representative good result:

```json
{
  "type": "function_call",
  "name": "noop",
  "arguments": "{}",
  "call_id": "call_abb045a867a05fd9"
}
```

Representative inconsistent result:

```json
{
  "id": "mcp_8c65a7664b82dae4",
  "arguments": "{}",
  "name": "noop",
  "server_label": "-functions",
  "type": "mcp_call",
  "status": "completed"
}
```

Conclusion:

- Responses is clearly stronger than the old plain-chat `fast` path
- but the output format is not stable enough on 20B to call cleanly production-ready

## B2. Chat Completions noop tool, repeated 5x

Observed results:

1. HTTP `500`
   - error: `unexpected tokens remaining in message header: Some("to=functions.noop")`
2. HTTP `200`
   - `content = null`
   - `tool_calls = []`
3. HTTP `200`
   - valid `tool_calls`
   - `finish_reason = "tool_calls"`
4. HTTP `200`
   - valid `tool_calls`
   - `finish_reason = "tool_calls"`
5. HTTP `200`
   - `content = null`
   - `tool_calls = []`

Representative failure:

```json
{
  "error": {
    "message": "unexpected tokens remaining in message header: Some(\"to=functions.noop\")",
    "type": "Internal Server Error",
    "code": 500
  }
}
```

Representative success:

```json
{
  "message": {
    "role": "assistant",
    "content": null,
    "tool_calls": [
      {
        "type": "function",
        "function": {
          "name": "noop",
          "arguments": "{}"
        }
      }
    ]
  },
  "finish_reason": "tool_calls"
}
```

Conclusion:

- the default Chat Completions tool path is not reliable enough

## B3. Responses follow-up tool-result turn

Observed result:

- HTTP `404`
- error: `Response with id 'resp_91cc79816c015d38' not found.`

Conclusion:

- the current `previous_response_id` continuation path did not behave like a clean reusable response-thread contract in this experiment

## B4. Chat Completions noop tool with `temperature=0.0`, repeated 5x

Observed result:

- five of five returned HTTP `200`
- five of five returned structured `tool_calls`
- all five used:
  - `name = "noop"`
  - `arguments = "{}"`
- all five finished with:
  - `finish_reason = "tool_calls"`

Conclusion:

- deterministic decoding materially improved Chat Completions stability here
- but this does not prove the current production caller contract is already safe
- it proves a narrower experimental mitigation exists

## Acceptance Evaluation

## Plain-chat acceptance

Pass.

The experiment showed:

- repeated plain Chat Completions return valid assistant text
- no empty completion
- no `content: null`
- no severe user-visible corruption in plain text

Reasoning fields still appear by default, but the spec allowed recording that rather than hiding it.

## Tool-lane backend acceptance

Fail.

Why:

- Responses path was not consistently one native tool-call shape
- one `mcp_call` appeared instead of a stable `function_call` contract
- follow-up Responses tool-output continuation failed with `404`
- default Chat Completions repeated runs included:
  - one hard `500`
  - one null/no-tool run
  - one additional null/no-tool run

This does not meet the spec’s reliability bar.

## Production approval bar

Fail.

Even though the experiment found a much stronger path than canonical `fast`, the result still does not justify promoting GPT-OSS 20B as a production tool lane because:

- backend acceptance did not pass cleanly
- the actual production caller contract remains Chat Completions-centric
- the reliable Chat Completions result depended on a deterministic variant not yet established as production contract

## What the Experiment Actually Proved

The experiment resolved several earlier ambiguities.

## 1. The old canonical `fast` tests were hitting the wrong contract

Earlier GPT-OSS `fast` failures were not testing a documented GPT-OSS function-calling lane.

They were testing:

- plain-chat GPT profile
- tools present in the request
- no GPT-OSS tool parser
- no auto-tool mode

That was a real mismatch.

## 2. Endpoint choice matters a lot

Observed local evidence now strongly supports:

- Responses is the better GPT-OSS tool surface on this stack
- Chat Completions is still the unstable edge

## 3. The remaining problem is not just “20B is too weak”

Why:

- 20B can produce valid structured tool calls in both Responses and Chat Completions under the experimental launch
- but reliability varies by endpoint and decoding behavior

So this is not simply:

- “20B too small to tool call”

It is more precisely:

- endpoint/adapter/runtime behavior remains unstable enough that 20B tool use is not production-safe yet

## 4. There is still a GPT-specific adapter/runtime problem on the current stack

The clearest evidence:

- `500 unexpected tokens remaining in message header`
- null/no-tool Chat Completions runs
- `mcp_call` showing up inside Responses output
- `previous_response_id` follow-up returning `404`

Those are not just “weak model” symptoms. They point to unresolved GPT-OSS integration behavior on the current stack.

## Detailed Root Cause Assessment

### Fixed mismatch

Fixed by this experiment:

- the earlier testing path was not launching GPT-OSS 20B as a documented function-calling lane

### Still unresolved

Unresolved after this experiment:

- default Chat Completions tool-calling is still not reliable
- Responses output is stronger but not yet clean enough to bless
- deterministic settings improve behavior, but that is not the same as proving the current production caller contract is safe

## Files Changed for This Pass

- [NOW.md](/home/christopherbailey/homelab-llm/NOW.md)
- [platform/ops/mlx-runtime-profiles.json](/home/christopherbailey/homelab-llm/platform/ops/mlx-runtime-profiles.json)
- [platform/ops/scripts/tests/test_mlx_runtime_profiles.py](/home/christopherbailey/homelab-llm/platform/ops/scripts/tests/test_mlx_runtime_profiles.py)

## Commands Run

Local validation:

```bash
uv run python platform/ops/scripts/tests/test_mlx_runtime_profiles.py
./platform/ops/scripts/mlxctl vllm-capabilities --json
./platform/ops/scripts/mlxctl vllm-render --ports 8100,8102 --validate --json
```

Studio preflight:

```bash
ssh studio 'lsof -nP -iTCP:8120 -sTCP:LISTEN || true'
ssh studio 'test -d /Users/thestudio/models/hf/models--mlx-community--gpt-oss-20b-MXFP4-Q4/snapshots/f356f2747216d7e98fee755df25987459fc19089 && echo snapshot-ok'
ssh studio '/Users/thestudio/.venv-vllm-metal/bin/vllm serve --help=all | rg -n "default-chat-template-kwargs|tool-call-parser|enable-auto-tool-choice"'
```

Studio experimental launch:

```bash
ssh studio 'python3 - <<\"PY\"
...
PY'
```

Studio backend matrix:

```bash
ssh studio 'python3 - <<\"PY\"
...
PY'
```

Studio cleanup:

```bash
ssh studio 'kill $(cat /tmp/vllm-8120-gptoss-tools-exp.pid) && rm -f /tmp/vllm-8120-gptoss-tools-exp.pid && echo stopped'
ssh studio 'sleep 2; lsof -nP -iTCP:8120 -sTCP:LISTEN || true'
```

## Final Verdict

`GPT-OSS 20B tool use is still not reliable on current stack`

## Production Recommendation

Keep `fast` as plain-chat only. Keep `main` as the only production-approved tool-capable lane. If GPT-OSS tool work continues, the next pass should be a narrower GPT-only investigation around:

- whether a deterministic Chat Completions contract is acceptable for the actual caller
- whether Responses output shape can be normalized or made stable enough
- whether the unresolved `500`, `mcp_call`, and `response_id` follow-up issues are known upstream defects or local runtime-specific behavior

## Operator-Facing Conclusion

- **What was wrong:** earlier GPT-OSS `fast` testing was hitting a plain-chat lane and not the documented GPT-OSS function-calling launch path; even after fixing that, the current stack still shows unstable tool behavior across endpoints.
- **What I changed:** I added a dedicated experimental GPT-OSS tools profile, launched a non-canonical `8120` GPT-OSS 20B canary with `openai` tool parser plus auto-tool mode, and ran the required backend matrix on both `/v1/chat/completions` and `/v1/responses`.
- **What the experiment proved:** GPT-OSS 20B can produce structured tool calls on this stack, but not reliably enough across the current endpoint/caller contract to approve it as a production tool lane.
- **What should be production policy now:** keep `fast` plain-chat only, keep `main` as the tool-capable lane, and treat GPT-OSS tool use as experimental until the endpoint/runtime instability is resolved.

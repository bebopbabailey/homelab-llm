# LiteLLM GPT-OSS 20B Noop-Tool Causal Isolation Report
Date: 2026-03-17
Host: Mini orchestrating the existing Studio experimental backend on `127.0.0.1:8120` through the established local tunnel
Scope: `metal-test-gptoss20b-enforce` experimental LiteLLM lane and the direct backend truth path
Status: Complete

## Executive Summary
This pass answered the narrow question that was still blocking promotion thinking:

- Is the repeated noop-tool failure caused by OpenCode?
- Is it caused by LiteLLM transport enforcement?
- Or does it already exist on the direct backend/runtime path?

The answer is now clear.

The failure already exists on the direct backend truth path.

On the exact frozen noop-tool request body, the direct backend failed `20/20` initial attempts. Every attempt returned:
- `HTTP 200`
- `status: "incomplete"`
- `incomplete_details.reason: "max_output_tokens"`
- output containing only `reasoning`
- no `function_call`
- no `call_id`

That same failure repeated after a clean backend restart. It also remained unchanged under the two explanatory direct probes:
- `max_output_tokens=1024`
- `store=false`

LiteLLM parity matched the same `20/20` failure shape, which means LiteLLM did not introduce the failure. It simply preserved the same broken initial tool-emission behavior through the already-validated transport contract.

The practical outcome is straightforward:

- `metal-test-gptoss20b-enforce` should remain experimental.
- Promotion-plan drafting toward canonical `fast` is blocked.
- The next useful work is backend/runtime GPT-OSS Responses tool-emission diagnosis, not more caller or LiteLLM transport work.

## Why This Pass Existed
The prior passes had already narrowed the problem space substantially.

What was already established before this pass:
- GPT-OSS 20B had a validated constrained backend transport contract:
  - `POST /v1/responses`
  - `stream=false`
  - `temperature=0.0`
- OpenCode config alone was not enough to preserve that contract.
- LiteLLM config alone was not enough either, because `stream=true` still leaked through.
- A narrow LiteLLM normalize guardrail was enough to make the backend consistently see the constrained transport.
- The experimental lane `metal-test-gptoss20b-enforce` was therefore useful and safe enough to keep experimentally.
- A later soak then showed the remaining blocker was not transport drift but repeated noop-tool instability.

That left one unresolved causal question:

Was the noop-tool failure actually a backend/runtime problem, or was it introduced somewhere in the LiteLLM lane or higher-level caller path?

This pass was designed to answer that question with minimal confounds:
- no OpenCode
- no prompt variation between attempts
- frozen initial request body
- frozen continuation body
- direct backend truth path first
- LiteLLM parity only after the direct path was characterized

## Pass Design
The pass used one frozen initial request body for every baseline attempt.

Direct initial body:

```json
{
  "model": "mlx-gpt-oss-20b-mxfp4-q4-exp-constrained",
  "input": "Use the noop tool exactly once, then stop.",
  "max_output_tokens": 512,
  "store": true,
  "stream": false,
  "temperature": 0.0,
  "tool_choice": "auto",
  "tools": [
    {
      "type": "function",
      "name": "noop",
      "description": "Return success without side effects.",
      "parameters": {
        "type": "object",
        "properties": {
          "note": {
            "type": "string"
          }
        },
        "required": []
      }
    }
  ]
}
```

Continuation was also frozen:
- always retrieve first
- use canonical `response_id`
- use canonical `call_id`
- one `function_call_output` item only
- `output: "Done."`
- no resent `tools`
- no resent `tool_choice`
- no resent `store`

The direct path ran first because that is the truth path for causality. LiteLLM parity was not allowed to reinterpret a failed direct result.

## Runtime Fingerprint
The causal result is pinned to a specific runtime/build identity.

Key runtime facts captured in [phase0-runtime-fingerprint.json](/tmp/20260317T080649Z-gptoss20b-noop-causal-isolation/artifacts/phase0-runtime-fingerprint.json):
- LiteLLM version: `1.80.11`
- LiteLLM service status: `connected`
- Active callbacks included `ResponsesContractGuardrail`
- Experimental alias under test: `metal-test-gptoss20b-enforce`
- Backend PID at pass start: `21150`
- Backend process start time: `Mon Mar 16 19:56:28 2026`
- Served model: `mlx-gpt-oss-20b-mxfp4-q4-exp-constrained`
- Model snapshot root:
  - `/Users/thestudio/models/hf/models--mlx-community--gpt-oss-20b-MXFP4-Q4/snapshots/f356f2747216d7e98fee755df25987459fc19089`
- Chat template:
  - `/opt/mlx-launch/templates/gpt-oss-20b-chat_template.jinja`
- Chat template hash:
  - `a4c9919cbbd4acdd51ccffe22da049264b1b73e59055fa58811a99efbd7c8146`
- Guardrail hash:
  - `1fe0a42ec84fd63ec7021413be34c55b009207d6a4448c047ccf8bda6f5e684d`
- Backend package versions:
  - `vllm 0.14.1`
  - `transformers 4.57.6`
  - `mlx-lm 0.29.1`
  - `openai-harmony 0.0.8`
- vLLM install source marker:
  - `file:///Users/thestudio/vllm-0.14.1`

The exact backend argv was also preserved in [phase0-backend-argv.txt](/tmp/20260317T080649Z-gptoss20b-noop-causal-isolation/artifacts/phase0-backend-argv.txt), including:
- `--port 8120`
- `--chat-template /opt/mlx-launch/templates/gpt-oss-20b-chat_template.jinja`
- `--default-chat-template-kwargs {"enable_thinking": false, "reasoning_effort": "low"}`
- `--enable-auto-tool-choice`
- `--tool-call-parser openai`
- `--no-async-scheduling`

## Harness Notes
This pass found and corrected two temporary harness issues before the final classified run:

1. The local capture forwarder was initially pointed at `http://127.0.0.1:8875/v1`, which duplicated the path and produced `/v1/v1/responses`.
2. A Phase 0 journald check was initially too strict and stopped the wrapper even though the lane and guardrail were healthy.

Those were temporary runner defects only. They were corrected before the final classified run. The final run used the corrected forwarder and completed cleanly.

This matters because it means the actual result below is not an artifact of the temporary harness mistakes.

## Phase Results
### Phase 1: Direct Backend Frozen Baseline
Summary: [phase1-direct.summary.json](/tmp/20260317T080649Z-gptoss20b-noop-causal-isolation/artifacts/phase1-direct.summary.json)

Results:
- initial successes: `0`
- initial failures: `20`
- continuation successes: `0`
- continuation failures: `0`

Every initial attempt failed in the same way:
- `HTTP 200`
- `status: "incomplete"`
- `incomplete_details.reason: "max_output_tokens"`
- `output_types: ["reasoning"]`
- `call_id: null`

That means the direct backend never emitted the first tool call even once.

Representative direct response evidence is in:
- [phase1-direct.responses.jsonl](/tmp/20260317T080649Z-gptoss20b-noop-causal-isolation/artifacts/phase1-direct.responses.jsonl)

### Phase 1R: Clean-Restart Repeat
Summary: [phase1r-direct.summary.json](/tmp/20260317T080649Z-gptoss20b-noop-causal-isolation/artifacts/phase1r-direct.summary.json)

Results:
- initial successes: `0`
- initial failures: `20`
- continuation successes: `0`
- continuation failures: `0`

This is important because it removes the warmed-state-only explanation.

The direct baseline did not fail merely because the runtime had accumulated state over time. After a clean backend restart, the exact same frozen initial request body still failed `20/20`.

Restart proof artifacts:
- [phase1r-backend-ps.txt](/tmp/20260317T080649Z-gptoss20b-noop-causal-isolation/artifacts/phase1r-backend-ps.txt)
- [phase1r-models.json](/tmp/20260317T080649Z-gptoss20b-noop-causal-isolation/artifacts/phase1r-models.json)

### Phase 2.1: Headroom Probe (`max_output_tokens=1024`)
Summary: [phase2-direct-1024.summary.json](/tmp/20260317T080649Z-gptoss20b-noop-causal-isolation/artifacts/phase2-direct-1024.summary.json)

Results:
- initial successes: `0`
- initial failures: `20`
- continuation successes: `0`
- continuation failures: `0`

The failure still ended in `incomplete` with `reason=max_output_tokens`. The only meaningful change was that the backend consumed more reasoning tokens before failing. It still never emitted a tool call.

This means the problem is not narrowly explained by the original `512` budget being slightly too small.

### Phase 2.2: Store-State Probe (`store=false`)
Summary: [phase2-direct-storefalse.summary.json](/tmp/20260317T080649Z-gptoss20b-noop-causal-isolation/artifacts/phase2-direct-storefalse.summary.json)

Results:
- initial successes: `0`
- initial failures: `20`
- continuation successes: `0`
- continuation failures: `0`

This means the failure is not explained by `store=true` on the initial turn. The backend still failed to emit a tool call when storage was removed from the initial request.

### Phase 3: LiteLLM Symmetric Parity Block
Summary: [phase3-litellm.summary.json](/tmp/20260317T080649Z-gptoss20b-noop-causal-isolation/artifacts/phase3-litellm.summary.json)

Results:
- initial successes: `0`
- initial failures: `20`
- continuation successes: `0`
- continuation failures: `0`

This is the key parity result:

LiteLLM did not make the situation worse in a way that changes the causal conclusion. It reproduced the same total failure shape that already existed on the direct backend truth path.

That means:
- the LiteLLM normalize guardrail is not the cause of the noop-tool instability
- the experimental lane’s transport enforcement remains orthogonal to the actual blocker

## What We Learned
This pass gives four concrete findings.

### 1. The blocker is now pinned to the direct backend/runtime path
The lane is not blocked by OpenCode behavior or by LiteLLM transport enforcement.

The backend truth path itself cannot reliably emit the initial noop function call under the frozen constrained request body. In this run, it could not emit it at all.

### 2. The failure is stronger than the earlier soak suggested
The earlier soak had shown intermittent or repeated instability across rounds. This pass was stricter and more revealing:

- the direct backend did not merely fail occasionally
- it failed `20/20` on the frozen baseline
- it repeated after a clean restart

So the current state is not “mostly stable with a noisy edge.” It is “not stable enough on the truth path to justify any promotion planning.”

### 3. The obvious first explanations did not rescue it
Two of the most plausible immediate explanations were tested directly:
- maybe `512` output tokens were too tight
- maybe `store=true` was interacting badly with the initial turn

Neither changed the result.

The model continued to spend its budget in reasoning and fail before emitting the function call.

### 4. LiteLLM parity is not the problem
The same frozen request body failed `20/20` through LiteLLM as well, but that is not evidence against LiteLLM. The direct path had already failed first.

So the right reading is:
- LiteLLM parity reflects the same broken backend behavior
- the guardrail is not introducing a new failure class here

## Classification
The final classification is preserved in [classification.md](/tmp/20260317T080649Z-gptoss20b-noop-causal-isolation/artifacts/classification.md):

- Phase 1 direct path hit the absolute failure gate.
- Phase 1R direct restart repeat also hit the absolute failure gate.
- LiteLLM parity hit the absolute failure gate.

And the classification note remains important:

**Eligible to draft a controlled promotion plan is not the same as promotion-ready behavior. Any nonzero failure count remains incompatible with direct promotion and would require mitigation, containment, and rollback planning.**

In this run, that distinction is almost academic, because the direct path did not show a nonzero but tolerable failure count. It showed a full `20/20` initial failure rate.

## Decision
The correct decision from this pass is:

- keep `metal-test-gptoss20b-enforce` experimental
- do not draft a promotion plan toward canonical `fast`
- do not spend more time on OpenCode config or LiteLLM transport for this specific blocker

The lane remains useful as an experimental transport-enforcement lane. But the narrow tool path is not promotable because the backend truth path itself is failing the causal gate.

## Recommended Next Step
The next pass should target backend/runtime GPT-OSS Responses tool-emission behavior directly.

That follow-up should be narrower than this one and focus on why the backend consumes the full reasoning budget without emitting the tool call under the frozen noop-tool request body. Useful directions now include:
- backend/runtime parser and tool-call emission debugging on the exact frozen request body
- template / parser / reasoning-mode interactions in the current `vllm 0.14.1` + `openai-harmony 0.0.8` runtime
- comparing this runtime’s direct behavior with a known-good or previously-observed-good backend state if one exists

What should not happen next:
- no promotion planning toward canonical `fast`
- no more OpenCode churn for this specific issue
- no more LiteLLM guardrail broadening for this specific issue

Those are no longer the highest-value seams.

## Key Artifacts
Primary artifact root:
- [/tmp/20260317T080649Z-gptoss20b-noop-causal-isolation/artifacts](/tmp/20260317T080649Z-gptoss20b-noop-causal-isolation/artifacts)

Most important files:
- [phase0-runtime-fingerprint.json](/tmp/20260317T080649Z-gptoss20b-noop-causal-isolation/artifacts/phase0-runtime-fingerprint.json)
- [phase0-backend-argv.txt](/tmp/20260317T080649Z-gptoss20b-noop-causal-isolation/artifacts/phase0-backend-argv.txt)
- [phase1-direct.summary.json](/tmp/20260317T080649Z-gptoss20b-noop-causal-isolation/artifacts/phase1-direct.summary.json)
- [phase1r-direct.summary.json](/tmp/20260317T080649Z-gptoss20b-noop-causal-isolation/artifacts/phase1r-direct.summary.json)
- [phase2-direct-1024.summary.json](/tmp/20260317T080649Z-gptoss20b-noop-causal-isolation/artifacts/phase2-direct-1024.summary.json)
- [phase2-direct-storefalse.summary.json](/tmp/20260317T080649Z-gptoss20b-noop-causal-isolation/artifacts/phase2-direct-storefalse.summary.json)
- [phase3-litellm.summary.json](/tmp/20260317T080649Z-gptoss20b-noop-causal-isolation/artifacts/phase3-litellm.summary.json)
- [classification.md](/tmp/20260317T080649Z-gptoss20b-noop-causal-isolation/artifacts/classification.md)

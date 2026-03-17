# GPT-OSS 20B vs 120B A/B Verification Review Pack

Date: `2026-03-15`  
Host scope: Mini orchestrating Studio experimental `8120` only  
Audience: associate / senior review  
Canonical trio: unchanged throughout the pass

## Executive Summary

This pass was a narrow backend verification run intended to answer one question:

- are the remaining GPT-OSS tool-use failures mainly a `20B` weakness, or do they reflect shared `vllm-metal` / Harmony / runtime behavior that also affects `120B`?

The answer from this pass is:

- the current stack does **not** support blaming `20B` alone
- `20B` does show a real non-deterministic initial `/v1/responses` weakness
- but the resumed `120B` half failed much earlier and more severely at the backend/transport level
- the strongest conclusion from this pass is that shared backend/runtime behavior materially contributes on the current stack

Exact verdict used in the pass:

- `GPT-OSS tool unreliability is mainly shared backend/Harmony behavior on current stack`

That verdict is not saying `20B` is strong. It is saying the A/B comparison does not support the simpler story that only `20B` is weak while the stack itself is clean.

## Scope and Guardrails

This pass intentionally stayed narrow.

Allowed and used:

- experimental port `8120` only
- ephemeral `vllm serve` processes only
- local task tracking and evidence files only

Explicitly not changed:

- canonical lane assignments on `8100`, `8101`, `8102`
- LiteLLM aliases
- OpenCode routing
- launchd policy
- `mlxctl`

The canonical trio was left running because Studio preflight showed ample headroom and there was no need to stop the managed listeners for this run.

## Why This Pass Existed

Prior local evidence had already established:

- GPT-OSS `20B` on experimental `8120` with Responses-store enabled was no longer failing because of storage/retrieval
- stored-response retrieval had already succeeded `10/10`
- follow-up continuation had already succeeded on all attemptable trials in the smaller earlier pass
- the remaining `20B` issue was the initial `/v1/responses` tool-emission step, where some noop-tool prompts produced reasoning-only output with no callable item
- deterministic non-streaming `/v1/chat/completions` improved behavior substantially, but `/v1/responses` remained the primary backend truth path

That narrowed the next question to:

- is the remaining miss rate mostly a `20B` robustness problem, or would the same stack/runtime path also fail on `120B`?

## Source Basis

### Local evidence

- `./platform/ops/scripts/mlxctl studio-cli-sha`
- `./platform/ops/scripts/mlxctl status --checks --json`
- `./platform/ops/scripts/mlxctl vllm-render --ports 8100,8102 --validate --json`
- direct Studio `/v1/models` probes on `8100`, `8101`, `8102`
- Studio experimental logs:
  - `/Users/thestudio/vllm-8120-gptoss-20b-ab.log`
  - `/Users/thestudio/vllm-8120-gptoss-120b-ab.log`
- raw artifacts written locally:
  - `/tmp/gptoss_ab_raw_20b.json`
  - `/tmp/gptoss_ab_raw_120b.json`

### Upstream primary-source anchors

- vLLM GPT-OSS guidance that treats `/v1/responses` as the recommended interface
- OpenAI GPT-OSS verification guidance requiring validation of both tool selection and API shape
- OpenAI Harmony guidance
- recent vLLM GPT-OSS issue traffic showing Chat Completions sharp edges

This report does not re-quote long upstream text. It uses those sources as the policy/interpretation frame and relies on local raw artifacts for the actual verdict.

## Pre-State

Before the pass:

- `mlxctl studio-cli-sha` showed local and Studio CLI parity
- `mlxctl status --checks --json` showed:
  - `8100`: `serving`, `converged`
  - `8101`: `serving`, `converged`
  - `8102`: `serving`, `converged`
- `mlxctl vllm-render --ports 8100,8102 --validate --json` confirmed canonical GPT baselines:
  - `8100` / GPT-OSS `120B`: `--max-model-len 65536`
  - `8102` / GPT-OSS `20B`: `--max-model-len 32768`
- Studio memory preflight during the experimental launch showed roughly:
  - total memory: `274.9GB`
  - available memory: `146.1GB`

Because headroom was high, the canonical trio was **not** stopped.

## Intended Experimental Design

The intended design was serialized, not concurrent:

1. run `20B` alone on `8120`
2. tear it down
3. run `120B` alone on `8120`
4. compare the two datasets

Shared experimental config shape:

- `VLLM_ENABLE_RESPONSES_API_STORE=1`
- `VLLM_METAL_MEMORY_FRACTION=auto`
- GPT-OSS chat template
- default chat-template kwargs:
  - `{"enable_thinking": false, "reasoning_effort": "low"}`
- `--enable-auto-tool-choice`
- `--tool-call-parser openai`
- `--no-async-scheduling`

Request matrices:

- main `/v1/responses` initial noop-tool matrix: `100` trials
- retrieval check after each successful initial trial
- follow-up continuation for attemptable trials only
- deterministic `/v1/responses` appendix: `25` trials with `temperature=0.0`
- deterministic `/v1/chat/completions` compatibility probe: `25` trials with `temperature=0.0`

## Actual 20B Launch

Exact 20B experimental argv:

```bash
VLLM_METAL_MEMORY_FRACTION=auto \
VLLM_ENABLE_RESPONSES_API_STORE=1 \
/Users/thestudio/.venv-vllm-metal/bin/vllm serve \
  /Users/thestudio/models/hf/models--mlx-community--gpt-oss-20b-MXFP4-Q4/snapshots/f356f2747216d7e98fee755df25987459fc19089 \
  --served-model-name mlx-gpt-oss-20b-mxfp4-q4-exp-ab \
  --host 127.0.0.1 \
  --port 8120 \
  --max-model-len 32768 \
  --chat-template /opt/mlx-launch/templates/gpt-oss-20b-chat_template.jinja \
  --default-chat-template-kwargs '{"enable_thinking": false, "reasoning_effort": "low"}' \
  --enable-auto-tool-choice \
  --tool-call-parser openai \
  --no-async-scheduling
```

20B completed and produced a complete raw artifact:

- `/tmp/gptoss_ab_raw_20b.json`

### 20B Results

Main `/v1/responses`:

- `shape_success_rate`: `85/100`
- `broad_semantic_success_rate`: `73/100`
- `strict_protocol_clean_success_rate`: `73/100`
- `reasoning_only_no_call_rate`: `10/100`

Retrieval:

- `retrieval_success_rate`: `95/100`
- `retrieval_404_count`: `0`
- `invalid_request_count`: `0`
- `identity_mismatch_count`: `0`

Follow-up:

- `attemptable_count`: `73`
- `follow_up_shape_success_rate`: `73/100`
- `follow_up_semantic_success_rate`: `73/100`
- `terminal_assistant_continuation_rate`: `73/100`
- `another_tool_call_requested_count`: `0`

Deterministic `/v1/responses` appendix:

- `shape_success_rate`: `25/25`
- `broad_semantic_success_rate`: `25/25`
- `strict_protocol_clean_success_rate`: `25/25`
- `reasoning_only_no_call_rate`: `0/25`

Deterministic `/v1/chat/completions`:

- `http_200_rate`: `25/25`
- `tool_calls_present_rate`: `25/25`
- `content_null_with_valid_tool_calls_count`: `25`
- `content_null_with_no_tool_calls_count`: `0`
- `http_500_count`: `0`
- `no_tool_failure_count`: `0`

### 20B Interpretation

`20B` is clearly usable enough to produce valid function calls on the current stack, but it is not robust on the main non-deterministic Responses matrix:

- `10/100` main Responses trials were reasoning-only / no-call
- deterministic decoding eliminated those misses in the appendix

That makes `20B` look weak in non-deterministic first-turn tool emission, but not dead.

## What Happened Before 120B Could Be Scored Cleanly

The first attempt to continue the pass was blocked by a Studio lock event.

Observed blocker text:

```text
This system is locked. To unlock it, use a local
account name and password. Once successfully
unlocked, you will be able to connect normally.
thestudio@192.168.1.72: Permission denied (publickey,password,keyboard-interactive).
```

After Studio was unlocked, the missing `120B` half was resumed.

## Actual 120B Launch Behavior

The intended baseline for `120B` was:

- `--max-model-len 65536`

Observed behavior:

- the `65536` attempt did not yield a stable usable serving surface for the scored run
- a forced fallback to `32768` was required to get an active `8120` listener

The resumed active listener was:

```bash
/Users/thestudio/.venv-vllm-metal/bin/vllm serve \
  /Users/thestudio/models/hf/models--mlx-community--gpt-oss-120b-MXFP4-Q4/snapshots/bce781bef0f2fc85ed4e575af74054f5aad73ddd \
  --served-model-name mlx-gpt-oss-120b-mxfp4-q4-exp-ab \
  --host 127.0.0.1 \
  --port 8120 \
  --max-model-len 32768 \
  --chat-template /opt/mlx-launch/templates/gpt-oss-120b-chat_template.jinja \
  --default-chat-template-kwargs '{"enable_thinking": false, "reasoning_effort": "low"}' \
  --enable-auto-tool-choice \
  --tool-call-parser openai \
  --no-async-scheduling
```

The resumed `120B` client pass wrote a complete raw artifact:

- `/tmp/gptoss_ab_raw_120b.json`

## 120B Results

Main `/v1/responses`:

- `shape_success_rate`: `0/100`
- `broad_semantic_success_rate`: `0/100`
- `strict_protocol_clean_success_rate`: `0/100`
- `reasoning_only_no_call_rate`: `0/100`
- `transport_exception_count`: `100`

Retrieval:

- `retrieval_success_rate`: `0/100`
- `retrieval_404_count`: `0`
- `invalid_request_count`: `0`
- `identity_mismatch_count`: `0`

Follow-up:

- `attemptable_count`: `0`
- `follow_up_shape_success_rate`: `0/100`
- `follow_up_semantic_success_rate`: `0/100`
- `terminal_assistant_continuation_rate`: `0/100`
- `another_tool_call_requested_count`: `0`

Deterministic `/v1/responses` appendix:

- `shape_success_rate`: `0/25`
- `broad_semantic_success_rate`: `0/25`
- `strict_protocol_clean_success_rate`: `0/25`
- `reasoning_only_no_call_rate`: `0/25`
- `transport_exception_count`: `25`

Deterministic `/v1/chat/completions`:

- `http_200_rate`: `0/25`
- `tool_calls_present_rate`: `0/25`
- `content_null_with_valid_tool_calls_count`: `0`
- `content_null_with_no_tool_calls_count`: `0`
- `http_500_count`: `0`
- `no_tool_failure_count`: `0`
- `transport_exception_count`: `25`

### Representative 120B Failure Shapes

Main Responses transport reset:

```json
{
  "trial": 1,
  "http_status": null,
  "response": {
    "_exception": "ConnectionResetError",
    "message": "[Errno 104] Connection reset by peer"
  }
}
```

Later deterministic appendix / chat refusal:

```json
{
  "trial": 1,
  "http_status": null,
  "response": {
    "_exception": "URLError",
    "message": "<urlopen error [Errno 111] Connection refused>"
  }
}
```

### 120B Interpretation

This pass did **not** measure `120B` as a stronger tool model on the current stack.

Instead:

- baseline `65536` did not stabilize for the scored run
- fallback `32768` did produce an active listener
- but the scored traffic was dominated by transport-level failure:
  - connection resets
  - later connection refusals

That means the `120B` path failed before semantic tool behavior could be scored meaningfully.

## Direct Comparison

| metric | 20B | 120B | comparison |
| --- | --- | --- | --- |
| main Responses `shape_success_rate` | `85/100` | `0/100` | 120B path failed before stable protocol output |
| main Responses `strict_protocol_clean_success_rate` | `73/100` | `0/100` | 20B produced real `function_call` output; 120B did not |
| main Responses `reasoning_only_no_call_rate` | `10/100` | `0/100` | 20B weakness is semantic; 120B never reached the same scoring surface |
| retrieval success | `95/100` | `0/100` | 20B store path worked; 120B never produced retrievable stored responses |
| follow-up attemptable count | `73` | `0` | 20B had real first-call wins; 120B had none |
| deterministic Responses appendix | `25/25` strict clean | `0/25` | greedy decoding fixed 20B but did not rescue 120B fallback |
| deterministic Chat Completions | `25/25` tool-calls present | `0/25` | compatibility probe also failed on 120B fallback |
| launch shape | baseline `32768` | forced fallback from `65536` to `32768` | 120B baseline shape itself was unstable |

## Required Comparison Answers

### 1. On `/v1/responses`, is the initial tool-emission miss rate materially worse on 20B than 120B?

No. The comparison does not support that framing. `120B` failed at the transport/backend level before it could demonstrate a lower miss rate.

### 2. Does 120B also show reasoning-only/no-call misses under the same config?

Not in a directly comparable way. The dominant `120B` failure class was earlier than protocol shape: transport resets and refusals.

### 3. Is storage/retrieval equally stable on both?

No.

- `20B`: retrieval stable enough to score (`95/100`)
- `120B`: no retrievable stored responses because no valid initial Responses objects were produced

### 4. Is follow-up continuation equally stable on both once the first call is valid?

No.

- `20B`: stable on every attemptable trial
- `120B`: no attemptable trials

### 5. Does deterministic Chat Completions reduce the gap, eliminate the gap, or leave a large gap?

It leaves a large gap.

- `20B`: deterministic Chat Completions was clean
- `120B`: deterministic Chat Completions also failed at transport level

### 6. Based on the evidence, is the remaining problem mainly 20B robustness, shared backend/Harmony behavior, or unresolved caller-contract mismatch?

Shared backend/runtime behavior contributes materially and dominates this pass. The current stack did not produce a clean `120B` comparison path at all.

## Failure Attribution

### Store/config

- `20B`: store semantics were not the primary blocker
- `120B`: store could not be meaningfully exercised because the path failed before valid stored responses existed

### Protocol-shape drift

- `20B`: yes, on the main non-deterministic Responses matrix (`10/100` reasoning-only/no-call)
- `120B`: not meaningfully scoreable because transport-level failure happened first

### Caller-contract compatibility

- `20B`: deterministic Chat Completions looked clean but remained secondary
- `120B`: deterministic Chat Completions also failed, so the issue was not limited to caller-contract mismatch

### Model-semantic robustness

- `20B`: weaker than ideal on the non-deterministic initial Responses turn
- `120B`: this pass does **not** support calling `120B` “more robust”; the stack failed before semantic behavior could be established

## Root Cause Framing

This pass separates two different failure classes:

1. `20B` semantic weakness on non-deterministic first-turn Responses tool emission
2. `120B` runtime/transport instability on the same experimental stack, including:
   - inability to keep the intended `65536` shape as the scored serving baseline
   - failure to sustain stable Responses or Chat Completions traffic even on the `32768` fallback

That means:

- the stack is not clean enough to use `120B` as the control that exonerates the backend
- the residual `20B` weakness is real, but it is not the whole story

## Verdict

`GPT-OSS tool unreliability is mainly shared backend/Harmony behavior on current stack`

## Production Recommendation

Keep `main` as the only production-approved tool lane. Do not promote GPT-OSS `20B` or GPT-OSS `120B` for production tool use from this pass. `20B` remains usable enough to show partial backend tool success, but still weak on non-deterministic initial Responses tool emission. `120B` failed more fundamentally on the current stack and did not provide a clean control comparison. The next GPT-OSS follow-up should focus on `120B` runtime stability and serving-shape viability before any additional lane-promotion discussion.

## Evidence Pointers

- raw 20B artifact: `/tmp/gptoss_ab_raw_20b.json`
- raw 120B artifact: `/tmp/gptoss_ab_raw_120b.json`
- working notes and representative excerpts:
  - [SCRATCH_PAD.md](/home/christopherbailey/homelab-llm/SCRATCH_PAD.md)

## Key Takeaways for Review

- The pass completed its intended comparison structure, but the `120B` side only after a forced fallback, and even then the result was transport-level failure.
- The strongest evidence from this pass is negative control evidence against the “it’s just 20B being weak” explanation.
- The next investigation should be narrower:
  - why `120B` baseline `65536` did not stabilize on this path
  - why the `32768` fallback listener reset/refused connections under scored traffic
  - whether the failure is in `vllm-metal`, Harmony handling, or GPT-OSS `120B` serving on this runtime specifically

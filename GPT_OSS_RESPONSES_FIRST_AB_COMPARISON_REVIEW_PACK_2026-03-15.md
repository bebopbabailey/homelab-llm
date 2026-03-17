# GPT-OSS Responses-First A/B Comparison Review Pack

Date: `2026-03-15`  
Host scope: Mini orchestrating Studio experimental `8120` and `8122`  
Audience: associate / senior review  
Primary truth path: `/v1/responses`  
Secondary compatibility probe only: `/v1/chat/completions`

## Executive Summary

This pass was the first clean semantic comparison after the 120B-only
stabilization work proved that GPT-OSS `120B` could hold a stable serving
surface on the current Studio `vllm-metal` stack.

The goal was narrow:

- compare GPT-OSS `20B` and GPT-OSS `120B` on the documented GPT-OSS
  tool-capable Responses path
- keep the work serialized, Studio-local, and non-streaming
- separate semantic tool weakness from store/runtime or transport failures

The result:

- `120B` successfully reproduced the validated `65536` control shape
- `20B` is materially weaker than `120B` on the primary non-deterministic
  `/v1/responses` initial tool-emission step
- but `120B` is not perfectly clean either; it still showed a small number of
  protocol-shape drift cases
- deterministic `/v1/responses` eliminated the observed gap in this pass

Final verdict used for this pass:

- `GPT-OSS tool unreliability is mixed: 20B is weaker, but shared backend behavior still contributes`

This is not a “GPT-OSS is dead” result. It is a much narrower statement:

- the remaining main-path weakness is mostly on `20B`
- but the backend/runtime path is still not immaculate, because `120B` is not
  perfectly protocol-clean either

## Scope and Guardrails

This pass intentionally stayed narrow.

Allowed and used:

- experimental ports only:
  - `8120` for `20B`
  - `8122` for `120B`
- one experimental GPT server at a time
- Studio-local probing only for scored HTTP traffic
- non-streaming only
- task tracking and evidence capture only

Explicitly not changed:

- canonical lane assignments on `8100`, `8101`, `8102`
- LiteLLM aliases
- OpenCode routing
- launchd policy
- `mlxctl` code
- repo config beyond `NOW.md` and `SCRATCH_PAD.md`

## Why This Pass Existed

Prior local evidence had already established:

- GPT-OSS `20B` was not dead
- the earlier `8120` work showed real function-calling behavior on the
  documented GPT-OSS path
- deterministic decoding improved `20B` materially
- the earlier broad A/B pass could not cleanly attribute the failure because the
  `120B` half had transport/runtime problems before becoming a valid control
- the dedicated 120B-only stabilization pass then proved that `120B` could
  serve as a valid control on the current stack when isolated and given enough
  headroom

That changed the question from:

- “is GPT-OSS viable?”

to:

- “on the documented Responses path, how much weaker is `20B` than a now-valid
  `120B` control?”

## Source Basis

### Local evidence

- [SCRATCH_PAD.md](/home/christopherbailey/homelab-llm/SCRATCH_PAD.md)
- [GPT_OSS_20B_VS_120B_AB_VERIFICATION_REVIEW_PACK_2026-03-15.md](/home/christopherbailey/homelab-llm/GPT_OSS_20B_VS_120B_AB_VERIFICATION_REVIEW_PACK_2026-03-15.md)
- [GPT_OSS_8120_RESPONSES_STORE_REVIEW_PACK_2026-03-15.md](/home/christopherbailey/homelab-llm/GPT_OSS_8120_RESPONSES_STORE_REVIEW_PACK_2026-03-15.md)
- raw artifacts under:
  - `/tmp/20260315T202337Z-gptoss-ab-compare/`

### Current upstream interpretation anchors

- vLLM GPT-OSS recipe:
  - <https://docs.vllm.ai/projects/recipes/en/latest/OpenAI/GPT-OSS.html>
- vLLM Responses serving / store behavior:
  - <https://docs.vllm.ai/en/latest/api/vllm/entrypoints/openai/responses/serving/>
- OpenAI GPT-OSS verification guidance:
  - <https://developers.openai.com/cookbook/articles/gpt-oss/verifying-implementations/>

This report uses those sources as the contract/interpretation frame and uses the
local raw artifacts as the actual evidence basis.

## Canonical Headroom Method Used

This pass standardized one headroom metric and used it consistently before both
model-launch decisions:

- `approx_reclaimable_gb`

Definition:

- `(Pages free + Pages inactive + Pages speculative) * 16384 / 1024^3`

Exact command family used each time:

```bash
ssh studio 'vm_stat'
ssh studio '/usr/bin/python3 - <<\"PY\"
import subprocess, re
out=subprocess.check_output([\"vm_stat\"], text=True)
page_size=16384
m={}
for line in out.splitlines():
    mm=re.match(r\"Pages (free|active|inactive|speculative|wired down):\\s+(\\d+)\\.\", line)
    if mm:
        m[mm.group(1)] = int(mm.group(2))
free=(m.get(\"free\",0)+m.get(\"inactive\",0)+m.get(\"speculative\",0))*page_size/1024/1024/1024
print(f\"approx_reclaimable_gb {free:.2f}\")
PY'
ssh studio 'lsof -nP -iTCP:8100-8102 -sTCP:LISTEN || true'
ssh studio 'lsof -nP -iTCP:8120,8122 -sTCP:LISTEN || true'
ssh studio '/Users/thestudio/.venv-vllm-metal/bin/python - <<\"PY\"
import importlib.metadata as m
for name in (\"vllm\", \"vllm-metal\", \"transformers\", \"mlx-lm\"):
    print(name, m.version(name))
PY'
```

Fresh results:

- before `20B`:
  - `approx_reclaimable_gb 101.67`
- before `120B`, after `20B` teardown and cooldown but with canonical trio still up:
  - `approx_reclaimable_gb 70.68`
- before `120B`, after stopping canonical listeners:
  - `approx_reclaimable_gb 167.12`

Decision path:

- the pass used the heavier validated `120B` control requirement to decide
  topology
- the threshold floor was:
  - `81.17GB` prior known need
  - plus `10GB` safety margin
  - equals `91.17GB`
- `20B` was allowed to run with canonical listeners still up because the initial
  measurement was clearly above the floor
- `120B` was not launched with the trio up because the second measurement was
  clearly below the floor
- canonical listeners were stopped only before the `120B` control run

## Runtime and Topology Pre-State

Before the pass:

- `mlxctl studio-cli-sha` showed local/Studio parity
- canonical trio was healthy:
  - `8100`: serving / converged
  - `8101`: serving / converged
  - `8102`: serving / converged
- current canonical render remained:
  - `8100` GPT-OSS `120B`: `65536`
  - `8101` Llama 3.3: `65536`
  - `8102` GPT-OSS `20B`: `32768`
- direct `/v1/models` probes on `8100`, `8101`, `8102` all returned `200`
- runtime tuple remained:
  - `vllm 0.14.1`
  - `vllm-metal 0.1.0`
  - `transformers 4.57.6`
  - `mlx-lm 0.29.1`

## Experimental Contracts

### 20B

Exact launch:

```bash
VLLM_METAL_MEMORY_FRACTION=auto \
VLLM_ENABLE_RESPONSES_API_STORE=1 \
/Users/thestudio/.venv-vllm-metal/bin/vllm serve \
  /Users/thestudio/models/hf/models--mlx-community--gpt-oss-20b-MXFP4-Q4/snapshots/f356f2747216d7e98fee755df25987459fc19089 \
  --served-model-name mlx-gpt-oss-20b-mxfp4-q4-exp-compare \
  --host 127.0.0.1 \
  --port 8120 \
  --max-model-len 32768 \
  --chat-template /opt/mlx-launch/templates/gpt-oss-20b-chat_template.jinja \
  --default-chat-template-kwargs '{"enable_thinking": false, "reasoning_effort": "low"}' \
  --enable-auto-tool-choice \
  --tool-call-parser openai \
  --no-async-scheduling
```

### 120B

Exact control launch:

```bash
VLLM_METAL_MEMORY_FRACTION=auto \
VLLM_ENABLE_RESPONSES_API_STORE=1 \
/Users/thestudio/.venv-vllm-metal/bin/vllm serve \
  /Users/thestudio/models/hf/models--mlx-community--gpt-oss-120b-MXFP4-Q4/snapshots/bce781bef0f2fc85ed4e575af74054f5aad73ddd \
  --served-model-name mlx-gpt-oss-120b-mxfp4-q4-exp-compare \
  --host 127.0.0.1 \
  --port 8122 \
  --max-model-len 65536 \
  --chat-template /opt/mlx-launch/templates/gpt-oss-120b-chat_template.jinja \
  --default-chat-template-kwargs '{"enable_thinking": false, "reasoning_effort": "low"}' \
  --enable-auto-tool-choice \
  --tool-call-parser openai \
  --no-async-scheduling
```

Important nuance from the current installed `vllm` source:

- for GPT-OSS on the Responses path, current `serving_responses.py` says it
  ignores `--enable-auto-tool-choice` and always enables tool use
- this flag was kept for parity with prior experiments
- it should not be over-credited as the reason the Responses path worked

## Probe Discipline

All scored traffic was:

- non-streaming
- Studio-local
- run through a single temporary Studio-local stdlib Python harness
- written to raw JSON artifacts under:
  - `/tmp/20260315T202337Z-gptoss-ab-compare/`

Warm-up gate for both models:

- `5` non-scored `/v1/responses` noop-tool trials
- required:
  - at least `3/5` valid callable responses
  - at least `3/5` successful retrievals
  - no transport failures
  - process alive
  - port listening

Main scored matrix for both models:

- `100` `/v1/responses` noop-tool initial-turn trials
- retrieval after every successful initial trial
- follow-up continuation only for attemptable trials
- health checkpoints at:
  - `25`
  - `50`
  - `75`

Appendices for both models:

- deterministic `/v1/responses`: `25` trials, `temperature=0.0`
- deterministic `/v1/chat/completions`: `25` trials, `temperature=0.0`

## 20B Results

### Warm-up

- callable responses: `4/5`
- retrieval success: `5/5`
- transport failures: `0`
- process alive: yes
- port listening: yes

### Main `/v1/responses`

- `shape_success_rate`: `73/100`
- `broad_semantic_success_rate`: `73/100`
- `strict_protocol_clean_success_rate`: `72/100`
- `reasoning_only_no_call_rate`: `13/100`
- `transport_failure_count`: `0`

### Retrieval

- `retrieval_success_rate`: `96/100`
- `retrieval_404_count`: `0`
- `invalid_request_count`: `0`
- `identity_mismatch_count`: `0`

### Follow-up

- `attemptable_count`: `80`
- `follow_up_shape_success_rate`: `80/80`
- `follow_up_semantic_success_rate`: `80/80`
- `terminal_continuation_rate`: `80/80`
- `another_tool_call_requested_count`: `0`

### Deterministic `/v1/responses`

- `shape_success_rate`: `25/25`
- `strict_protocol_clean_success_rate`: `25/25`
- `reasoning_only_no_call_rate`: `0/25`
- `transport_failure_count`: `0`

### Deterministic Chat Completions

- `http_200_rate`: `25/25`
- `tool_calls_present_rate`: `25/25`
- `content_null_with_valid_tool_calls_count`: `25`
- `content_null_with_no_tool_calls_count`: `0`
- `http_500_count`: `0`
- `no_tool_failure_count`: `0`

### 20B failure shape

The main non-deterministic `20B` failures were not transport failures. They
were mostly:

- reasoning-only / no-call turns
- a small retrieval miss delta
- a small amount of protocol-shape drift
- two `400` initial create failures in the main matrix

Representative protocol drift case:

```json
{"name":"noop","arguments":{}}
```

returned as the `arguments` string inside a `function_call`, which is not the
required clean empty-object argument contract.

## Hard Teardown Boundary After 20B

This pass explicitly enforced a clean boundary before `120B`:

- `20B` parent process was stopped
- `8120` listener was cleared
- a fixed `30s` cooldown was observed
- headroom was re-measured before the `120B` decision

This matters because Responses store retains state in memory until process exit.

## 120B Control Reproduction and Results

### Control reproduction

The validated `120B` `65536` control shape reproduced successfully on `8122`
after the canonical trio was stopped for headroom.

No fallback was needed.

### Warm-up

- callable responses: `5/5`
- retrieval success: `5/5`
- transport failures: `0`
- process alive: yes
- port listening: yes

### Main `/v1/responses`

- `shape_success_rate`: `96/100`
- `broad_semantic_success_rate`: `96/100`
- `strict_protocol_clean_success_rate`: `96/100`
- `reasoning_only_no_call_rate`: `0/100`
- `transport_failure_count`: `0`

### Retrieval

- `retrieval_success_rate`: `100/100`
- `retrieval_404_count`: `0`
- `invalid_request_count`: `0`
- `identity_mismatch_count`: `0`

### Follow-up

- `attemptable_count`: `99`
- `follow_up_shape_success_rate`: `99/99`
- `follow_up_semantic_success_rate`: `99/99`
- `terminal_continuation_rate`: `99/99`
- `another_tool_call_requested_count`: `0`

### Deterministic `/v1/responses`

- `shape_success_rate`: `25/25`
- `strict_protocol_clean_success_rate`: `25/25`
- `reasoning_only_no_call_rate`: `0/25`
- `transport_failure_count`: `0`

### Deterministic Chat Completions

- `http_200_rate`: `25/25`
- `tool_calls_present_rate`: `25/25`
- `content_null_with_valid_tool_calls_count`: `25`
- `content_null_with_no_tool_calls_count`: `0`
- `http_500_count`: `0`
- `no_tool_failure_count`: `0`

### 120B non-perfect cases

`120B` was very strong, but not perfectly protocol-clean.

Raw artifact inspection showed four non-perfect main-matrix cases:

1. one `mcp_call` drift case:
   - `type: "mcp_call"`
   - `name: "<|constrain|>User"`
   - arguments carrying `functions.noop`
2. three malformed `function_call` argument cases:
   - `{"": {}}`

That means `120B` is a valid control on this stack, but not a perfectly clean
one.

## Direct Comparison

### Main `/v1/responses`

- `20B` strict protocol-clean:
  - `72/100`
- `120B` strict protocol-clean:
  - `96/100`
- delta:
  - `24/100` in favor of `120B`

- `20B` reasoning-only / no-call:
  - `13/100`
- `120B` reasoning-only / no-call:
  - `0/100`
- delta:
  - `13/100` in favor of `120B`

### Retrieval

- `20B` retrieval success:
  - `96/100`
- `120B` retrieval success:
  - `100/100`

There were no retrieval `404`, invalid-request, or identity-mismatch failures
on either model.

### Follow-up continuation

- `20B` attemptable:
  - `80`
- `120B` attemptable:
  - `99`

Once attemptable:

- both models were perfect on follow-up continuation

This is important:

- the main gap is not follow-up continuation
- the main gap is initial-turn tool emission on non-deterministic Responses

### Deterministic `/v1/responses`

- `20B`: `25/25`
- `120B`: `25/25`

Deterministic decoding eliminated the observed gap in this pass.

### Deterministic Chat Completions

Both models were also clean here:

- `25/25` HTTP `200`
- `25/25` tool calls present
- `0` `500`
- `0` null-content-without-tool

This supports compatibility, but does **not** override the Responses verdict.

## Failure Attribution

### Headroom / host-capacity

Headroom mattered materially for `120B`.

- with the trio still up after the `20B` run and cooldown:
  - headroom was insufficient for the validated `120B` control shape
- after stopping canonical listeners:
  - headroom became ample

So headroom policy did matter, but it did not invalidate the semantic
comparison. It enabled the control reproduction.

### Launch instability

Not observed in this clean pass.

### Store / retrieval

There was a small real delta:

- `20B`: `96/100`
- `120B`: `100/100`

That should be attributed to store/retrieval stability first, not semantic
tool weakness.

### Transport / runtime

No transport failures occurred on either main matrix.

This is the key difference from the earlier failed broad A/B pass:

- the clean serialized design removed transport collapse from the comparison

### Protocol-shape drift

Still present on both models.

- worse on `20B`
- still present on `120B`

This is why the final verdict is not “20B only” despite the large semantic gap.

### Semantic tool robustness

This is where the dominant difference lives.

`20B` is materially weaker than `120B` on non-deterministic initial Responses
tool emission.

But deterministic decoding cleaned that up dramatically.

That means the weakness is strongly concentrated in `20B`’s non-deterministic
semantic robustness on the primary path.

### Caller-contract compatibility

Deterministic Chat Completions looked clean on both models, but that remains a
secondary observation only.

Current GPT-OSS guidance still points to `/v1/responses` as the primary truth
path, so Chat Completions should not drive the verdict.

## Verdict

Exact verdict for this pass:

- `GPT-OSS tool unreliability is mixed: 20B is weaker, but shared backend behavior still contributes`

Why not “20B-specific robustness”?

- because `120B` was not perfect:
  - it still had four protocol-shape drift cases in the main matrix

Why not “shared backend/Harmony behavior”?

- because the gap is too large to ignore:
  - `72/100` vs `96/100`
  - `13/100` reasoning-only / no-call vs `0/100`

Why “mixed” fits best:

- `20B` is clearly weaker on the main non-deterministic Responses path
- but the stack is still not perfectly clean even for `120B`

## What This Means for the Next Pass

This pass does **not** justify a broad production promotion.

What it does justify:

- keep using the validated `120B` `65536` control shape for future comparison work
- focus the next narrow GPT-OSS pass on:
  - residual Responses protocol-shape drift on the current stack
  - `20B` non-deterministic initial-turn tool robustness

The key takeaway is narrower than the incident framing from earlier passes:

- the stack can now sustain a clean enough control
- the remaining weakness is mostly on `20B`
- but not exclusively on `20B`

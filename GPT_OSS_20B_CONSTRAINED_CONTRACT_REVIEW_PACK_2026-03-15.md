# GPT-OSS 20B Constrained-Contract Review Pack

Date: `2026-03-15`  
Host scope: Mini orchestrating Studio experimental `8120`  
Audience: associate / senior review  
Primary truth path: `/v1/responses`  
Secondary compatibility probe only: `/v1/chat/completions`

## Executive Summary

This pass was a narrow `20B`-only follow-up to the clean serialized
Responses-first A/B comparison.

The question was no longer whether GPT-OSS `20B` was weaker than `120B`. That
had already been established. The narrower question was:

- can GPT-OSS `20B` be made operationally boring enough for a deliberately
  constrained experimental tool-use contract on the current Studio
  `vllm-metal` stack?

The result:

- under the baseline non-deterministic `/v1/responses` contract, `20B` remained
  operationally noisy on the first tool-emission turn
- once the first turn was valid, retrieval and follow-up continuation remained
  clean
- under deterministic `/v1/responses` with `temperature=0.0`, `20B` became
  fully clean in this pass:
  - `50/50` strict protocol-clean initial turns
  - `0/50` reasoning-only / no-call
  - `50/50` retrieval success
  - `50/50` follow-up semantic success
  - `0` transport failures

That supports a narrow conclusion:

- GPT-OSS `20B` is usable for a constrained experimental tool contract on the
  current stack, but only under a much tighter contract than the general
  non-deterministic path

The constrained contract supported by this pass is:

- `/v1/responses` only
- non-streaming only
- deterministic decoding (`temperature=0.0`)
- experimental callers only

This is not a production-promotion statement.

## Scope and Guardrails

This pass intentionally stayed narrow.

Allowed and used:

- one experimental server only
- experimental `8120` on Studio loopback
- Studio-local probing only for scored traffic
- non-streaming only
- task tracking and evidence capture only

Explicitly not changed:

- canonical lane assignments
- LiteLLM aliases
- OpenCode routing
- launchd policy
- `mlxctl` code
- repo config beyond `NOW.md` and `SCRATCH_PAD.md`

## Why This Pass Existed

The latest local evidence already established:

- GPT-OSS `120B` is a valid control under isolated/headroom-cleared conditions
- GPT-OSS `20B` is materially weaker than `120B` on the non-deterministic
  initial `/v1/responses` tool-emission step
- once the first turn is valid, `20B` follow-up continuation is already clean
- deterministic `/v1/responses` eliminated the observed `20B` vs `120B` gap in
  the latest pass
- deterministic Chat Completions also looked clean, but `/v1/responses`
  remains the primary backend truth path

That changed the next useful question from:

- “is `20B` viable in general?”

to:

- “is there a constrained contract where `20B` is operationally boring enough
  for experimental callers?”

## Source Basis

### Local evidence

- [GPT_OSS_RESPONSES_FIRST_AB_COMPARISON_REVIEW_PACK_2026-03-15.md](/home/christopherbailey/homelab-llm/GPT_OSS_RESPONSES_FIRST_AB_COMPARISON_REVIEW_PACK_2026-03-15.md)
- [SCRATCH_PAD.md](/home/christopherbailey/homelab-llm/SCRATCH_PAD.md)
- raw artifacts under:
  - `/tmp/20260315T215135Z-gptoss-20b-constrained/`

### Current upstream interpretation anchors

- vLLM GPT-OSS recipe:
  - <https://docs.vllm.ai/projects/recipes/en/latest/OpenAI/GPT-OSS.html>
- vLLM Responses serving / store behavior:
  - <https://docs.vllm.ai/en/latest/api/vllm/entrypoints/openai/responses/serving/>
- OpenAI GPT-OSS verification guidance:
  - <https://developers.openai.com/cookbook/articles/gpt-oss/verifying-implementations/>

This report uses those sources as the contract/interpretation frame and uses
the local raw artifacts as the evidence basis.

## Preflight and Runtime State

Before the experimental pass:

- `mlxctl studio-cli-sha` showed local/Studio parity
- canonical trio remained healthy:
  - `8100`: serving / converged
  - `8101`: serving / converged
  - `8102`: serving / converged
- direct `/v1/models` probes on `8100`, `8101`, `8102` all returned `200`
- current runtime tuple remained:
  - `vllm 0.14.1`
  - `vllm-metal 0.1.0`
  - `transformers 4.57.6`
  - `mlx-lm 0.29.1`

## Canonical Headroom Method Used

This pass reused the same standardized headroom metric from the clean A/B pass:

- `approx_reclaimable_gb`

Definition:

- `(Pages free + Pages inactive + Pages speculative) * 16384 / 1024^3`

Exact command family:

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
ssh studio 'lsof -nP -iTCP:8120 -sTCP:LISTEN || true'
ssh studio '/Users/thestudio/.venv-vllm-metal/bin/python - <<\"PY\"
import importlib.metadata as m
for name in (\"vllm\", \"vllm-metal\", \"transformers\", \"mlx-lm\"):
    print(name, m.version(name))
PY'
```

Fresh result before launch:

- `approx_reclaimable_gb 86.84`

Decision path:

- canonical listeners were kept up
- reason: this was a `20B`-only pass, the experimental `8120` port was clear,
  and fresh headroom remained consistent with the previously known-good
  isolated `20B` experimental shape

No canonical stop or restore was required in this pass.

## Exact Experimental Contract

Exact launch:

```bash
VLLM_METAL_MEMORY_FRACTION=auto \
VLLM_ENABLE_RESPONSES_API_STORE=1 \
/Users/thestudio/.venv-vllm-metal/bin/vllm serve \
  /Users/thestudio/models/hf/models--mlx-community--gpt-oss-20b-MXFP4-Q4/snapshots/f356f2747216d7e98fee755df25987459fc19089 \
  --served-model-name mlx-gpt-oss-20b-mxfp4-q4-exp-constrained \
  --host 127.0.0.1 \
  --port 8120 \
  --max-model-len 32768 \
  --chat-template /opt/mlx-launch/templates/gpt-oss-20b-chat_template.jinja \
  --default-chat-template-kwargs '{"enable_thinking": false, "reasoning_effort": "low"}' \
  --enable-auto-tool-choice \
  --tool-call-parser openai \
  --no-async-scheduling
```

Important nuance for interpretation:

- current installed `vllm` Responses serving code for GPT-OSS ignores
  `--enable-auto-tool-choice` and always enables tool use on the Responses path
- the flag was kept only for parity with prior experiments
- this report does not credit that flag as the causal lever

The actual lever under test here was decoding policy, not tool-enable flags.

## Warm-up Gate

Before each scored Responses matrix, the pass required:

- `5` non-scored warm-up trials
- at least `3/5` broad semantic successes
- at least `3/5` successful retrievals
- `0` transport failures
- process alive
- port listening

Both baseline and deterministic warm-up gates passed cleanly:

### Baseline warm-up (`5`)

- broad semantic: `5/5`
- strict protocol-clean: `5/5`
- retrieval success: `5/5`
- follow-up semantic: `5/5`
- transport failures: `0`

### Deterministic warm-up (`5`, `temperature=0.0`)

- broad semantic: `5/5`
- strict protocol-clean: `5/5`
- retrieval success: `5/5`
- follow-up semantic: `5/5`
- transport failures: `0`

That meant the scored blocks began from a real stable serving surface, not from
a single lucky response.

## Main Matrix Design

### Primary request surface

- `/v1/responses`

### Tool schema

Main truth test used the same noop tool schema as the earlier A/B pass:

```json
{
  "model": "mlx-gpt-oss-20b-mxfp4-q4-exp-constrained",
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

### Decoding policies tested

1. baseline non-deterministic policy
2. deterministic policy with `temperature=0.0`

### Trial counts

- baseline `/v1/responses`: `50`
- deterministic `/v1/responses`: `50`

The pass intentionally did not build a larger entropy grid. The point was to
measure whether deterministic decoding was sufficient to make the contract
boring enough.

## Main Results

## Baseline Non-Deterministic `/v1/responses`

### Score summary

- shape success: `39/50`
- broad semantic success: `35/50`
- strict protocol-clean success: `35/50`
- reasoning-only / no-call: `11/50`
- protocol-shape drift: `4/50`
- transport failures: `0`

### Retrieval

- retrieval success: `47/47` created responses
- retrieval `404`: `0`
- invalid request: `0`
- identity mismatch: `0`
- retrieval transport failures: `0`

### Follow-up continuation

- attemptable count: `39`
- follow-up shape success: `39/39`
- follow-up semantic success: `39/39`
- terminal continuation returned: effectively `39/39`
- another tool call requested: `0`

### Interpretation

This reproduced the already-known weakness pattern on `20B`:

- the first turn remained noisy
- the noise was concentrated in:
  - reasoning-only / no-call misses
  - protocol-shape drift
  - a small number of parser-level `400` failures
- once the first turn became a real callable `function_call`, the backend
  remained clean enough for retrieval and follow-up continuation

In other words:

- `20B` did not fail because the whole backend collapsed
- it failed because first-turn tool emission under the baseline policy was not
  operationally boring

## Representative Baseline Failures

The most useful baseline failure examples were:

- trial `6`:
  - malformed args wrapper `{"name":"noop","arguments":{}}`
- trial `10`:
  - malformed args payload `{"foo":"bar"}`
- trial `39`:
  - malformed args payload `{"args":{}}`
- trials `18`, `33`, `46`:
  - initial request returned `400 Bad Request` with parser-level messages like:
    - `unexpected tokens remaining in message header: Some("<|constrain|>functions.noop:")`
    - `unexpected tokens remaining in message header: Some("to=functions.noop>{}</assistant<|channel|>commentary")`
    - `unexpected tokens remaining in message header: Some("to=functions.noop")`

These are important because they are not store failures and not transport
failures. They are part of the first-turn tool-emission / protocol-shape
problem.

## Deterministic `/v1/responses` (`temperature=0.0`)

### Score summary

- shape success: `50/50`
- broad semantic success: `50/50`
- strict protocol-clean success: `50/50`
- reasoning-only / no-call: `0/50`
- protocol-shape drift: `0/50`
- transport failures: `0`

### Retrieval

- retrieval success: `50/50`
- retrieval `404`: `0`
- invalid request: `0`
- identity mismatch: `0`
- retrieval transport failures: `0`

### Follow-up continuation

- attemptable count: `50`
- follow-up shape success: `50/50`
- follow-up semantic success: `50/50`
- terminal continuation returned: effectively `50/50`
- another tool call requested: `0`

### Interpretation

Deterministic decoding removed the observed weakness completely in this pass.

This matters because the earlier A/B comparison had already suggested that
deterministic decoding was the main lever. This pass confirmed it directly on a
larger `20B`-only constrained matrix.

Operationally, the important outcome is:

- the backend was not merely “less bad”
- it became clean enough to satisfy a real constrained experimental contract

## Conditional Second-Schema Appendix

This pass intentionally allowed a second tiny schema only if deterministic noop
still left ambiguity around empty-object args.

Trigger conditions for the appendix were:

- deterministic strict protocol-clean success `< 49/50`, or
- deterministic reasoning-only / no-call `> 0/50`, or
- deterministic retrieval success `< 49/50`, or
- any malformed-args drift at all under deterministic noop

That appendix was **not** triggered, because deterministic noop was fully clean:

- `50/50` strict protocol-clean
- `0/50` reasoning-only / no-call
- `50/50` retrieval success
- `0` deterministic malformed-args drift

Interpretation:

- this pass did not need a second schema to rescue the result
- there was no remaining evidence that empty-object args were still the live
  landmine once decoding was constrained to deterministic mode

## Secondary Compatibility Appendix: Deterministic Chat Completions

This appendix remained explicitly secondary.

Request family:

- `/v1/chat/completions`
- non-streaming
- deterministic `temperature=0.0`
- same noop tool schema

Trial count:

- `10`

### Score summary

- HTTP `200`: `10/10`
- tool calls present: `10/10`
- `content: null` with valid tool calls: `10/10`
- `content: null` with no tool calls: `0/10`
- `500`: `0`
- no-tool failures: `0`

### Interpretation

This supports a compatibility observation:

- `20B` still looks caller-compatible on a tightly constrained deterministic
  Chat Completions shape

But it does **not** override the Responses verdict.

The current GPT-OSS guidance still treats:

- `/v1/responses` as the primary path
- Chat Completions as the compatibility surface

So the main decision in this report is based on `/v1/responses`.

## Failure Attribution

This pass needs careful attribution because the goal was to distinguish
operational boringness from vague “seems better” claims.

### Headroom / host-capacity

- not a blocker in this pass
- fresh headroom with canonical trio up remained sufficient for the isolated
  `20B` experimental lane

### Launch instability

- not observed
- readiness on `8120` reproduced cleanly

### Store / retrieval

- baseline:
  - no retrieval `404`
  - no invalid-request retrieval failures
  - no identity mismatch
  - retrieval succeeded on all created responses
- deterministic:
  - fully clean `50/50`

This means store/runtime did **not** dominate the constrained deterministic
result.

### Transport / runtime

- no transport failures in either scored Responses block
- no listener death
- no process exit

### Protocol-shape drift

- baseline:
  - `4/50`
- deterministic:
  - `0/50`

This is a core part of the first-turn weakness story and should not be
collapsed into “tool selection success.”

### Semantic tool robustness

- baseline non-deterministic:
  - still weak enough to be operationally noisy
- deterministic:
  - fully clean in this pass

This means the remaining weakness is mainly about the unconstrained
non-deterministic first-turn contract, not about the model being incapable of
tool use under all conditions.

### Caller-contract compatibility

- deterministic Chat Completions was clean again
- but remained secondary

This supports a compatibility observation, not the backend truth verdict.

## Decision Against the Requested Outcomes

The pass defined three possible outcomes:

1. `20B` is usable for a constrained experimental tool contract
2. `20B` is still too unstable even under constrained settings
3. `20B` remains backend-capable but should stay plain-chat only because the caller contract is still wrong

### Outcome reached

Outcome `1` was reached.

Reason:

- deterministic strict protocol-clean success: `50/50`
- deterministic reasoning-only / no-call: `0/50`
- deterministic retrieval success: `50/50`
- deterministic follow-up semantic success: `50/50`
- transport failures: `0`

The pass also included the guardrail that if deterministic tool emission was
clean but retrieval/store misses recurred, the result should not be described
as a semantic failure.

That guardrail did not trigger here, because retrieval/store stayed clean in
the deterministic block.

## Final Verdict

GPT-OSS `20B` is usable for a constrained experimental tool contract on the
current Studio `vllm-metal` stack, under this exact candidate contract:

- `/v1/responses` only
- non-streaming only
- deterministic `temperature=0.0`
- experimental callers only

This is a backend-truth result, not a production promotion.

## Production / Operational Recommendation

Keep `20B` out of broad production tool routing for now.

What this pass supports is narrower:

- a small experimental caller contract using deterministic `/v1/responses`
- no streaming
- no automatic assumption that the broader non-deterministic path is now safe

What it does **not** support:

- promoting `20B` to general tool-use production
- treating the baseline non-deterministic contract as fixed

If a next pass is run, it should focus on one of these two directions only:

1. a narrow caller-facing experiment using the exact constrained contract above
2. a smaller parser/protocol investigation into why baseline `20B` still emits
   malformed first-turn shapes and parser-level `400` traces

## Cleanup

After the pass:

- the experimental `8120` parent process stopped cleanly
- the `8120` listener cleared cleanly
- canonical `8100/8101/8102` listeners remained up throughout
- final direct `/v1/models` probes on `8100`, `8101`, `8102` still returned
  `200`

No canonical restore or repair step was needed.

## Artifact Index

Raw artifacts:

- `/tmp/20260315T215135Z-gptoss-20b-constrained/responses_noop_warmup_baseline.json`
- `/tmp/20260315T215135Z-gptoss-20b-constrained/responses_noop_main_baseline.json`
- `/tmp/20260315T215135Z-gptoss-20b-constrained/responses_noop_warmup_deterministic.json`
- `/tmp/20260315T215135Z-gptoss-20b-constrained/responses_noop_main_deterministic.json`
- `/tmp/20260315T215135Z-gptoss-20b-constrained/chat_noop_deterministic.json`

Repo evidence summary:

- [SCRATCH_PAD.md](/home/christopherbailey/homelab-llm/SCRATCH_PAD.md)

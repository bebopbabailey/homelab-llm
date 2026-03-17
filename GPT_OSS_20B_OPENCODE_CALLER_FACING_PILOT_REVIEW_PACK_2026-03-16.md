# GPT-OSS 20B OpenCode Caller-Facing Pilot Review Pack

Date: `2026-03-16`  
Host scope: Mini orchestrating Studio experimental `8120`  
Audience: associate / senior review  
Primary backend truth path: `/v1/responses`  
Caller surface under pilot: `OpenCode CLI` one-shot only  

## Executive Summary

This pass was the first narrow caller-facing pilot of the already-validated
GPT-OSS `20B` constrained backend contract.

That backend contract was already established locally and was not re-litigated:

- `/v1/responses` only
- non-streaming only
- `temperature=0.0`
- experimental `20B` lane only
- experimental callers only

The only question in this pass was whether one real caller surface in this repo
could preserve that contract cleanly enough to be experimentally useful without
changing production routing.

The chosen caller surface was:

- `OpenCode CLI`
- one-shot only
- non-interactive only
- routed through an authoritative local shim that enforced the contract and
  captured exact evidence

Result:

- the pilot succeeded cleanly
- plain non-tool smoke was `2/2` clean
- the primary noop-tool pilot was `10/10` clean on the caller path
- direct replay of the exact normalized backend payload was also `10/10` clean
- retrieval and follow-up were both `10/10`
- no protocol-shape drift appeared in the scored noop tool runs
- no caller/direct mismatch appeared

That supports a narrow conclusion:

- one real caller path in this repo can use the validated GPT-OSS `20B`
  constrained contract experimentally
- but only through the fixed one-shot shim path used here
- this is not a production-promotion statement

## Scope and Guardrails

This pass intentionally stayed narrow.

Used:

- one experimental model server only
- one caller surface only
- one-shot OpenCode CLI only
- `/v1/responses` only as backend truth
- non-streaming backend traffic only
- exact payload capture and direct replay control

Explicitly not changed:

- canonical lane assignments
- production LiteLLM aliases
- OpenCode production routing
- launchd policy
- `mlxctl` code
- broader UI or gateway wiring

Repo-tracked changes for the pilot:

- `platform/ops/scripts/opencode_gptoss20b_responses_pilot.py`
- `NOW.md`
- `SCRATCH_PAD.md`

## Why This Pass Existed

The previous local reports had already established:

- GPT-OSS `120B` is the valid control on the current stack
- GPT-OSS `20B` is the weaker non-deterministic tool model
- GPT-OSS `20B` becomes operationally reliable enough under the constrained
  backend contract:
  - `/v1/responses`
  - non-streaming
  - `temperature=0.0`

That changed the next useful question from:

- “is GPT-OSS `20B` broadly viable?”

to:

- “can one actual caller seam preserve the already-validated constrained
  backend contract without reintroducing the same failures?”

This report answers that narrower question.

## Source Basis

### Local evidence anchors

- [GPT_OSS_20B_CONSTRAINED_CONTRACT_REVIEW_PACK_2026-03-15.md](/home/christopherbailey/homelab-llm/GPT_OSS_20B_CONSTRAINED_CONTRACT_REVIEW_PACK_2026-03-15.md)
- [SCRATCH_PAD.md](/home/christopherbailey/homelab-llm/SCRATCH_PAD.md)
- raw pilot artifacts under:
  - `/tmp/20260316T082015Z-gptoss20b-opencode-pilot/`

### Current upstream interpretation frame

- vLLM GPT-OSS recipe:
  - <https://docs.vllm.ai/projects/recipes/en/latest/OpenAI/GPT-OSS.html>
- vLLM Responses serving/store docs:
  - <https://docs.vllm.ai/en/latest/api/vllm/entrypoints/openai/responses/serving/>
- OpenAI GPT-OSS verification guidance:
  - <https://developers.openai.com/cookbook/articles/gpt-oss/verifying-implementations/>
- OpenCode providers docs:
  - <https://opencode.ai/docs/providers>
- OpenCode issue history informing the shim-first design:
  - <https://github.com/sst/opencode/issues/930>
  - <https://github.com/sst/opencode/issues/1735>
  - <https://github.com/sst/opencode/issues/3118>

Those sources justify treating `/v1/responses` as the backend truth path and
justify not trusting native custom-provider behavior to preserve the contract
without an authoritative shim.

## Experimental Topology

### Backend

Studio experimental `20B` backend:

- host: `127.0.0.1`
- port: `8120`
- served model: `mlx-gpt-oss-20b-mxfp4-q4-exp-constrained`

Launch shape:

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

Important nuance:

- current vLLM GPT-OSS Responses serving ignores `--enable-auto-tool-choice`
  and always enables tool use on the Responses path
- the flag was kept for launch parity only
- this report does not treat that flag as the causal lever

### Caller path

Caller-facing surface:

- `OpenCode CLI`
- `opencode run`
- one-shot only
- non-interactive only

Authoritative shim:

- local script:
  - [platform/ops/scripts/opencode_gptoss20b_responses_pilot.py](/home/christopherbailey/homelab-llm/platform/ops/scripts/opencode_gptoss20b_responses_pilot.py)
- bound on Mini loopback only:
  - `127.0.0.1:8871`

The shim owned:

- endpoint selection
- non-streaming enforcement
- `temperature=0.0` enforcement
- allowed scenario enforcement
- allowed tool-schema enforcement
- `response_id` / `call_id` preservation
- exact raw payload capture
- direct replay of the exact normalized backend payload
- fail-closed behavior on unsupported shapes

### Experimental contract preserved by the shim

Actual enforced backend contract:

- backend endpoint: `/v1/responses`
- streaming: disabled
- `temperature=0.0`
- target model pinned to experimental `20B`
- narrow allowlisted prompt set only
- narrow allowlisted tool schemas only

## Preflight and Runtime State

Before launch:

- `mlxctl studio-cli-sha`: local/Studio parity matched
- `mlxctl status --checks --json`: canonical trio healthy; experimental `8120`
  was clear before launch
- runtime tuple:
  - `vllm 0.14.1`
  - `vllm-metal 0.1.0`
  - `transformers 4.57.6`
  - `mlx-lm 0.29.1`
- standardized headroom:
  - `approx_reclaimable_gb 78.73`

No canonical listeners were stopped in this pass because this was a `20B`-only
experimental pilot and headroom remained sufficient.

## What OpenCode Actually Sent

The pilot confirmed that OpenCode’s one-shot ingress did not naturally match the
validated backend contract.

Observed caller-side ingress shape at the shim:

- `POST /v1/chat/completions`
- `stream: true`
- no explicit `temperature`
- caller model id `test`
- OpenCode built-in tool inventory attached

This matters because the backend contract that had actually been validated was:

- `/v1/responses`
- non-streaming
- `temperature=0.0`
- narrow allowlisted tools only

So the shim was not incidental convenience. It was the necessary contract
preserver.

## Pilot Scenarios

### Scenario 0: Plain non-tool smoke

Prompt:

- `Reply with exactly: pilot-plain-ok`

Purpose:

- prove that OpenCode one-shot could reach the shim
- prove exact caller/shim/backend evidence capture worked end-to-end
- prove the shim could preserve a deterministic non-tool path

Trials:

- `2`

Result:

- `2/2` classified `caller_and_direct_both_clean`

### Scenario 1: Noop tool exactly once

Prompt:

- `Use the noop tool exactly once, then stop.`

Backend tool schema:

```json
{
  "type": "function",
  "name": "noop",
  "description": "noop",
  "parameters": {
    "type": "object",
    "properties": {}
  }
}
```

Trials:

- `10`

Per-trial workflow:

1. OpenCode one-shot sent its request to the shim.
2. The shim recorded the exact caller payload.
3. The shim normalized it to the exact backend `/v1/responses` payload.
4. The shim recorded the exact normalized backend payload.
5. The shim sent that payload to the backend.
6. The shim recorded the exact backend response.
7. The shim returned the caller-visible interpreted result.
8. The shim replayed the exact same normalized backend payload directly to the
   backend outside OpenCode.
9. Retrieval and follow-up were executed for successful initial tool turns.

## Raw Evidence Requirements Met

For every scored noop trial, the pilot captured:

1. exact caller -> shim payload
2. exact shim -> backend `/v1/responses` payload
3. exact backend response payload
4. exact caller-visible interpreted result

It also captured:

- direct backend replay on the same normalized payload
- retrieval response
- follow-up request/response where applicable
- timestamps

Artifacts live under:

- `/tmp/20260316T082015Z-gptoss20b-opencode-pilot/artifacts/`

Representative companion outputs live under:

- `/tmp/20260316T082015Z-gptoss20b-opencode-pilot/opencode/plain/`
- `/tmp/20260316T082015Z-gptoss20b-opencode-pilot/opencode/noop/`

## Results

### Plain non-tool smoke

- total trials: `2`
- clean classifications: `2/2`
- direct replay matched caller path: `2/2`

### Noop tool pilot

- total trials: `10`
- classification `caller_and_direct_both_clean`: `10/10`
- primary backend initial shape success: `10/10`
- primary backend broad semantic success: `10/10`
- primary backend strict protocol-clean success: `10/10`
- reasoning-only / no-call: `0/10`
- protocol-shape drift: `0/10`
- retrieval success: `10/10`
- follow-up semantic success: `10/10`
- direct replay strict protocol-clean success: `10/10`
- caller-path vs direct replay mismatch: `0/10`

No second-schema appendix was needed because noop showed:

- no malformed-args drift
- no reasoning-only / no-call misses
- no caller/direct mismatch

## Representative Evidence

### Representative normalized backend payload

```json
{
  "model": "mlx-gpt-oss-20b-mxfp4-q4-exp-constrained",
  "input": "Use the noop tool exactly once, then stop.",
  "temperature": 0.0,
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

### Representative caller-side ingress truth

Observed OpenCode caller payload characteristics on noop:

- caller route: `/v1/chat/completions`
- caller model: `test`
- caller `stream: true`
- caller `temperature`: omitted
- caller tools: OpenCode built-in inventory, not the constrained backend tool set

That is exactly why the shim had to be authoritative.

### Representative noop outcome

Caller-path backend result:

- HTTP `200`
- callable item existed
- callable type: `function_call`
- callable name: `noop`
- callable args: `{}`
- retrieval succeeded
- follow-up semantic continuation succeeded

Direct replay result:

- same outcome class on the same normalized payload

## Failure Attribution

### Backend/runtime

No backend-runtime failure was observed in the scored pilot scenarios.

Evidence:

- direct replay succeeded `10/10`
- retrieval succeeded `10/10`
- follow-up succeeded `10/10`
- Studio `8120` listener remained healthy during the run and was torn down
  cleanly afterward

### Caller adaptation

The pilot did not show caller adaptation failure in the scored path, because the
authoritative shim preserved the constrained contract cleanly.

### Contract mismatch risk

The pilot did confirm that the raw caller ingress shape did not naturally match
the validated backend contract.

Without the shim, the caller would have been trying to use:

- Chat Completions ingress
- streaming
- omitted deterministic temperature
- broader built-in tool inventory

So the successful result here is not:

- “OpenCode natively matches the backend contract”

It is:

- “OpenCode one-shot can be used experimentally through a strict contract
  enforcer that preserves the validated backend path”

## Important Evidence Nuance

The raw artifacts recorded:

- `backend_process_alive: false`
- `backend_port_listening: false`

on scored trials.

That did **not** represent a real backend failure. It was a locality bug in the
shim’s per-trial health-check path when the backend lived on Studio and the shim
lived on Mini.

Direct post-run verification showed:

- the Studio pid in `/tmp/vllm-8120-gptoss-20b-opencode-pilot.pid` was alive
- `127.0.0.1:8120` was still listening

Because initial turn, retrieval, follow-up, and direct replay all succeeded,
that health-flag bug does not change the pilot verdict. It does mean the shim’s
remote-aware health checks should be fixed before the shim is reused for a later
pass.

## Verdict

One real caller path in this repo is compatible enough with the validated
GPT-OSS `20B` constrained backend contract to be experimentally useful:

- caller surface: `OpenCode CLI`
- usage mode: one-shot only
- transport path: authoritative shim only
- backend path: `/v1/responses` only
- decoding: `temperature=0.0`
- streaming: disabled at the backend contract layer

This is a narrow experimental compatibility verdict, not a broad OpenCode
provider verdict and not a production-promotion recommendation.

## What This Does Not Mean

This pass does **not** establish any of the following:

- that OpenCode’s native custom-provider path is clean enough on its own
- that Chat Completions should become the backend truth path
- that interactive OpenCode sessions are validated
- that broader tool inventories are validated
- that production routing should change

## Recommended Next Step

If another caller-facing pass is needed, keep it narrow:

- reuse the same constrained backend contract
- fix the shim’s remote-aware health-check fields
- then test either:
  - a second tiny allowlisted tool schema, or
  - one additional one-shot caller scenario

Do not broaden into interactive OpenCode sessions or production routing changes
until the narrow shim-preserved path has been deliberately expanded and
re-verified.

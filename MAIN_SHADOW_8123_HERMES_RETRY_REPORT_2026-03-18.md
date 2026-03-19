# MAIN Shadow `8123` Resume Validation And Exposure Report

Date: 2026-03-18
Authoring host: Mini
Target host: Studio
Scope: resumed `main-shadow` validation on `192.168.1.72:8123` plus operator-only LiteLLM exposure
Verdict: `PASS and exposed`

## Executive summary

This report covers the pass that resumed `main-shadow` validation **after** the
forced-tool failures had already been narrowed down.

Key decision for this pass:
- keep `tool_choice="required"` and named forced-tool failures as known backend
  defects on the current `vllm-metal` build
- finish the rest of the lane evaluation anyway
- expose `main-shadow` only if the remaining direct-backend gates passed

Outcome:
- Studio `8123` passed:
  - startup
  - `/v1/models`
  - structured outputs
  - `tool_choice="auto"`
  - long-context sanity
  - bounded generic concurrency
  - shared-prefix branch-generation probe
- LiteLLM `main-shadow` exposure succeeded after restoring the full operator-only
  shadow env surface required by the current router
- `main`, `boost`, and `code-reasoning` remained unchanged
- public `main` was **not** promoted

Known limitation retained:
- `tool_choice="required"` remains broken
- explicit named forced-tool choice remains broken

## Runtime contract used

Host / label / bind:
- host: Studio
- label: `com.bebop.mlx-shadow.8123`
- bind: `192.168.1.72`
- port: `8123`

Runtime:
- `vllm 0.14.1`
- `vllm-metal 0.1.0`

Artifact:
- `LibraxisAI/Qwen3-Next-80B-A3B-Instruct-MLX-MXFP4`
- snapshot:
  `/Users/thestudio/models/hf/models--LibraxisAI--Qwen3-Next-80B-A3B-Instruct-MLX-MXFP4/snapshots/35386111fd494a54a4e3a3705758e280c44d9e9e`

Served model name:
- `mlx-qwen3-next-80b-mxfp4-a3b-instruct`

Command shape:

```bash
/Users/thestudio/.venv-vllm-metal/bin/vllm serve \
  /Users/thestudio/models/hf/models--LibraxisAI--Qwen3-Next-80B-A3B-Instruct-MLX-MXFP4/snapshots/35386111fd494a54a4e3a3705758e280c44d9e9e \
  --served-model-name mlx-qwen3-next-80b-mxfp4-a3b-instruct \
  --host 192.168.1.72 \
  --port 8123 \
  --max-model-len 32768 \
  --generation-config vllm \
  --no-async-scheduling \
  --enable-auto-tool-choice \
  --tool-call-parser hermes \
  --no-enable-prefix-caching
```

Environment:

```bash
VLLM_METAL_MEMORY_FRACTION=auto
PATH=/opt/homebrew/bin:/Users/thestudio/.local/bin:/Users/thestudio/.venv-vllm-metal/bin:/usr/bin:/bin:/usr/sbin:/sbin
```

## Sources used

External:
1. Qwen3-Next official card
   - <https://huggingface.co/Qwen/Qwen3-Next-80B-A3B-Instruct>
2. vLLM Qwen3-Next recipe
   - <https://docs.vllm.ai/projects/recipes/en/latest/Qwen/Qwen3-Next.html>
3. vLLM tool-calling docs
   - <https://docs.vllm.ai/en/latest/features/tool_calling/>
4. vLLM structured outputs docs
   - <https://docs.vllm.ai/en/latest/features/structured_outputs/>
5. vLLM OpenAI-compatible server docs
   - <https://docs.vllm.ai/en/latest/serving/openai_compatible_server/>
6. Upstream issue on `required` + xgrammar behavior
   - <https://github.com/vllm-project/vllm/issues/16880>
7. Upstream issue distinguishing forced-tool failure from broader tool behavior
   - <https://github.com/vllm-project/vllm/issues/20470>
8. `vllm-metal` README
   - <https://github.com/vllm-project/vllm-metal>

Repo-local:
- [runtime-lock.md](/home/christopherbailey/homelab-llm/docs/foundation/runtime-lock.md)
- [testing.md](/home/christopherbailey/homelab-llm/docs/foundation/testing.md)
- [2026-03-18-main-shadow-8123-final-no-forced-backend-retry-no-go.md](/home/christopherbailey/homelab-llm/docs/journal/2026-03-18-main-shadow-8123-final-no-forced-backend-retry-no-go.md)
- [2026-03-18-main-shadow-8123-resumed-validation-and-shadow-exposure.md](/home/christopherbailey/homelab-llm/docs/journal/2026-03-18-main-shadow-8123-resumed-validation-and-shadow-exposure.md)

## Direct backend results

### Previously established and carried forward
- `/v1/models`: PASS
- structured outputs: PASS (`5/5`)
- `tool_choice="required"`: FAIL (`0/5`)
- named forced-tool choice: FAIL (`0/5`)

These forced-tool failures remained known limitations and were not reopened in
this pass.

### Resumed validation results

#### `tool_choice="auto"`
- PASS (`10/10`)
- latencies (s):
  `7.776, 0.395, 0.373, 0.377, 0.375, 0.373, 0.377, 0.377, 0.373, 0.375`
- payload shape remained valid structured `tool_calls`

#### Long-context sanity
- PASS (`3/3`)
- latencies (s):
  `3.231, 2.306, 2.416`
- expected exact outputs:
  - `context-ok-0`
  - `context-ok-1`
  - `context-ok-2`

#### Bounded generic concurrency
- PASS
- request shape:
  - history chars: `12000`
  - one-sentence output target
  - streaming enabled for TTFT capture
- results:
  - `c1`: `ttft_p95=0.836s`, `latency_p95=1.153s`
  - `c2`: `ttft_p95=1.681s`, `latency_p95=3.166s`
  - `c4`: `ttft_p95=3.336s`, `latency_p95=4.476s`
- zero crash
- zero listener loss
- zero `5xx`
- zero timeouts

#### Shared-prefix branch-generation probe
- PASS
- shape:
  - shared prefix: ~`20k` chars
  - sibling suffix variants for candidate-style branching
  - streaming enabled for TTFT capture
- results:
  - `c2`: `ttft_p95=2.667s`, `latency_p95=4.357s`
  - `c4`: `ttft_p95=5.319s`, `latency_p95=7.169s`
- zero crash
- zero listener loss
- zero `5xx`
- zero timeouts

## LiteLLM exposure findings

### First restart failure
The first Mini exposure attempt failed because the live LiteLLM env did not
contain the full operator-only shadow env surface expected by the current
`router.yaml`.

Observed failure:
- LiteLLM startup crashed with:
  `TypeError: argument of type 'NoneType' is not iterable`

Interpretation:
- restarting LiteLLM against the current router contract exposed existing env
  drift, not a `main-shadow` backend regression

### Recovery
Recovered LiteLLM by restoring the full shadow env set from `config/env.example`:
- `MAIN_SHADOW_*`
- `MAIN_FALLBACK_SHADOW_*`
- `HELPER_SHADOW_*`
- `LLMSTER_*`

After that recovery:
- readiness returned healthy
- `/v1/models` included `main-shadow`
- `main-shadow` worked through LiteLLM

## LiteLLM validation
- readiness: PASS
- authenticated `/v1/models`: PASS
- `main-shadow` structured outputs: PASS
- `main-shadow` `tool_choice="auto"`: PASS
- `main`: PASS
- `boost`: PASS
- `code-reasoning` discovery in `/v1/model/info`: PASS

## What stayed unchanged
- public `main` still points at current `8101`
- `boost*` remained intact
- `code-reasoning` remained intact
- OpenCode defaults remained unchanged
- OpenHands contract remained unchanged

## Final interpretation

`main-shadow` is now a valid operator-only shadow lane for:
- structured outputs
- `tool_choice="auto"`
- long-context work
- bounded concurrency
- shared-prefix branch/candidate-generation traffic

It is **not** a validated forced-tool lane on the current backend build.

That means:
- operator-only `main-shadow` exposure is justified
- immediate public `main` promotion still depends on whether forced-tool
  semantics are considered mandatory for the canonical lane

## Related repo records
- [NOW.md](/home/christopherbailey/homelab-llm/NOW.md)
- [2026-03-18-main-shadow-8123-resumed-validation-and-shadow-exposure.md](/home/christopherbailey/homelab-llm/docs/journal/2026-03-18-main-shadow-8123-resumed-validation-and-shadow-exposure.md)
- [index.md](/home/christopherbailey/homelab-llm/docs/journal/index.md)

# Fast-Lane `vllm-metal` Incident Review Pack

Date: 2026-03-15  
Scope: attempts to replace the Studio `fast` lane (`8102`) with a different model family under the current `vllm-metal` / MLX runtime stack  
Audience: senior engineer / associate review and follow-on remediation design

## Executive Summary

The failed `fast`-lane replacement campaign was not one issue. It was a stack of distinct issues across:

- runtime compatibility
- MLX backend support
- model-family tool-calling behavior
- `mlxctl` control-plane truth
- LiteLLM alias drift

The three candidate families tried after the original `gpt-oss-20b` lane were:

1. `GLM-4.7-Flash`
2. `Seed-OSS-36B`
3. `Granite-20B-FunctionCalling`

All three failed for different reasons on the current stack.

Current validated state after this pass:

- `main` (`8101`) on `mlx-community/Llama-3.3-70B-Instruct-4bit` is the only lane in this branch of work that clearly satisfies the required tool-calling contract.
- direct Studio `8101` probes are good
- LiteLLM `main` and `code-reasoning` were repaired and now route to the live Llama backend correctly
- `fast` has been put back onto `mlx-community/gpt-oss-20b-MXFP4-Q4` at the runtime/process level
- but `fast` still does not satisfy the hardened readiness contract cleanly, and its current responses are often reasoning-only with `content: null`

That means:

- the rollback target for `fast` is back in place operationally
- but `fast` is not fully “boring” under the current stricter control-plane truth model
- `main` is the only currently validated tool-capable lane for OpenCode / MCP-style use

## Scope Clarification

The request text said “VLM and Seed-OSS.” The actual attempted family was `GLM-4.7-Flash`, so this report uses `GLM` consistently.

This report covers:

- the practical `fast`-lane replacement attempts
- the runtime and control-plane issues encountered
- the current state of `main` and `fast`
- the repair work needed to get the gateway back in sync with live runtime truth

This report does not attempt to:

- redesign the serving stack
- prove that no future `fast` candidate can work
- choose between a future `vllm-metal` refresh and a pure-MLX serving path

## Current Runtime Truth

### Shared Studio runtime

Observed locally on Studio shared serving env:

- `vllm 0.14.1`
- `vllm-metal 0.1.0`
- `transformers 4.57.6`
- `mlx-lm 0.29.1`

Observed locally on the dedicated GLM canary env:

- `vllm 0.14.1`
- `vllm-metal 0.1.0`
- `transformers 5.3.0.dev0`
- `mlx-lm 0.29.1`

### Current lane/process state

Observed locally:

- `8100` -> `mlx-gpt-oss-120b-mxfp4-q4`
- `8101` -> `mlx-llama-3-3-70b-4bit-instruct`
- `8102` -> `mlx-gpt-oss-20b-mxfp4-q4` at the runtime/process layer

Current control-plane nuance:

- `8101` lane state is converged and healthy
- `8102` runtime is serving GPT-OSS 20B, but lane-state reconciliation is still failed because the current readiness probe did not accept the completion shape it saw from GPT-OSS

### Current gateway truth

Before repair in this pass:

- LiteLLM `main` still pointed at stale Qwen env wiring and returned `404`
- LiteLLM `code-reasoning` also pointed at stale Qwen env wiring
- LiteLLM `fast` still routed to GPT-OSS 20B

After repair in this pass:

- `main` and `code-reasoning` now point to Llama 3.3 on `8101`
- `fast` still points to GPT-OSS 20B on `8102`

## Timeline

## 1. Original fast-lane replacement attempt

The initial effort was to replace `fast` / `8102` with a different family while keeping the team-lane runtime under `mlxctl` + `vllm-metal`.

That surfaced early `mlxctl` swap-path issues:

- false-success behavior during lane loads
- partial desired/actual state mismatches
- duplicate or stale assignment behavior during earlier swap attempts

Those control-plane problems were later hardened, but they are part of the incident context because they made early results less trustworthy and increased the blast radius of experiments.

## 2. GLM-4.7-Flash on the shared runtime

Attempted target:

- `mlx-community/GLM-4.7-Flash-4bit-mxfp4`

Observed local failure:

- the shared Studio serving env failed before serving
- `transformers 4.57.6` did not recognize `glm4_moe_lite`
- `vllm-8102.err.log` showed the model/config load failure directly

Interpretation:

- this was a runtime compatibility failure first
- not a parser-flag failure first

## 3. GLM dedicated canary env

A dedicated Studio canary venv was created to isolate GLM work from the shared serving stack:

- `/Users/thestudio/.venv-vllm-metal-glm47`

The canary env upgraded `transformers` to a much newer dev build.

Observed local progress:

- `AutoConfig.from_pretrained(...)` succeeded in the canary env
- `AutoTokenizer.from_pretrained(..., trust_remote_code=True)` succeeded

Observed local failure after that:

- `vllm-metal` still failed in the MLX backend layer
- `mlx_lm` could not load `glm4_moe_lite`
- exact failure included:
  - `ModuleNotFoundError: No module named 'mlx_lm.models.glm4_moe_lite'`
  - `ValueError: Model type glm4_moe_lite not supported.`

Interpretation:

- updating `transformers` alone is not enough for GLM on this stack
- the current `mlx_lm` / `vllm-metal` backend path also lacks the required model support

## 4. Seed-OSS-36B canary

Attempted target:

- `mlx-community/Seed-OSS-36B-Instruct-4bit`

Applied family-specific runtime settings:

- `tool_choice_mode=auto`
- `tool_call_parser=seed_oss`
- local `chat_template.jinja`
- trust-remote-code path

Observed local behavior:

- server boots
- `/v1/models` responds
- model loads quickly and stays up

But direct repeated tool probes on the raw Studio lane produced inconsistent results:

- correct structured `tool_calls` with `noop`
- no `tool_calls` at all
- wrong tool names such as `example_function_name`
- long thought output / overrun behavior

Interpretation:

- Seed is loadable on this runtime
- Seed is not reliable enough for the OpenCode / MCP-style backend contract required here

This matters because “boots and answers” is not the acceptance bar. The required bar is structured, correct tool-calling behavior.

## 5. Granite-20B-FunctionCalling canary

Attempted target:

- `ibm-granite/granite-20b-functioncalling`

The base model snapshot was downloaded and converted to:

- `/Users/thestudio/models/hf/hub/converted--granite-20b-functioncalling-canary`

Observed local failure 1:

- launch with generic `--max-model-len 65536` failed
- model-derived `max_position_embeddings` was `8192`

Observed local failure 2 after correcting to `8192`:

- tokenizer initialization crashed in the current `vllm` / `transformers` runtime
- exact failure:
  - `AttributeError: 'list' object has no attribute 'keys'`

Interpretation:

- Granite got farther than GLM
- but the converted artifact + current runtime combination is still not a working canary for this stack

## 6. Rollback to GPT-OSS 20B

Rollback target:

- `mlx-community/gpt-oss-20b-MXFP4-Q4`

Observed local result:

- `8102` is again serving `mlx-gpt-oss-20b-mxfp4-q4` at the runtime/process layer
- `/v1/models` succeeds
- LiteLLM `fast` still reaches the backend

But the hardened readiness path still does not mark the lane converged:

- `actual_serving_target` remains `null`
- `last_known_good_target` still points at the failed GLM target
- `last_failure` still reports readiness failure

Observed local reason:

- the GPT-OSS completion probe returned reasoning-only output with `content: null`
- it did not satisfy the current `assistant_text_or_tool_calls` readiness predicate

Interpretation:

- `fast` is operationally rolled back
- `fast` is not cleanly reconciled under the current readiness model

## 7. Main lane audit

Current target:

- `mlx-community/Llama-3.3-70B-Instruct-4bit`

Observed local `vllm` render:

- `--served-model-name mlx-llama-3-3-70b-4bit-instruct`
- `--max-model-len 65536`
- `--no-async-scheduling`
- `--enable-auto-tool-choice`
- `--tool-call-parser llama3_json`
- no reasoning parser
- `VLLM_METAL_MEMORY_FRACTION=auto`

Observed direct Studio behavior:

- plain chat works
- 5/5 repeated noop tool probes returned proper structured `tool_calls`
- first tool name was `noop` every time

Observed LiteLLM behavior after repair:

- `main` now routes to the Llama backend correctly
- `code-reasoning` now routes to the same backend correctly
- both return structured noop tool calls through LiteLLM

Interpretation:

- `main` is the only lane in this campaign that clearly meets the required tool-use contract

## Findings by Topic

## A. GLM failed on backend support, not parser choice first

### Upstream-documented behavior

The official GLM-4.7 card documents local vLLM support with fresh components and uses:

- `--tool-call-parser glm47`
- `--reasoning-parser glm45`
- very fresh `vllm`
- `transformers` from Git

vLLM issue `#33348` documents the current parser mismatch state and explicitly notes there is no registered `glm47` reasoning parser.

### Observed local behavior

Even after the canary env got past `transformers` config recognition, the MLX backend still failed because `mlx_lm` lacked `glm4_moe_lite` support.

### Conclusion

GLM is not a lane-swap problem on this stack. It is a backend/runtime-support problem.

## B. Seed failed on tool reliability, not startup

### Upstream-documented behavior

vLLM has a Seed-specific tool-calling recipe and parser surface.

### Observed local behavior

Seed started and served, but direct raw lane probes were not reliable enough for structured tool use.

### Conclusion

Seed is not production-valid for this `fast` lane on the current stack.

## C. Granite failed on model/runtime integration details

### Upstream expectation

Granite function-calling is an attractive fallback family because it is explicitly positioned for that use case.

### Observed local behavior

The model got past config parsing but failed on max-context assumptions first, then tokenizer initialization.

### Conclusion

Granite is not a working fallback on the current runtime path either.

## D. The main lane is currently healthy

Observed local behavior shows:

- correct render
- direct structured tool calls
- fixed LiteLLM alias path after repair

### Conclusion

Llama 3.3 on `8101` is the currently validated lane for OpenCode / MCP-style use.

## E. The gateway had real stale-config drift

Observed local issue:

- `sync-gateway` regenerated `env.local` from the corrected served-set
- but static alias sections in `router.yaml` still hardcoded old Qwen env var names

That left:

- `main` broken through LiteLLM
- `code-reasoning` broken through LiteLLM
- some task aliases still stale too

The gateway repair in this pass updated:

- served handle for slot `8101`
- generated env vars
- static router aliases

### Conclusion

The incident was not only about model runtime. It also exposed real stale-canon drift in the gateway layer.

## F. The current GPT-OSS fast lane is back, but not perfectly reconciled

Observed local behavior:

- direct runtime path is GPT-OSS 20B again
- LiteLLM `fast` still resolves to that backend
- but the hardened readiness logic still does not like the backend’s completion shape

### Conclusion

The old `fast` lane is back operationally, but it is not a perfect match for the new readiness assumptions.

## Root Cause Assessment

There is no single root cause.

### Root cause class 1: runtime compatibility

Applies to:

- GLM on shared runtime

Evidence:

- `transformers` in shared runtime does not recognize `glm4_moe_lite`

### Root cause class 2: MLX backend family support

Applies to:

- GLM on the dedicated canary runtime

Evidence:

- `mlx_lm` does not support `glm4_moe_lite` in the current stack

### Root cause class 3: tool-calling behavior quality

Applies to:

- Seed

Evidence:

- repeated direct tool probes were inconsistent even when the server was healthy

### Root cause class 4: tokenizer/runtime integration

Applies to:

- Granite

Evidence:

- tokenizer init failure after corrected max-model-len

### Root cause class 5: control-plane and gateway drift

Applies to:

- `mlxctl` lane reconciliation on GPT rollback
- LiteLLM `main` / `code-reasoning` stale mapping

Evidence:

- `8102` runtime healthy but lane-state still failed
- `main` alias returned `404` until gateway repair

## Current Recommendations

## 1. Keep `main` on Llama 3.3

This is the current validated tool-capable lane.

Treat as current best path for:

- OpenCode
- MCP-style backend tool use
- code-reasoning alias

## 2. Keep `fast` on GPT-OSS 20B for now

Do not continue the replacement search in the same pass as day-to-day operations.

Treat `fast` as:

- restored operationally
- still synthesis-oriented
- not the lane to rely on for backend tool use

## 3. Treat GLM as a runtime-refresh project, not a lane-swap project

If GLM is to be revisited, the work needs to explicitly include:

- shared runtime compatibility
- `mlx_lm` backend support
- dedicated validation on an experimental port

## 4. Do not promote Seed on this stack without stronger direct evidence

The current evidence says:

- loadable
- not tool-reliable enough

## 5. Treat Granite as failed for this stack unless tokenizer/runtime behavior changes

Granite is not a simple “retry later this afternoon” candidate.

## Open Questions for Associate Review

1. Is `vllm-metal` the right long-term serving path for non-GPT/non-Llama `fast` candidates, or should those families move to a different runtime path?
2. Should `fast` remain synthesis-only, or is there still a hard requirement that every lane be MCP/tool-capable?
3. Should `mlxctl` readiness for GPT-OSS-style lanes accept reasoning-only responses, or is that a bug/regression that should stay fail-closed?
4. Is the current GPT-OSS 20B behavior acceptable as the canonical `fast` lane under the upgraded control-plane assumptions?
5. Is Seed’s inconsistency likely a parser/template issue worth further tuning, or is it a model/runtime mismatch not worth more effort?
6. If GLM is important enough to pursue, should the next step be:
   - a shared runtime refresh
   - a separate canary runtime branch
   - or a pure-MLX serving path outside `vllm-metal`

## Evidence Appendix

## Key local files and logs

- Studio registry:
  - `/Users/thestudio/models/hf/hub/registry.json`
- Team-lane stderr:
  - `/Users/thestudio/vllm-8102.err.log`
- GLM canary log:
  - `/Users/thestudio/vllm-8120-glm47.log`
- Granite canary log:
  - `/Users/thestudio/vllm-8121-granite.log`
- Current repo docs/config:
  - `docs/foundation/mlx-registry.md`
  - `docs/foundation/runtime-lock.md`
  - `platform/ops/runtime-lock.json`
  - `layer-gateway/litellm-orch/config/router.yaml`
  - `layer-gateway/litellm-orch/config/env.local`
  - `layer-gateway/registry/handles.jsonl`
  - `layer-gateway/litellm-orch/SERVICE_SPEC.md`
  - `docs/INTEGRATIONS.md`
  - `docs/OPENCODE.md`

## Commands used as primary evidence

- `./platform/ops/scripts/mlxctl status --checks --json`
- `./platform/ops/scripts/mlxctl vllm-render --ports 8101,8102 --validate --json`
- direct Studio `curl http://127.0.0.1:8101/v1/models`
- direct Studio `curl http://127.0.0.1:8102/v1/models`
- direct Studio noop tool probes on `8101`
- direct LiteLLM noop tool probes on `main` and `code-reasoning`
- direct LiteLLM plain-chat / tool probes on `fast`
- Studio package-version probes in both the shared and GLM canary venvs

## Upstream primary sources

- vLLM OpenAI-compatible server docs  
  <https://docs.vllm.ai/en/latest/serving/openai_compatible_server/>
- vLLM tool-calling docs  
  <https://docs.vllm.ai/en/latest/features/tool_calling/>
- GLM-4.7-Flash official model card  
  <https://huggingface.co/zai-org/GLM-4.7-Flash>
- vLLM issue `#33348`  
  <https://github.com/vllm-project/vllm/issues/33348>
- vLLM Seed recipe  
  <https://docs.vllm.ai/projects/recipes/en/latest/Seed/Seed-OSS-36B.html>
- ByteDance Seed model card  
  <https://huggingface.co/ByteDance-Seed/Seed-OSS-36B-Instruct>
- Granite function-calling model card  
  <https://huggingface.co/ibm-granite/granite-20b-functioncalling>
- Meta Llama 3.3 docs  
  <https://www.llama.com/docs/model-cards-and-prompt-formats/llama3_3/>

## Final Current-State Judgment

As of 2026-03-15:

- `main` is healthy and validated
- `code-reasoning` now correctly follows `main`
- `fast` is back on GPT-OSS 20B operationally
- but the `fast` lane replacement problem is not solved
- the current stack does not yet have a validated alternative `fast` family that is both:
  - high quality
  - and trustworthy for OpenCode / MCP-style backend tool use

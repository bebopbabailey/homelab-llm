# GPT-OSS `vllm-metal` Review Pack

Date: 2026-03-15  
Audience: associate review / follow-on remediation design  
Scope: current canonical GPT-OSS lanes under Studio `vllm-metal`, with focus on why `fast` (`8102`) is not a validated tool-capable lane for OpenCode on the present stack

## Executive Summary

The current canonical ensemble is live and converged:

- `deep` (`8100`) -> `mlx-gpt-oss-120b-mxfp4-q4`
- `main` (`8101`) -> `mlx-llama-3-3-70b-4bit-instruct`
- `fast` (`8102`) -> `mlx-gpt-oss-20b-mxfp4-q4`

The GPT-OSS-specific issue is narrower than the earlier multi-model incident:

- GPT-OSS loads and serves under the current Studio `vllm-metal` stack.
- Plain chat works on both `deep` and `fast`.
- `mlxctl` originally failed to compile the intended GPT chat-template kwargs into the `vllm-metal` argv, which made the live GPT lanes less controlled than intended.
- That control-plane/runtime wiring issue has now been fixed.
- Even with the corrected GPT kwargs and an explicit raw `vllm serve` canary, GPT-OSS 20B still does not satisfy the acceptance bar for a tool-capable OpenCode `fast` lane on this stack.

The current direct `fast` noop-tool probe returns:

- `tool_calls: []`
- `content: "{}"`
- verbose `reasoning` / `reasoning_content`
- no structured OpenAI-style tool call

That means the present blocker is not lane bring-up anymore. The blocker is behavior at the model/runtime/protocol layer:

- GPT-OSS is usable as a plain-chat synthesis lane.
- GPT-OSS is not yet validated as a reliable tool-calling lane for OpenCode on the current `vllm-metal` stack.

`main` on Llama 3.3 remains the only currently validated tool-capable lane.

## Scope and Intent

This review pack is intentionally focused on GPT-OSS, not GLM/Seed/Granite.

It covers:

- the current `deep` / `fast` GPT-OSS runtime shape
- the specific `mlxctl` / `vllm-metal` integration issue found
- direct plain-chat and tool-call behavior on the current stack
- why `fast` is still not approved as a tool-capable OpenCode lane
- concrete next-step recommendations for an associate

It does not cover:

- choosing a new non-GPT `fast` candidate
- upgrading Studio runtime dependencies
- redesigning LiteLLM or OpenCode itself

## Current Runtime Truth

### Live canonical lanes

Observed locally from `mlxctl status --checks --json`:

- `8100` is running `mlx-community/gpt-oss-120b-MXFP4-Q4`
- `8101` is running `mlx-community/Llama-3.3-70B-Instruct-4bit`
- `8102` is running `mlx-community/gpt-oss-20b-MXFP4-Q4`

All three lanes currently report:

- `health_state = serving`
- `reconciliation_state = converged`
- `http_models_ok = true`

### Shared Studio serving runtime

Observed locally on Studio:

- `vllm 0.14.1`
- `vllm-metal 0.1.0`
- `transformers 4.57.6`
- `mlx-lm 0.29.1`

### Current `vllm-metal` capability surface

Observed locally from `mlxctl vllm-capabilities --json`:

- `supports_auto_tool_choice = true`
- `supports_tool_call_parser = true`
- `supports_reasoning_parser = true`
- `supports_default_chat_template_kwargs = true`
- `tool_call_parsers` include `openai`
- `reasoning_parsers = []`

That last point matters: the runtime exposes the reasoning-parser flag surface, but there are no registered reasoning parsers in this environment.

## Effective Lane Config

Observed locally from `mlxctl vllm-render --ports 8100,8101,8102 --validate --json`.

### `deep` / `8100`

- profile: `gpt_oss_lane`
- served model: `mlx-gpt-oss-120b-mxfp4-q4`
- `--chat-template /opt/mlx-launch/templates/gpt-oss-120b-chat_template.jinja`
- `--default-chat-template-kwargs {"enable_thinking": false, "reasoning_effort": "low"}`
- `--max-model-len 65536`
- `--no-async-scheduling`
- no tool parser
- logical readiness mode: `chat_basic`

### `main` / `8101`

- profile: `llama3_json`
- served model: `mlx-llama-3-3-70b-4bit-instruct`
- `--enable-auto-tool-choice`
- `--tool-call-parser llama3_json`
- `--max-model-len 65536`
- `--no-async-scheduling`
- no reasoning parser

### `fast` / `8102`

- profile: `gpt_oss_lane`
- served model: `mlx-gpt-oss-20b-mxfp4-q4`
- `--chat-template /opt/mlx-launch/templates/gpt-oss-20b-chat_template.jinja`
- `--default-chat-template-kwargs {"enable_thinking": false, "reasoning_effort": "low"}`
- `--max-model-len 32768`
- `--no-async-scheduling`
- no tool parser
- logical readiness mode: `chat_basic`

## Primary Issues Found

## 1. `mlxctl` was not compiling GPT chat-template kwargs into `vllm-metal`

### Observed local evidence

GPT registry entries already carried logical chat-template arguments:

- `enable_thinking = false`
- `reasoning_effort = low`

But before the fix, the active `vllm-metal` launch path did not emit:

- `--default-chat-template-kwargs`

That meant GPT-OSS lanes were not actually being launched with the intended GPT-specific chat-template controls, even though the logical config existed.

### Impact

- control-plane truth did not match runtime argv
- GPT-OSS behavior was more ambiguous than intended
- readiness and output behavior were harder to reason about

### Status

Fixed in `mlxctl`.

Current `vllm-render --validate` now shows GPT lanes compiling:

- `--default-chat-template-kwargs {"enable_thinking": false, "reasoning_effort": "low"}`

`8102` was reloaded with the same canonical GPT-OSS 20B target after the fix, and lane state reconverged successfully.

## 2. GPT-OSS plain chat still exposes reasoning fields in client-visible responses

### Observed local evidence

Direct non-streaming plain-chat probe on `8100` returned:

- `content: "I’m ready."`
- `tool_calls: []`
- `reasoning: "..."`
- `reasoning_content: "..."`

Direct non-streaming plain-chat probe on `8102` returned:

- `content: "I’m ready to help!"`
- `tool_calls: []`
- `reasoning: "..."`
- `reasoning_content: "..."`

### Interpretation

The GPT-OSS lanes now produce final assistant text, but they still expose reasoning fields in the response shape.

That is not a load/readiness failure. It is a protocol/response-shape concern for downstream consumers.

### Practical effect

- plain chat is usable
- downstream clients may still see extra reasoning fields
- if a caller expects a cleaner assistant-only shape, additional normalization may be needed

## 3. GPT-OSS 20B still does not satisfy the tool-calling acceptance bar for `fast`

### Raw direct probe result

Direct noop tool probe on `8102` with:

- one `noop` function tool
- `tool_choice = auto`
- `max_tokens = 256`

returned:

- `content: "{}"`
- `tool_calls: []`
- `finish_reason: "stop"`
- verbose `reasoning`
- verbose `reasoning_content`

It did not return:

- a structured `tool_calls` entry
- a valid `function_call`
- a semantically correct OpenAI-style tool call

### Why this matters

For this repo, a tool-capable lane is not “close enough” unless it reliably does all of the following:

- emits structured tool calls
- uses the correct tool name
- does not collapse into plain text or pseudo-protocol text
- behaves reliably enough for OpenCode tool driving

GPT-OSS 20B does not currently clear that bar on the present stack.

## 4. The failure mode is behavioral, not boot/runtime anymore

This is the most important narrowing result in the current pass.

The GPT-OSS problem is no longer:

- lane cannot boot
- lane cannot serve `/v1/models`
- lane truth cannot converge

Those are all working now.

The remaining issue is:

- GPT-OSS 20B under current `vllm-metal` does not produce the required structured tool-call behavior for `fast`

That sharply reduces the problem space for follow-on work.

## Comparative Baseline: Why `main` Matters

`main` / `8101` on Llama 3.3 is the control case.

Observed locally:

- direct Studio noop-tool probe returns structured `tool_calls`
- function name is `noop`
- no reasoning-field leakage was observed in the successful tool probe

That means:

- the current stack can support a valid tool-capable lane
- the problem is not “all tool calling is broken on Studio”
- the remaining GPT-OSS issue is family/runtime/protocol-specific

## LiteLLM / OpenCode Implications

## LiteLLM

After the earlier gateway repair:

- `main` and `code-reasoning` correctly point to Llama 3.3
- `fast` points to GPT-OSS 20B

Current implication:

- `main` is the valid tool-capable alias
- `fast` is currently a plain-chat GPT alias, not a validated tool alias

## OpenCode

Observed locally:

- `opencode models litellm` lists `deep`, `main`, and `fast`
- direct end-to-end `opencode run` smokes on `main` and `fast` did not complete before timeout in the last pass

More importantly, even before OpenCode client validation, the backend acceptance bar for `fast` already failed:

- direct raw `8102` tool probe did not produce structured tool calls

So `fast` should not currently be represented as “validated for OpenCode tool use.”

## What Was Fixed in This Pass

### Control-plane / runtime integration

Fixed:

- `mlxctl` now detects and reports `supports_default_chat_template_kwargs`
- GPT logical `chat_template_args` now compile into `vllm` as:
  - `--default-chat-template-kwargs`
- `vllm-render --validate` now shows effective GPT chat-template kwargs
- `mlxctl verify` now fails if a lane is serving but desired/actual truth is unresolved

### Canonical runtime state

Fixed:

- `fast` was reloaded onto the canonical GPT-OSS 20B target after the compile-path repair
- `8102` lane truth reconverged
- canonical launchd-managed trio is live and policy-compliant

### Canon/docs

Fixed:

- `main` is now documented consistently as Llama 3.3
- stale Qwen-era `main` language was removed from authoritative docs
- docs now explicitly state that `fast` is canonical GPT-OSS 20B but not a validated tool-calling lane on the current stack

## What Is Still Not Fixed

1. `fast` is not validated as a tool-capable GPT-OSS lane.
2. `deep` and `fast` still expose reasoning fields in plain-chat responses.
3. OpenCode end-to-end validation is still incomplete because the CLI smokes timed out.
4. No MCP-specific validation was run in this pass.

## Root Cause Assessment

This issue separates into three layers.

## A. Fixed control-plane integration bug

Root cause:

- `mlxctl` was not compiling GPT chat-template kwargs into the active `vllm-metal` launch path

Status:

- fixed

## B. Remaining GPT-OSS response-shape issue

Root cause:

- GPT-OSS under the current `vllm-metal` stack still emits reasoning fields on plain-chat responses even when `enable_thinking` is disabled via chat-template kwargs

Status:

- not fixed
- likely requires either deeper GPT runtime understanding or downstream normalization

## C. Remaining GPT-OSS tool-use issue

Root cause:

- GPT-OSS 20B on the current `vllm-metal` stack does not currently translate the noop tool prompt into a valid structured OpenAI-style tool call under the tested configuration

Status:

- not fixed
- current evidence says the lane is usable for chat, not yet approved for tool use

## Recommendations

## Immediate recommendations

1. Keep the canonical trio as-is:
   - `deep` = GPT-OSS 120B
   - `main` = Llama 3.3
   - `fast` = GPT-OSS 20B

2. Keep `main` as the only validated tool-capable lane for now.

3. Do not advertise `fast` as a validated OpenCode/MCP tool lane until a direct raw backend tool probe succeeds reliably.

4. Treat the current GPT-OSS `fast` lane as plain-chat/synthesis oriented.

## Associate review questions

1. Is GPT-OSS tool use on `vllm-metal` expected to require a different parser, prompt shape, or served-model-specific chat contract than the one currently tested?
2. Are the remaining reasoning fields expected/acceptable for GPT-OSS in this stack, or should they be normalized at the gateway?
3. Should `fast` remain non-tool by policy, with `main` carrying all tool-use responsibility?
4. If GPT-OSS tool use is a hard requirement for `fast`, is the next step:
   - deeper direct raw `vllm-metal` experimentation, or
   - a different serving path entirely for GPT-OSS?

## Suggested next-step experiments

These are not part of the current fix, but they are the smallest next investigations:

1. Run a tighter raw `vllm serve` matrix on experimental ports for GPT-OSS 20B varying only:
   - prompt wording
   - token budget
   - chat-template kwargs
   - any GPT-OSS-specific parser support if upstream/runtime evidence exists

2. Determine whether reasoning-field leakage is:
   - inherent to current GPT-OSS `vllm-metal` response shape, or
   - suppressible with a different GPT config

3. If backend behavior remains unchanged, decide whether the right boundary is:
   - gateway normalization for reasoning fields only
   - or policy that `fast` is not a tool lane

## Evidence Appendix

## Key local commands

Control plane:

```bash
./platform/ops/scripts/mlxctl status --checks --json | jq '.ports[] | select(.port==8100 or .port==8101 or .port==8102)'
./platform/ops/scripts/mlxctl vllm-render --ports 8100,8101,8102 --validate --json
./platform/ops/scripts/mlxctl vllm-capabilities --json
./platform/ops/scripts/mlxctl verify
```

Direct Studio plain-chat probes:

```bash
curl -fsS http://127.0.0.1:8100/v1/models | jq .
curl -fsS http://127.0.0.1:8102/v1/models | jq .
```

Direct Studio tool probe shape used on `fast`:

```json
{
  "model": "mlx-gpt-oss-20b-mxfp4-q4",
  "messages": [{"role": "user", "content": "Use the noop tool exactly once, then stop."}],
  "tools": [{
    "type": "function",
    "function": {
      "name": "noop",
      "description": "noop",
      "parameters": {"type": "object", "properties": {}}
    }
  }],
  "tool_choice": "auto",
  "stream": false,
  "max_tokens": 256
}
```

## Key local files

- [platform/ops/scripts/mlxctl](/home/christopherbailey/homelab-llm/platform/ops/scripts/mlxctl)
- [platform/ops/runtime-lock.json](/home/christopherbailey/homelab-llm/platform/ops/runtime-lock.json)
- [docs/foundation/runtime-lock.md](/home/christopherbailey/homelab-llm/docs/foundation/runtime-lock.md)
- [docs/foundation/mlx-registry.md](/home/christopherbailey/homelab-llm/docs/foundation/mlx-registry.md)
- [docs/OPENCODE.md](/home/christopherbailey/homelab-llm/docs/OPENCODE.md)
- [docs/INTEGRATIONS.md](/home/christopherbailey/homelab-llm/docs/INTEGRATIONS.md)

## Bottom Line

The GPT-OSS issue is now clearly bounded.

`mlxctl` and launchd are no longer the main problem for GPT-OSS:

- the canonical lanes are up
- lane truth is converged
- GPT kwargs are now compiled correctly

The unresolved issue is model/runtime behavior:

- GPT-OSS plain chat works
- GPT-OSS still exposes reasoning fields
- GPT-OSS 20B tool use is not yet validated on the current `vllm-metal` stack

For now, the stable contract is:

- `main` is the tool-capable lane
- `fast` is canonical GPT-OSS 20B but not yet a validated tool lane

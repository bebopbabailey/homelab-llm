# OpenCode Planning Alias Incident Report

Date: 2026-03-11  
Scope: OpenCode plan-agent behavior through LiteLLM and OptiLLM for `boost-plan-trio` and `boost-plan`  
Audience: senior developer review and follow-on design work

## Executive Summary

OpenCode planning requests against the coding-specific aliases `boost-plan-trio` and `boost-plan` are not reliable for tool-shaped repository-analysis prompts.

The original failing prompt was:

> Read `layer-gateway/litellm-orch/config/router.yaml` and related config/docs. Produce a keep/ditch/defer matrix for every LiteLLM alias and callback, preserving `fast`, `main`, and `deep` as the canonical public lanes unless the repo itself proves otherwise. Recommend the smallest router surface that still supports current workflows. Do not edit files yet.

Verified outcomes:

- `boost-plan-trio` returned a fake search step, not a real answer.
- `boost-plan` returned Python implementation text, not a matrix.
- `main` returned tool-intent JSON only, with no final answer.
- `deep` was the only tested lane that actually performed repo reads, but it was partial and slow.

The critical architectural constraint is that OptiLLM approaches flatten the OpenCode conversation into plain text. They do not receive OpenCode tool schemas or tool-call results. That means `boost-plan-trio` cannot truly execute repo-reading tasks the way direct OpenCode use of `deep` can.

The current recommended direction is to treat `boost-plan-trio` as needing a safe, explicit error path for tool-required OpenCode prompts rather than trying to fake tool use or silently fall back to another alias.

## Affected Components

- OpenCode desktop/service session planner
- LiteLLM gateway on the Mini
- OptiLLM proxy on the Studio
- Local Trio plugin:
  `layer-gateway/optillm-proxy/optillm/plugins/plansearchtrio_plugin.py`
- Upstream stock OptiLLM `plansearch` implementation in the Studio virtualenv

## User-Visible Symptoms

### `boost-plan-trio`

- In the OpenCode UI, the request appeared to do one search and then stop producing useful output.
- The stored assistant turn contained only:
  - `step-start`
  - the text `[search "layer-gateway/litellm-orch/config/router.yaml"]`
  - `step-finish`

### `boost-plan`

- In the OpenCode UI, the request began writing Python and then stopped.
- The content was a fenced Python script that attempted to parse `router.yaml` as if it had `aliases` and `callbacks` in a structure that does not match the repo.

## Evidence Sources

Primary evidence was gathered from:

- OpenCode log:
  `~/.local/share/opencode/log/2026-03-11T191933.log`
- OpenCode DB:
  `opencode db ...`
- Mini journald:
  `journalctl -u litellm-orch.service ...`
- Studio OptiLLM error log:
  `~/Library/Logs/optillm-proxy.err`
- Fresh read-only one-shot OpenCode runs with `litellm/boost-plan`, `litellm/main`, and `litellm/deep`
- Read-only source inspection of the deployed OptiLLM package and the local Trio plugin

No secrets or private URLs are included in this report.

## Timeline

### Incident 1: `boost-plan-trio`

Time:
- OpenCode request started at `2026-03-11 19:23:53 UTC`
- Studio-side Trio logs were at `2026-03-11 14:23:53` local time

Observed sequence:
1. OpenCode sent the request with model `boost-plan-trio`.
2. LiteLLM routed it to the Trio path (`plansearchtrio-deep`).
3. Studio logs showed Trio `synthesis` returned empty output.
4. Trio fell into its final fallback path.
5. The fallback used `main` as a last-resort final-answer model.
6. That internal `main` call returned the literal text:
   `[search "layer-gateway/litellm-orch/config/router.yaml"]`
7. LiteLLM streamed that back as a normal `200 OK` completion with `finish_reason=stop`.
8. OpenCode stored that single line as the assistant response and exited the loop.

Important detail:
- This was not a transport hang, crash, or timeout.
- It was a semantically bad but technically successful completion.

### Incident 2: `boost-plan`

Time:
- OpenCode request started at `2026-03-11 19:56:35 UTC`
- Studio-side `plansearch` logs were at `2026-03-11 14:56:35` local time

Observed sequence:
1. OpenCode sent the request with model `boost-plan`.
2. LiteLLM routed it to stock `plansearch` over `deep`.
3. Studio logs showed:
   - `Generating initial observations`
   - `Generating derived observations`
   - `Generating solution based on observations`
   - `Solution generation response truncated or empty`
   - `Implementing solution in Python`
4. The final returned text was Python code, not a planning matrix.

Important detail:
- This also completed as `200 OK`.
- It did not fail closed or return a user-visible error.

## Fresh One-Shot Reproductions

These runs were done read-only after the incidents to separate session contamination from baseline behavior.

### `litellm/boost-plan`

- Fresh OpenCode one-shot returned Python code again.
- Wall time was about 40 seconds.
- This confirms the bad `boost-plan` behavior was not just contamination from the earlier Trio session.

### `litellm/main`

- Fresh OpenCode one-shot returned only tool-intent JSON.
- No final matrix or prose answer was produced.
- Wall time was about 30 seconds.

### `litellm/deep`

- Fresh OpenCode one-shot actually read repo files and produced a partial matrix.
- It did not cover callbacks and did not fully satisfy the prompt.
- It was slow, about 118 seconds.

### Clean interpretation

- `deep` is tool-capable in OpenCode.
- The OptiLLM planning aliases are not tool-capable in the same way.
- `boost-plan-trio` and `boost-plan` are therefore failing for different reasons, but both are incompatible with this prompt class as currently wired.

## Root Causes

## 1. Trio final fallback reused an OpenCode tool prompt in a plain-chat subcall

The local Trio plugin reuses the caller system prompt inside internal stage calls.

For the failing request, the caller prompt was the OpenCode tool-oriented system prompt. Trio then used that prompt for internal non-tool subcalls that had no real OpenCode tool schema attached.

When `deep` synthesis returned empty, Trio asked `main` to generate the final answer under that same prompt shape. `main` emitted a fake search action instead of a real answer.

This is the direct cause of the `[search "..."]` incident.

## 2. Trio cannot actually execute OpenCode tool-required repo tasks

OptiLLM parses incoming messages into:

- `system_prompt`
- `initial_query`

and then runs its approaches against those text strings.

It does not preserve:

- OpenCode tool schemas
- tool-call envelopes
- tool-call results
- structured file-read context gathered during the turn

That means a Trio approach has no real way to perform repo inspection inside OptiLLM. It can only guess from prompt text.

This is the primary architectural blocker for making `boost-plan-trio` truly equivalent to direct OpenCode use of `deep` on file-reading tasks.

## 3. Stock `plansearch` is structurally wrong for this prompt class

The deployed OptiLLM `plansearch` implementation is a competitive-programming pipeline.

Its stages are:

1. generate observations
2. generate derived observations
3. generate natural-language solution
4. implement the solution in Python

When solution generation truncates or returns empty, the implementation path still runs and asks the model to implement the solution in Python.

This is why `boost-plan` produced Python instead of a keep/ditch/defer matrix.

This is not a random sampling issue. It is the stock design of the approach.

## 4. `main` is not a reliable safety fallback for OpenCode planning prompts

Fresh `main` testing showed tool-intent JSON without a final answer.
The Trio incident showed bracketed pseudo-tool text.

Both outcomes are evidence that `main` is not a safe final-answer fallback when the incoming task is OpenCode tool-shaped but the underlying path is no longer tool-capable.

## Constraints

These constraints were explicitly or implicitly established during investigation:

- User requested minimal, reversible changes.
- User does not want existing production lanes disturbed.
- User does not want automatic fallbacks.
- If Trio cannot do the task safely, it should show an error and let the user manually choose another model.
- User chose not to change defaults; they can select another model alias manually.
- User chose to focus follow-on work on `boost-plan-trio`, not `boost-plan`.

Technical constraints:

- No new ports, binds, auth changes, or LAN exposure.
- No secrets or private URLs in git-managed docs.
- No direct MLX runtime changes.
- No automatic alias fallback in LiteLLM for this fix.
- No broad architecture redesign in this change.

## Blockers

## Architectural blocker: no end-to-end tool preservation through OptiLLM approaches

This is the main blocker.

Without preserving OpenCode tools and tool results through the OptiLLM approach layer, `boost-plan-trio` cannot honestly perform prompts that require:

- reading files
- searching the repo
- confirming docs/config content
- generating repo-grounded answers from discovered evidence

Any attempt to make Trio “work” on those prompts without fixing the architecture is limited to:

- safe explicit failure
- best-effort hallucination from prompt text

The user chose safe explicit failure.

## Scope blocker: `boost-plan` is also broken, but excluded from the immediate fix

The stock `boost-plan` path is unsuitable for this prompt class, but the current implementation discussion has intentionally narrowed to `boost-plan-trio`.

That means:

- `boost-plan` remains a known issue
- no remediation for `boost-plan` is included in the immediate follow-on task

## Related Issues

## 1. Trio `fast` verification/triage instability

Earlier logs also showed:

- repeated empty `fast` stage outputs in Trio
- a `channel marker present but no channel value found in header` error on the `fast` lane

This did not directly cause the `[search "..."]` response, but it is part of the Trio instability surface.

## 2. Documentation drift risk

The repo’s documented OpenCode/OptiLLM planning story and the actual runtime behavior are not fully aligned with what was observed on this prompt class.

This matters because another developer may assume:

- `boost-plan-trio` is a drop-in OpenCode planning lane for repo-reading tasks
- `boost-plan` is a safe baseline for the same prompts

Neither assumption is currently true.

## 3. Session contamination can disguise root cause

When retrying inside the same OpenCode session, earlier bad outputs are included in later requests.

That means a baseline retry after a Trio failure is not a clean comparator unless it is:

- a fresh one-shot run, or
- a direct API reproduction

## What Has Already Been Decided

These planning decisions were made during the investigation:

- Do not add automatic fallbacks.
- Do not change defaults.
- Do not make a larger architecture change in the immediate fix.
- Focus the immediate fix on `boost-plan-trio`.
- For tool-required OpenCode prompts, prefer a safe explicit error over fake tool output.

## Practical Implication for the Next Plan

The next implementation plan for `boost-plan-trio` should assume:

1. Trio needs an early guard for OpenCode tool-required prompts.
2. Trio should fail clearly and visibly for those prompts.
3. Trio internal stages should stop reusing the raw OpenCode system prompt.
4. Trio should reject pseudo-tool text and similar semantically invalid outputs.
5. Trio should not use `main` as a last-resort final-answer generator for this prompt class.

## Explicit Non-Goals for the Immediate Trio Fix

- Make Trio truly tool-capable in OpenCode
- Fix `boost-plan`
- Introduce new aliases
- Change user defaults
- Add automatic fallback to another alias

## Suggested Review Questions for a Senior Developer

- Is a safe explicit error the right contract for tool-required OpenCode prompts, or should the team invest in preserving tool use through the OptiLLM layer?
- Should Trio detect tool-required prompts heuristically, or should the client mark them explicitly?
- Is removing `main` as Trio’s final fallback sufficient, or should final-output validation be stricter across all Trio stages?
- Should `boost-plan` remain documented as-is if it is known to be structurally wrong for repo-analysis prompts?
- Is the right long-term fix a Trio hardening pass, a new tool-aware planning alias, or an architecture change that keeps OpenCode tools alive end to end?

## File and Service References

- Trio plugin:
  `layer-gateway/optillm-proxy/optillm/plugins/plansearchtrio_plugin.py`
- Trio tests:
  `layer-gateway/optillm-proxy/tests/test_plansearchtrio.py`
- OptiLLM service contract:
  `layer-gateway/optillm-proxy/SERVICE_SPEC.md`
- LiteLLM service contract:
  `layer-gateway/litellm-orch/SERVICE_SPEC.md`
- OpenCode integration notes:
  `docs/INTEGRATIONS.md`
- OpenCode local setup notes:
  `docs/OPENCODE.md`

## Current Bottom Line

`boost-plan-trio` is not currently safe for OpenCode repo-reading prompts.

The problem is not just a bad sample. It is a combination of:

- unsafe Trio fallback behavior
- loss of tool context inside OptiLLM approaches
- a mismatch between coding-specific planning aliases and OpenCode tool-driven repo tasks

The minimal immediate path is not “make Trio read the repo.”
The minimal immediate path is “make Trio detect when it cannot do that safely, and fail honestly.”

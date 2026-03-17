# GPT-OSS Fast-Lane Experimental Tooling Spec

Date: 2026-03-15  
Audience: Codex follow-on remediation  
Scope: isolate whether GPT-OSS 20B can be made into a reliable tool-capable lane on the current Studio `vllm-metal` stack without destabilizing the canonical trio

## Mission

Implement a **non-invasive experimental path** for GPT-OSS tool use.

Do **not** keep guessing inside the canonical `fast` lane.
Do **not** rewrite the whole control plane.
Do **not** touch the canonical trio unless the experiment proves out.

Current canonical policy stays:

- `deep` = GPT-OSS 120B
- `main` = Llama 3.3 70B
- `fast` = GPT-OSS 20B plain-chat lane
- `main` remains the only production-approved tool-capable lane unless this experiment proves otherwise

## Why this spec exists

The current evidence says the GPT-OSS problem is now **behavior/protocol**, not lane bring-up:

- canonical lanes are live
- lane truth is converged
- GPT chat-template kwargs now compile correctly
- `fast` is still not a validated tool lane

The strongest current upstream guidance says:

- `/v1/responses` is the recommended interface for GPT-OSS
- `/v1/chat/completions` offers a familiar interface, but “No tool will be invoked” in the current vLLM GPT-OSS recipe
- for **user-defined function calling**, vLLM says to run GPT-OSS with:
  - `--tool-call-parser openai`
  - `--enable-auto-tool-choice`

This means the current noop probe against canonical `fast` was not testing a function-calling GPT-OSS lane. It was testing a plain-chat GPT-OSS lane with tools in the request.

## Source hierarchy you must follow

When sources disagree, use this priority order:

1. current upstream vLLM GPT-OSS docs
2. current upstream vLLM issues affecting GPT-OSS tool behavior
3. OpenAI Harmony / GPT-OSS implementation docs
4. local repo/runtime evidence
5. older/stale GPT-OSS examples only as historical context

Do not use older GPT-OSS how-tos to override newer vLLM behavior when the newer docs better match observed runtime behavior.

## Hard constraints

1. Do not break or repurpose the canonical `fast` lane during the experiment.
2. Do not change LiteLLM aliases or OpenCode production routing in this pass.
3. Do not claim GPT-OSS is production tool-capable unless the documented acceptance bar passes.
4. Keep all GPT-OSS experimentation on an **experimental port/profile**.
5. Keep `main` as production tool lane unless and until the experiment proves GPT-OSS cleanly.

## What you must do

### Phase 1 — verify current reality, no assumptions

Inspect the repo/runtime and answer these concretely before patching:

1. What exact endpoint(s) do the current GPT-OSS probes use?
   - `/v1/chat/completions`
   - `/v1/responses`
   - both

2. What exact client contract matters for the eventual caller?
   - OpenCode direct
   - LiteLLM-mediated OpenCode
   - other internal tooling

3. Does the current production caller for `fast` require **Chat Completions tool calls**, or can it consume **Responses API** semantics?

4. Does the current runtime capability surface expose any GPT-OSS reasoning parser such as `openai_gptoss`?
   - If yes, document how it is discovered
   - If no, do not invent it in profile defaults

5. Are the current `gpt_oss_lane` profile semantics explicitly plain-chat-only, or are they ambiguously mixing chat/reasoning/tool concepts?

Required output for Phase 1:
- a concise evidence-backed diagnosis of the current contract mismatch

### Phase 2 — add a dedicated experimental GPT-OSS tools profile

Create a new experimental profile for GPT-OSS function-calling validation.

Suggested shape:
- profile name: `gpt_oss_tools_experimental`
- separate from canonical `gpt_oss_lane`
- bound only to an experimental port in this pass

The profile must be designed to test the **current documented vLLM GPT-OSS function-calling path** first, before any custom improvisation.

Required launch behavior to test first:
- same GPT-OSS 20B model family already used for canonical `fast`
- preserve current chat template and current GPT chat-template kwargs unless evidence requires change
- add:
  - `--tool-call-parser openai`
  - `--enable-auto-tool-choice`

Do not add undocumented parser combinations first.
Do not start by inventing a Harmony-specific tool parser if the current vLLM GPT-OSS recipe does not require one.

### Phase 3 — implement a tight backend test matrix

Run a backend-only matrix on experimental port(s). No gateway/client assumptions yet.

#### Matrix A — plain chat sanity

1. `/v1/chat/completions`
   - no tools
   - `include_reasoning: false`
   - tiny prompt
   - verify assistant text is returned cleanly enough for plain chat

2. `/v1/chat/completions`
   - no tools
   - default reasoning behavior
   - record response shape

Purpose:
- confirm whether the experimental profile damages plain chat
- document whether reasoning-field leakage remains with current runtime

#### Matrix B — function-calling behavior

Run at minimum the following noop tests repeatedly (not once):

1. `/v1/responses`
   - one noop tool
   - minimal prompt: “Use the noop tool exactly once, then stop.”

2. `/v1/chat/completions`
   - same noop tool
   - same prompt

3. `/v1/responses`
   - one noop tool
   - tiny follow-up tool result turn if applicable / supported

4. `/v1/chat/completions`
   - one noop tool
   - low temperature / deterministic settings if available

You must capture raw request/response JSON for both successful and failed cases.

### Phase 4 — use the correct acceptance bars

Do not use vague wording like “looked better”.
Use these explicit acceptance criteria.

#### Plain-chat acceptance

A GPT-OSS lane is acceptable as plain-chat if:
- repeated `/v1/chat/completions` requests return valid assistant output
- no `content: null`
- no empty completion
- no severe corruption / token leakage in user-facing text

Reasoning fields may still appear depending on the endpoint/runtime; record them, do not hide them.

#### Tool-lane experimental acceptance

A GPT-OSS experimental tool lane passes backend acceptance only if:
- repeated tool requests produce structured tool calls in the endpoint’s native response format
- tool name is correct every time
- arguments are structurally valid every time
- no Harmony/special-token leakage appears in tool names or arguments
- no `content: null` / empty malformed extraction in the tested path
- no intermittent first-call-success then later corruption pattern in a short repeated run

#### Production approval bar

Do **not** approve GPT-OSS 20B as production tool lane unless:
- the backend acceptance bar passes repeatedly
- and the result matches the actual caller contract that matters for OpenCode/LiteLLM

If `/v1/responses` works but the production caller only supports Chat Completions tool calls, then GPT-OSS is **not** production-approved for that caller yet.

## Specific questions this pass must answer

1. Is GPT-OSS 20B tool use actually viable on the current Studio runtime when tested using the documented vLLM GPT-OSS function-calling path?
2. Is the current failure mostly caused by using the wrong endpoint/contract?
3. Is the remaining blocker specifically the Chat Completions path?
4. Is the right outcome one of these?
   - keep GPT-OSS `fast` as plain-chat only
   - use GPT-OSS tools only through a dedicated Responses-path integration
   - reject GPT-OSS tool use on the current stack for now

## What not to do

- Do not mutate canonical `fast` into a tool lane in this pass
- Do not change `main` away from Llama 3.3
- Do not rewrite lane-state semantics again
- Do not broaden this into GLM/Seed/Granite work
- Do not hand-wave around “tool support” without raw backend evidence
- Do not normalize broken `content: null` behavior into “healthy”

## Expected outputs

Return all of the following:

### A. Short diagnosis
- what the real mismatch was
- whether current GPT-OSS docs align with observed behavior

### B. Minimal file list changed
Only include files actually needed for:
- experimental GPT-OSS tools profile
- experimental port wiring if required
- tests/docs directly affected

### C. Raw evidence summary
- exact experimental argv
- exact endpoint(s) tested
- exact acceptance results
- one or more raw request/response pairs

### D. Verdict
Choose exactly one:
- `GPT-OSS 20B tool use is backend-validated on current stack`
- `GPT-OSS 20B tool use works only through Responses path, not current production caller contract`
- `GPT-OSS 20B tool use is still not reliable on current stack`

### E. Production recommendation
One paragraph only.
Say whether `fast` should remain:
- plain-chat only
- experimental tool lane only
- or promoted to tool-capable

## Primary source anchors you must reconcile

Current docs / issues to verify against March 2026 state:

- vLLM GPT-OSS recipe
- vLLM OpenAI-compatible server docs
- OpenAI Harmony response format guide
- vLLM GPT-OSS chat-completions tool-call issue(s)
- vLLM GPT-OSS token leakage / malformed extraction issue(s)
- local evidence from:
  - current GPT-OSS review pack
  - current `mlxctl vllm-render`
  - current raw matched 20B vs 120B noop evidence

## Suggested operator-facing conclusion format

Use this exact pattern at the end:

- **What was wrong:** ...
- **What I changed:** ...
- **What the experiment proved:** ...
- **What should be production policy now:** ...

## Reminder

This is an evidence-first experimental validation pass.
The point is not to force GPT-OSS into being a tool lane.
The point is to determine whether the current `fast` weirdness is:
- endpoint mismatch,
- missing function-calling flags,
- Chat Completions adapter bugs,
- or a genuinely non-viable GPT-OSS tool path on this stack.

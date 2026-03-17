# OpenCode `/phase-a` Lane Incident Report

Date: 2026-03-12  
Scope: OpenCode command-path behavior for `/phase-a` across `deep`, `fast`, and `main`  
Audience: senior developer review and follow-on debugging / remediation design

## Executive Summary

OpenCode `/phase-a` is not behaving consistently across lanes for the same repo-investigation prompt.

For the three most recent comparable runs:

- `deep` completed the investigation correctly enough to inspect real repo files and produce a grounded answer.
- `fast` partially engaged, then emitted a malformed tool name and stopped after meta-planning instead of finishing the repo investigation.
- `main` did not attempt any repo tool use at all and returned a template-compliant but ungrounded answer.

This incident is not primarily a permissions problem and not primarily a missing-tool-surface problem. The tool surface was available in all three sessions. The divergence is in model behavior under the exact `/phase-a` prompt shape.

There is also a secondary OpenCode command-path inconsistency:

- exported session metadata shows the three runs were truly submitted as `deep`, `fast`, and `main`
- but raw `session.prompt` log lines mislabel two of those sessions as `litellm/deep`

That means at least one logging or command-labeling bug exists in the OpenCode command path, and raw `session.prompt` lines are not reliable as the sole source of truth for lane attribution in this incident.

## Follow-up Status

Post-incident normalization on 2026-03-13:

- canonical user-global command path is now `~/.config/opencode/commands/phase-a.md`
- the previous path `~/.opencode/commands/phase-a.md` was a local compatibility path and has been retired from active use
- a deprecated host-local copy may remain as `~/.opencode/commands/phase-a.md.deprecated` for rollback/reference
- this normalization does not change the historical facts of the incident below

## The Command Under Test

Command file under test at incident time:

- `~/.opencode/commands/phase-a.md`

Current frontmatter:

- `description: Read-only repo investigation and evidence gathering`
- `agent: plan`
- `model: litellm/main`

Current purpose:

- inject a long, structured, read-only investigation prompt
- force a fixed report shape
- bias the model toward evidence gathering rather than editing

Important drift at incident time:

- the current public OpenCode docs describe markdown commands under `~/.config/opencode/commands/` or project `.opencode/commands/`
- the active local command here lives in `~/.opencode/commands/phase-a.md`

This did not prove the command location was causing the lane inconsistency, but it was a real docs/runtime mismatch at the time and was tracked separately for normalization.

## Prompt Under Test

All three compared runs used this task through `/phase-a`:

> investigate how LiteLLM routing is defined in this repository. Identify the configuration files that define model aliases, routing behavior, and environment variables in `layer-gateway/litellm-orch`. Follow references into parent directories when necessary and determine which files are the source of truth versus documentation or examples.

## Affected Components

- OpenCode command runner
- OpenCode session logging / export path
- OpenCode agent/model selection behavior for markdown commands
- LiteLLM-backed direct lanes:
  - `deep`
  - `fast`
  - `main`
- Local command prompt file:
  - `~/.opencode/commands/phase-a.md`

## Compared Sessions

These three sessions are the primary evidence set:

| Session ID | User Model (export) | Assistant Model(s) (export) | Outcome |
| --- | --- | --- | --- |
| `ses_31b9c48adffecvc6yq4cN6350e` | `deep` | `deep` x8 | grounded repo investigation with real tool use |
| `ses_31b983cd3ffel9bJU861i8bMJ7` | `fast` | `fast` x2 | malformed tool name, then meta-planning only |
| `ses_31b9717a9ffeHhAGxo90CQ1vh3` | `main` | `main` x1 | no tool use, shallow template response |

## Timeline

### Session 1: `deep`

Session:

- `ses_31b9c48adffecvc6yq4cN6350e`

Created:

- 2026-03-12 23:31:06 UTC

Observed sequence:

1. OpenCode created a new session and injected the `/phase-a` body.
2. Tool registry initialized successfully.
3. Primary assistant calls ran on `deep`.
4. The model repeatedly used repo tools:
   - `glob`
   - `read`
   - `grep`
5. It read:
   - `layer-gateway/litellm-orch/config/router.yaml`
   - `layer-gateway/litellm-orch/config/env.local`
   - `layer-gateway/litellm-orch/config/env.example`
   - `layer-gateway/litellm-orch/SERVICE_SPEC.md`
6. It returned a grounded summary with concrete file evidence.

Result:

- best-performing lane in this incident
- the only lane that actually followed the intended Phase A workflow

### Session 2: `fast`

Session:

- `ses_31b983cd3ffel9bJU861i8bMJ7`

Created:

- 2026-03-12 23:35:31 UTC

Observed sequence:

1. OpenCode created a new session and injected the same `/phase-a` body.
2. Tool registry initialized successfully.
3. Primary assistant calls ran on `fast`.
4. First assistant turn produced reasoning and plan text about how it intended to inspect the repo.
5. It attempted one tool call, but the tool name was malformed:
   - `glob<|channel|>commentary`
6. OpenCode rejected that as an invalid tool.
7. Second assistant turn again described a plan and example tool payloads, but never executed real repo reads.
8. Session stopped without inspecting the target files.

Result:

- partial engagement only
- failed to convert plan text into real repo tool usage

### Session 3: `main`

Session:

- `ses_31b9717a9ffeHhAGxo90CQ1vh3`

Created:

- 2026-03-12 23:36:46 UTC

Observed sequence:

1. OpenCode created a new session and injected the same `/phase-a` body.
2. Tool registry initialized successfully.
3. Primary assistant call ran on `main`.
4. No reasoning parts were emitted.
5. No tool parts were emitted.
6. The model returned a fully formatted answer skeleton:
   - checklist remained `UNCERTAIN`
   - files checked remained empty
   - findings remained empty
   - recommended next step was to use `glob`
7. Session stopped immediately.

Result:

- worst-performing lane in this incident
- zero actual repo investigation happened

## Evidence Sources

Primary local evidence:

- command file:
  - `~/.opencode/commands/phase-a.md`
- OpenCode logs:
  - `~/.local/share/opencode/log/2026-03-12T233032.log`
  - `~/.local/share/opencode/log/2026-03-12T233501.log`
  - `~/.local/share/opencode/log/2026-03-12T233632.log`
- OpenCode DB:
  - `opencode db ...`
- OpenCode session exports:
  - `opencode export ses_31b9c48adffecvc6yq4cN6350e`
  - `opencode export ses_31b983cd3ffel9bJU861i8bMJ7`
  - `opencode export ses_31b9717a9ffeHhAGxo90CQ1vh3`

Relevant official docs:

- OpenCode commands:
  - <https://opencode.ai/docs/commands/>

## Confirmed Findings

### 1. Tool availability was not the blocker

All three sessions successfully initialized the same tool registry before the primary model call.

That included:

- `read`
- `glob`
- `grep`
- `bash`
- `edit`
- `write`
- `task`
- `webfetch`

Therefore:

- this was not a missing-tools incident
- this was not a permission-denied incident
- this was not a read-only-filesystem incident

### 2. `deep` is the only lane that reliably executed the Phase A workflow

The `deep` session:

- emitted reasoning
- called tools repeatedly
- read the expected repo files
- produced a grounded answer that matched the prompt intent much better than the other lanes

### 3. `fast` failed in a specific, non-random way

`fast` did not simply refuse tools.

Instead it:

- reasoned about using tools
- emitted plan text
- then attempted a malformed tool name containing a control/channel marker:
  - `glob<|channel|>commentary`

This strongly suggests prompt/control-token contamination of the tool name rather than a missing capability.

### 4. `main` did not even transition into tool use

`main`:

- emitted no reasoning
- emitted no tool calls
- returned a shell answer that only satisfied the requested report format

This means the current failure mode for `main` under `/phase-a` is not “tool call attempted and rejected.”

It is:

- “prompt-following without evidence-gathering”

### 5. The raw `session.prompt` log line is unreliable for model attribution here

For the `fast` and `main` sessions, raw logs claim:

- `model=litellm/deep`

But exported session metadata proves:

- one user message was `fast`
- one user message was `main`

That contradiction means:

- exported session JSON and message metadata are more trustworthy than the single raw `session.prompt` line for this incident

### 6. `/phase-a` frontmatter model override is not behaving consistently

Current local file declares:

- `model: litellm/main`

But the three compared sessions were truly submitted as:

- `deep`
- `fast`
- `main`

That means the current runtime is not consistently honoring the command file’s `model:` line, even though the command body is definitely being injected.

What is not yet proven:

- whether this is caused by command-frontmatter precedence
- whether it is caused by the undocumented `~/.opencode/commands/` location
- whether it is caused by a web-session override layer after command resolution

## Related Contradictions and Drift

### Drift 1: documented command locations vs local runtime

Official docs describe markdown commands in:

- `~/.config/opencode/commands/`
- project `.opencode/commands/`

Live local file is:

- `~/.opencode/commands/phase-a.md`

The file is clearly active, so either:

- undocumented compatibility exists
- or local runtime behavior has diverged from current docs

### Drift 2: command body appears stable, model override does not

Across recent sessions:

- the `/phase-a` body is injected consistently
- `agent=plan` appears consistent
- `model:` behavior is not consistent

That points to a narrower bug than “command loading is broken.”

## Likely Causes

These are evidence-based hypotheses, not final proof.

### Likely Cause A: prompt-shape sensitivity by lane

The `/phase-a` body is long and highly structured.

It strongly emphasizes:

- checklisting
- candidate paths
- exact output shape
- confidence reporting
- a recommended next step

Observed effect:

- `main` satisfies the shape but skips the evidence-gathering work
- `fast` partially reasons about the work, then degrades into malformed tool use
- `deep` is capable of executing the intended workflow despite the same structure

This makes prompt-shape sensitivity the leading explanation for the lane divergence.

### Likely Cause B: tool-call serialization contamination on `fast`

The malformed tool name:

- `glob<|channel|>commentary`

is not a normal model error like choosing the wrong existing tool.

It looks like internal channel/control-token leakage into the emitted tool name.

This should be treated as a model-output-formatting issue specific to `fast` under this prompt shape unless disproven.

### Likely Cause C: `main` is over-indexing on “report structure” instead of action

`main` behaved as if the highest-priority requirement was:

- produce the requested markdown scaffold immediately

instead of:

- satisfy the scaffold with real inspected evidence

This is consistent with a lane-specific weakness on tool-triggering when the prompt allows a low-effort, format-compliant response.

## Constraints

Constraints established during investigation:

- user wants a full incident report suitable for sharing
- no secrets may be committed to git
- no runtime mutation was required for this report
- evidence should be grounded in local logs, DB, and exports
- fixes should not be assumed from symptoms alone

Technical constraints relevant to follow-on work:

- current command path behavior is inconsistent enough that logs alone are insufficient
- exported session JSON must be treated as authoritative for model attribution in this incident
- any prompt redesign should preserve read-only behavior and evidence-first investigation

## Blockers

### Blocker 1: no proven root cause for command-model precedence inconsistency

We know:

- the `model:` frontmatter is not behaving consistently

We do not yet know:

- whether that is a command-loader bug
- a path-resolution issue
- a web-session override behavior
- or a logging bug plus normal model selection

### Blocker 2: prompt redesign and command-precedence debugging are separate workstreams

Two different problems are present:

1. lane behavior under the Phase A prompt
2. inconsistent command/log/model override behavior

They are related, but not identical. A fix plan should decide which one to tackle first.

## Security / Handling Notes

During the successful `deep` run, the model read:

- `layer-gateway/litellm-orch/config/env.local`

That file contains secret-looking runtime values.

This report intentionally does not quote those values.

If raw session exports are shared outside the trusted development group, they should be redacted first.

## Open Questions

- Why does `/phase-a` inject correctly while its `model:` line does not behave consistently?
- Is `~/.opencode/commands/` an intentionally supported compatibility path or accidental working behavior?
- Can `fast` recover from the malformed tool-name issue with a shorter or less rigid prompt?
- Can `main` be made to use tools reliably on this task purely by changing prompt shape, or is the lane fundamentally weak for this class of command?
- Should `phase-a` continue to force the `plan` agent, or should it become lane-neutral and only inject the task scaffold?

## Recommended Review Focus For Another Senior Engineer

Suggested order of review:

1. Review the three exported sessions side by side before trusting the raw log labels.
2. Treat `deep` as the current behavioral baseline for what “working” looks like.
3. Inspect why `fast` emitted `glob<|channel|>commentary` instead of `glob`.
4. Inspect why `main` returned a zero-evidence report shell rather than attempting any tool use.
5. Inspect command-frontmatter precedence and command path handling for `~/.opencode/commands/phase-a.md`.

## Bottom Line

This incident is not one single failure.

It is a combination of:

- prompt-shape sensitivity across lanes
- `fast` tool-name corruption
- `main` evidence-free prompt completion
- and a separate command/log/model-attribution inconsistency

For this exact `/phase-a` task today:

- `deep` is usable
- `fast` is unreliable
- `main` is not trustworthy

That is the current evidence-backed state.

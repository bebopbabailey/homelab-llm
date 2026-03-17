# OpenCode Native Config Follow-Up Report

Date: 2026-03-16  
Host: Mini  
Scope: disposable OpenCode native Responses config follow-up for GPT-OSS 20B

## Executive Summary

Outcome classification: `Outcome 4`

The follow-up pass found that OpenCode can stay on the native Responses route, but local config changes did not alter the two constrained request-shape requirements that matter for GPT-OSS 20B on the current backend:

- request path stayed `POST /v1/responses`
- `stream` stayed `true`
- `temperature` stayed absent / `null`

Neither of the two plausible config control surfaces moved the outbound request body:

- `agent.temperature = 0.0`
- provider-model `options = {"stream": false, "temperature": 0.0}`

Because neither surface changed the request at all, the approved gating rule did not justify running the combined case or the conditional tools-bearing follow-up case.

## Scope and Constraints

This pass was intentionally narrow.

In scope:

- disposable OpenCode config only
- CLI path only
- exact outbound request-shape capture
- no production config changes

Out of scope:

- LiteLLM alias changes
- launchd or MLX changes
- broader GPT-OSS viability work
- tool-calling viability
- new shim or app-logic work

## Baseline Carried Into This Pass

The preceding native-provider audit had already established:

- the live OpenCode path still uses `@ai-sdk/openai-compatible`
- a disposable native `@ai-sdk/openai` config does hit `POST /v1/responses`
- the native request still sent `stream: true` and omitted `temperature`

This follow-up pass existed only to test whether config alone could correct that request shape.

## Test Setup

Disposable audit root:

- `/tmp/20260316T192139Z-gptoss20b-native-config-contract-followup/`

Reusable temp harness:

- capture server: `/tmp/20260316T192139Z-gptoss20b-native-config-contract-followup/capture_server.py`
- case runner: `/tmp/20260316T192139Z-gptoss20b-native-config-contract-followup/run_case.sh`

Executed cases:

1. `01-synth-baseline`
2. `02-agent-temp0`
3. `03-modelopts`

Skipped by plan gate:

4. `04-combined`
5. `05-tools-present`

## Case Matrix

### Case 01: `01-synth-baseline`

Purpose:

- test the native Responses path with a synthesis-oriented disposable agent

Config deltas:

- none beyond the base native config

Key artifacts:

- request: `/tmp/20260316T192139Z-gptoss20b-native-config-contract-followup/cases/01-synth-baseline/artifacts/last-request.json`
- response: `/tmp/20260316T192139Z-gptoss20b-native-config-contract-followup/cases/01-synth-baseline/artifacts/last-response.json`
- stderr: `/tmp/20260316T192139Z-gptoss20b-native-config-contract-followup/cases/01-synth-baseline/artifacts/opencode-run.stderr.log`

Observed result:

- path: `/v1/responses`
- `stream: true`
- `temperature: null`
- `tools` present with one serialized function tool
- response: `422 constrained_contract_mismatch`

### Case 02: `02-agent-temp0`

Purpose:

- test whether `agent.temperature = 0.0` is forwarded to the native request

Config deltas:

- `agent.audit-synth.temperature = 0.0`
- `agent.audit-tool.temperature = 0.0`

Key artifacts:

- request: `/tmp/20260316T192139Z-gptoss20b-native-config-contract-followup/cases/02-agent-temp0/artifacts/last-request.json`
- response: `/tmp/20260316T192139Z-gptoss20b-native-config-contract-followup/cases/02-agent-temp0/artifacts/last-response.json`
- merged config: `/tmp/20260316T192139Z-gptoss20b-native-config-contract-followup/cases/02-agent-temp0/artifacts/debug-config.json`

Observed result:

- path: `/v1/responses`
- `stream: true`
- `temperature: null`
- no change from Case 01 on the constrained fields
- response: `422 constrained_contract_mismatch`

### Case 03: `03-modelopts`

Purpose:

- test whether provider-model `options` can force `stream = false` and `temperature = 0.0`

Config deltas:

- `provider.pilot-native.models.test.options.stream = false`
- `provider.pilot-native.models.test.options.temperature = 0.0`

Key artifacts:

- request: `/tmp/20260316T192139Z-gptoss20b-native-config-contract-followup/cases/03-modelopts/artifacts/last-request.json`
- response: `/tmp/20260316T192139Z-gptoss20b-native-config-contract-followup/cases/03-modelopts/artifacts/last-response.json`
- merged config: `/tmp/20260316T192139Z-gptoss20b-native-config-contract-followup/cases/03-modelopts/artifacts/debug-config.json`

Observed result:

- path: `/v1/responses`
- `stream: true`
- `temperature: null`
- no change from Case 01 on the constrained fields
- response: `422 constrained_contract_mismatch`

## Cross-Case Findings

### 1. Native Responses routing was preserved

All executed cases used:

- `POST /v1/responses`

This confirms the provider package path remained native during the follow-up pass.

### 2. Neither plausible config lever changed the constrained request shape

Across all three executed cases:

- `stream` remained `true`
- `temperature` remained absent / `null`

This was true even when:

- agent temperature was set to `0.0`
- model options explicitly set `stream: false` and `temperature: 0.0`

### 3. The synthesis-oriented disposable agent still serialized a tool

Case 01 still included:

- `tool_choice: "auto"`
- one serialized function tool
- first tool name: `todowrite`

This is visible in:

- `/tmp/20260316T192139Z-gptoss20b-native-config-contract-followup/cases/01-synth-baseline/artifacts/last-request.json`

That matters because it shows tool serialization is not eliminated simply by disabling the user-defined tool set in the disposable agent config.

### 4. Repo-local config still merged into the disposable config surface

The merged debug config still showed repo defaults such as:

- `model: "litellm/deep"`
- `default_agent: "repo-deep"`

But the actual captured request still used:

- model `test`
- provider path `/v1/responses`
- the explicitly selected disposable agent

This means the repo-local config was merged, but the per-run `-m pilot-native/test` and `--agent audit-synth` overrides still controlled the emitted request.

### 5. Case 04 and Case 05 were correctly skipped

The approved execution logic said:

- run Case 04 only if Case 02 or Case 03 showed partial movement
- run Case 05 only if a synthesis case fully matched the constrained contract

Neither prerequisite was met.

## Commands Run

Preparation and validation:

- `opencode --version`
- `opencode run --help`
- `sed -n '1,120p' NOW.md`
- `jq . <case config>`

Per-case execution:

- `/tmp/20260316T192139Z-gptoss20b-native-config-contract-followup/run_case.sh /tmp/20260316T192139Z-gptoss20b-native-config-contract-followup/cases/01-synth-baseline native-followup-01 audit-synth "Reply with exactly: native-config-ok"`
- `/tmp/20260316T192139Z-gptoss20b-native-config-contract-followup/run_case.sh /tmp/20260316T192139Z-gptoss20b-native-config-contract-followup/cases/02-agent-temp0 native-followup-02 audit-synth "Reply with exactly: native-config-ok"`
- `/tmp/20260316T192139Z-gptoss20b-native-config-contract-followup/run_case.sh /tmp/20260316T192139Z-gptoss20b-native-config-contract-followup/cases/03-modelopts native-followup-03 audit-synth "Reply with exactly: native-config-ok"`

Post-run evidence extraction:

- `jq` summaries against `last-request.json`, `last-response.json`, and `debug-config.json`
- `rg` against per-case stderr logs

## Notable Runtime Notes

- Each isolated case root performed a one-time disposable SQLite migration inside its own `data` directory.
- The capture harness behaved as expected and returned `422 constrained_contract_mismatch` for every executed case because the request shape still violated the constrained backend contract.

## Final Interpretation

This pass did not find a config-only path to force the native OpenCode Responses request into the GPT-OSS 20B backend’s constrained contract.

What it did prove:

- the native provider path is real and stable enough to test
- the two most plausible config surfaces do not currently alter `stream` or `temperature`
- local config tuning should stop here unless a new, evidence-backed control surface is discovered

Practical conclusion:

- a simple native-provider swap is not sufficient
- further progress is more likely to come from a thin translator/shim layer or an upstream/OpenCode-side fix than from additional local config tweaking

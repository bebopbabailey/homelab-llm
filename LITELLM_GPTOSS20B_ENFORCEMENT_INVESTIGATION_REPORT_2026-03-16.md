# LiteLLM GPT-OSS 20B Enforcement Investigation Report

Date: 2026-03-16  
Host: Mini  
Scope: narrow LiteLLM enforcement investigation for the GPT-OSS 20B experimental Responses path used by OpenCode

## Executive summary

This pass answered the next decision question after the native OpenCode config follow-up: whether LiteLLM can become the enforcement seam for the already-validated GPT-OSS 20B constrained contract, instead of pushing more request-shape logic into OpenCode-specific shims.

The answer is yes, but not with config alone.

Findings:
- OpenCode-native caller behavior remained on `POST /v1/responses`, but still sent `stream=true` and omitted `temperature`.
- LiteLLM config-only enforcement on a fresh temporary alias was partially effective:
  - it preserved `/v1/responses`
  - it forced `temperature: 0.0`
  - it did not suppress `stream: true`
- A narrow LiteLLM pre-call normalize guardrail, scoped only to the temporary alias, was sufficient:
  - backend path stayed `/v1/responses`
  - backend saw `stream: false`
  - backend saw `temperature: 0.0`
  - direct noop-tool, retrieval, and follow-up all succeeded under that enforcement
  - one real OpenCode tools-bearing request also preserved those invariants

Primary conclusion:
- LiteLLM is a viable enforcement seam for this GPT-OSS 20B experimental path.
- LiteLLM config alone is insufficient.
- A narrow pre-call normalize guardrail is sufficient.
- Reject-mode enforcement was not needed in this pass because normalize mode worked cleanly.

## Background

This investigation was intentionally narrow.

It did not reopen general GPT-OSS model viability. That question was already answered locally for the constrained experimental backend contract:
- `/v1/responses`
- `stream=false`
- `temperature=0.0`
- experimental callers only

The preceding OpenCode-native config follow-up had already established:
- native provider selection alone is not enough
- OpenCode can remain on `/v1/responses`
- but local OpenCode config tuning did not suppress streaming or force temperature

That made LiteLLM the next honest seam to test because it already sits between caller and backend, already supports `/v1/responses`, and already exposes documented request-modification hooks.

## Question under test

This pass was designed to answer four questions:

1. Can LiteLLM enforce `/v1/responses`, `stream=false`, and `temperature=0.0` for this GPT-OSS 20B path?
2. If yes, can that be done with LiteLLM config/model params alone, or does it require a pre-call hook?
3. Can LiteLLM fail closed if a caller sends a request outside the constrained contract?
4. Is LiteLLM a cleaner support seam than more OpenCode-specific request-shape churn?

## Experimental topology

The investigation used one fresh temporary alias and one experimental backend lane only.

Temporary alias:
- `metal-test-gptoss20b-enforce`

Callers:
- direct `/v1/responses` caller through LiteLLM for the primary noop-tool and retrieval/follow-up truth tests
- disposable OpenCode native-provider config for:
  - one plain non-tool smoke
  - one secondary tools-bearing smoke

Gateway:
- existing LiteLLM service on Mini `127.0.0.1:4000`

Capture path:
- Mini loopback capture-forwarder on `127.0.0.1:8874/v1`
- Mini loopback tunnel on `127.0.0.1:8875` forwarding to the Studio experimental backend

Backend:
- Studio experimental Responses backend on `127.0.0.1:8120`
- served model `mlx-gpt-oss-20b-mxfp4-q4-exp-constrained`

All changes were temporary and rolled back at the end of the pass.

## Sources and local surfaces consulted

Primary public anchors:
- LiteLLM proxy call hooks: https://docs.litellm.ai/docs/proxy/call_hooks
- LiteLLM proxy config settings: https://docs.litellm.ai/docs/proxy/config_settings
- LiteLLM OpenAI Responses support: https://docs.litellm.ai/docs/providers/openai/responses_api
- LiteLLM Responses release notes: https://docs.litellm.ai/release_notes/tags/responses-api
- OpenCode providers docs: https://opencode.ai/docs/providers/
- OpenCode issue history:
  - https://github.com/anomalyco/opencode/issues/5037
  - https://github.com/anomalyco/opencode/issues/2785
  - https://github.com/anomalyco/opencode/issues/4698

Repo-local service surfaces read before mutation:
- [layer-gateway/litellm-orch/AGENTS.md](/home/christopherbailey/homelab-llm/layer-gateway/litellm-orch/AGENTS.md)
- [layer-gateway/litellm-orch/CONSTRAINTS.md](/home/christopherbailey/homelab-llm/layer-gateway/litellm-orch/CONSTRAINTS.md)
- [layer-gateway/litellm-orch/RUNBOOK.md](/home/christopherbailey/homelab-llm/layer-gateway/litellm-orch/RUNBOOK.md)
- [layer-gateway/litellm-orch/SERVICE_SPEC.md](/home/christopherbailey/homelab-llm/layer-gateway/litellm-orch/SERVICE_SPEC.md)
- [layer-gateway/litellm-orch/config/router.yaml](/home/christopherbailey/homelab-llm/layer-gateway/litellm-orch/config/router.yaml)
- [layer-gateway/litellm-orch/config/env.local](/home/christopherbailey/homelab-llm/layer-gateway/litellm-orch/config/env.local)
- [layer-gateway/litellm-orch/config/harmony_guardrail.py](/home/christopherbailey/homelab-llm/layer-gateway/litellm-orch/config/harmony_guardrail.py)
- [layer-gateway/litellm-orch/config/transcribe_guardrail.py](/home/christopherbailey/homelab-llm/layer-gateway/litellm-orch/config/transcribe_guardrail.py)
- [layer-gateway/litellm-orch/docs/litellm-extension-points.md](/home/christopherbailey/homelab-llm/layer-gateway/litellm-orch/docs/litellm-extension-points.md)
- [OPENCODE_NATIVE_CONFIG_FOLLOWUP_REPORT_2026-03-16.md](/home/christopherbailey/homelab-llm/OPENCODE_NATIVE_CONFIG_FOLLOWUP_REPORT_2026-03-16.md)
- [GPT_OSS_20B_OPENCODE_CALLER_FACING_PILOT_REVIEW_PACK_2026-03-16.md](/home/christopherbailey/homelab-llm/GPT_OSS_20B_OPENCODE_CALLER_FACING_PILOT_REVIEW_PACK_2026-03-16.md)

## Enforcement options tested

### Option 1: LiteLLM config / model-param enforcement only

This branch used a fresh alias in LiteLLM with model-scoped params:
- `temperature: 0.0`
- `stream: false`

The goal was to determine whether LiteLLM config alone could preserve the already-validated contract even when callers still sent out-of-contract payloads.

Result:
- partially effective
- insufficient on its own

What changed:
- backend received `temperature: 0.0`

What did not change:
- backend still received `stream: true`

Interpretation:
- config/model params can supply a numeric temperature override for this path
- config/model params did not reliably suppress explicit caller streaming on the Responses path

### Option 2: LiteLLM pre-call normalize guardrail

This branch added a temporary narrow pre-call guardrail scoped only to the temporary alias.

The guardrail did not rewrite tools, did not translate chat/completions into Responses, and did not change response content. It only normalized the already-validated transport constraints on the experimental lane:
- `temperature=0.0`
- `stream=false`

Result:
- sufficient

What changed:
- ingress request still arrived with `stream=true` and `temperature=null`
- backend request left LiteLLM with `stream=false` and `temperature=0.0`

### Option 3: Reject-mode enforcement

This branch was planned but not needed.

It was intentionally skipped because normalize mode already preserved the contract cleanly. There was no value in adding a stronger failure mode once the narrow rewrite path had been proven sufficient.

## Detailed findings

### 1. Config-only LiteLLM enforcement was insufficient

The first branch proved LiteLLM config alone was not enough.

Config-only ingress to LiteLLM:
- path: `/v1/responses`
- model: `metal-test-gptoss20b-enforce`
- `stream: true`
- `temperature: null`

Config-only backend request from LiteLLM:
- path: `/v1/responses`
- model: `mlx-gpt-oss-20b-mxfp4-q4-exp-constrained`
- `stream: true`
- `temperature: 0.0`

This is the central config-only result:
- path enforcement was already fine
- temperature could be forced
- streaming still leaked through to the backend

That means config/model params alone cannot be treated as a complete enforcement seam for this path.

### 2. Pre-call normalize guardrail was sufficient

After adding a narrow temporary pre-call guardrail and restarting LiteLLM cleanly, the same caller-side shape was normalized before backend dispatch.

Ingress to LiteLLM under normalize mode:
- path: `/v1/responses`
- model: `metal-test-gptoss20b-enforce`
- `stream: true`
- `temperature: null`

Backend request under normalize mode:
- path: `/v1/responses`
- model: `mlx-gpt-oss-20b-mxfp4-q4-exp-constrained`
- `stream: false`
- `temperature: 0.0`

This held across:
- direct noop-tool initial turn
- direct retrieval
- direct follow-up continuation
- one real OpenCode tools-bearing request

### 3. Direct noop-tool initial turn succeeded under normalize mode

The primary truth test used a direct `/v1/responses` caller with:
- one narrow function-style `noop` tool
- `tool_choice: auto`
- `store: true`
- deliberately bad upstream shape:
  - `stream: true`
  - omitted `temperature`

Under normalize enforcement:
- LiteLLM preserved the Responses path
- LiteLLM sent `stream: false` to the backend
- LiteLLM sent `temperature: 0.0` to the backend
- the backend returned a valid stored response including the expected tool call

Important captured value:
- returned tool `call_id`: `call_8bf9755d71a804d3`

The recorded caller-visible response is in:
- [/tmp/20260316T221444Z-litellm-gptoss20b-enforcement/artifacts/openai-direct-noop.hook.response.json](/tmp/20260316T221444Z-litellm-gptoss20b-enforcement/artifacts/openai-direct-noop.hook.response.json)

### 4. Retrieval and follow-up continuation also succeeded under normalize mode

The second primary truth test was stored Responses continuity.

Retrieval succeeded:
- a canonical stored response was returned
- the retrieval payload preserved the function call id

Follow-up also succeeded when the continuation used the canonical retrieved identifiers instead of earlier streamed event ids.

This is an important nuance:
- the need to use canonical `response_id` and `call_id` from retrieval/non-streaming state appears to be a Responses-store/runtime behavior
- it is not evidence that LiteLLM enforcement failed

The follow-up response returned assistant output `"Done."`

Relevant artifacts:
- [/tmp/20260316T221444Z-litellm-gptoss20b-enforcement/artifacts/openai-direct-retrieve.hook.response.json](/tmp/20260316T221444Z-litellm-gptoss20b-enforcement/artifacts/openai-direct-retrieve.hook.response.json)
- [/tmp/20260316T221444Z-litellm-gptoss20b-enforcement/artifacts/openai-direct-followup.hook.response.json](/tmp/20260316T221444Z-litellm-gptoss20b-enforcement/artifacts/openai-direct-followup.hook.response.json)

### 5. Real OpenCode tools-bearing serialization also preserved the enforced contract

After the direct caller scenarios succeeded, the pass ran one secondary actual OpenCode tools-bearing smoke through the same LiteLLM experimental alias.

This case was intentionally secondary:
- it did not replace the direct-caller verdict
- it was not a broad OpenCode tool benchmark
- it only checked whether the same enforcement still held when a real OpenCode tools-bearing request came through

OpenCode tools-bearing ingress summary:
- path: `/v1/responses`
- model: `metal-test-gptoss20b-enforce`
- `stream: true`
- `temperature: null`
- `tool_choice: "auto"`
- `tool_count: 10`

Backend summary for that same request:
- path: `/v1/responses`
- model: `mlx-gpt-oss-20b-mxfp4-q4-exp-constrained`
- `stream: false`
- `temperature: 0.0`
- `tool_choice: "auto"`
- `tool_count: 10`

This does not prove parity with the earlier narrow noop-function tool contract. It does prove that LiteLLM enforcement still preserved the basic constrained transport invariants on a real OpenCode tools-bearing request serialization.

## Raw evidence

Primary artifact root:
- [/tmp/20260316T221444Z-litellm-gptoss20b-enforcement](/tmp/20260316T221444Z-litellm-gptoss20b-enforcement)

Most important artifacts:
- ingress capture:
  - [/tmp/20260316T221444Z-litellm-gptoss20b-enforcement/artifacts/ingress-requests.jsonl](/tmp/20260316T221444Z-litellm-gptoss20b-enforcement/artifacts/ingress-requests.jsonl)
- backend capture:
  - [/tmp/20260316T221444Z-litellm-gptoss20b-enforcement/artifacts/forwarder-requests.jsonl](/tmp/20260316T221444Z-litellm-gptoss20b-enforcement/artifacts/forwarder-requests.jsonl)
  - [/tmp/20260316T221444Z-litellm-gptoss20b-enforcement/artifacts/forwarder-responses.jsonl](/tmp/20260316T221444Z-litellm-gptoss20b-enforcement/artifacts/forwarder-responses.jsonl)
- OpenCode plain smoke:
  - [/tmp/20260316T221444Z-litellm-gptoss20b-enforcement/artifacts/opencode-plain.stdout.jsonl](/tmp/20260316T221444Z-litellm-gptoss20b-enforcement/artifacts/opencode-plain.stdout.jsonl)
  - [/tmp/20260316T221444Z-litellm-gptoss20b-enforcement/artifacts/opencode-plain.stderr.log](/tmp/20260316T221444Z-litellm-gptoss20b-enforcement/artifacts/opencode-plain.stderr.log)
- direct config-only baseline:
  - [/tmp/20260316T221444Z-litellm-gptoss20b-enforcement/artifacts/openai-direct-noop.response.raw](/tmp/20260316T221444Z-litellm-gptoss20b-enforcement/artifacts/openai-direct-noop.response.raw)
  - [/tmp/20260316T221444Z-litellm-gptoss20b-enforcement/artifacts/openai-direct-retrieve.response.json](/tmp/20260316T221444Z-litellm-gptoss20b-enforcement/artifacts/openai-direct-retrieve.response.json)
  - [/tmp/20260316T221444Z-litellm-gptoss20b-enforcement/artifacts/openai-direct-followup.response.raw](/tmp/20260316T221444Z-litellm-gptoss20b-enforcement/artifacts/openai-direct-followup.response.raw)
  - [/tmp/20260316T221444Z-litellm-gptoss20b-enforcement/artifacts/openai-direct-followup-canonical.response.raw](/tmp/20260316T221444Z-litellm-gptoss20b-enforcement/artifacts/openai-direct-followup-canonical.response.raw)
- direct normalize-hook path:
  - [/tmp/20260316T221444Z-litellm-gptoss20b-enforcement/artifacts/openai-direct-noop.hook.response.json](/tmp/20260316T221444Z-litellm-gptoss20b-enforcement/artifacts/openai-direct-noop.hook.response.json)
  - [/tmp/20260316T221444Z-litellm-gptoss20b-enforcement/artifacts/openai-direct-retrieve.hook.response.json](/tmp/20260316T221444Z-litellm-gptoss20b-enforcement/artifacts/openai-direct-retrieve.hook.response.json)
  - [/tmp/20260316T221444Z-litellm-gptoss20b-enforcement/artifacts/openai-direct-followup.hook.response.json](/tmp/20260316T221444Z-litellm-gptoss20b-enforcement/artifacts/openai-direct-followup.hook.response.json)
- OpenCode tools-bearing smoke under normalize hook:
  - [/tmp/20260316T221444Z-litellm-gptoss20b-enforcement/artifacts/opencode-tools-hook.stdout.jsonl](/tmp/20260316T221444Z-litellm-gptoss20b-enforcement/artifacts/opencode-tools-hook.stdout.jsonl)
  - [/tmp/20260316T221444Z-litellm-gptoss20b-enforcement/artifacts/opencode-tools-hook.stderr.log](/tmp/20260316T221444Z-litellm-gptoss20b-enforcement/artifacts/opencode-tools-hook.stderr.log)
- final restored health:
  - [/tmp/20260316T221444Z-litellm-gptoss20b-enforcement/artifacts/health-restored.json](/tmp/20260316T221444Z-litellm-gptoss20b-enforcement/artifacts/health-restored.json)

## Journal evidence

After the clean service restart with the temporary guardrail enabled, `journalctl -u litellm-orch.service` showed the guardrail loading.

The key evidence line was:
- `Initializing custom guardrail: responses_contract_guardrail.ResponsesContractGuardrail`

The guardrail list also included the new pre-call guardrail after restart.

This matters because the hook trace file itself did not populate reliably. The strongest enforcement evidence therefore comes from:
- journal initialization lines proving the guardrail was loaded
- ingress capture proving the caller still sent the bad shape
- backend capture proving LiteLLM emitted the normalized shape

## Commands and execution flow

High-level execution sequence:

1. Read required repo and service constraints.
2. Inspect `router.yaml`, `env.local`, existing guardrails, and LiteLLM extension points.
3. Confirm LiteLLM readiness and model exposure on Mini.
4. Add a fresh temporary alias for the experiment in LiteLLM.
5. Add temporary local env entries pointing the alias at the Mini loopback capture-forwarder.
6. Start the Studio experimental backend on `127.0.0.1:8120`.
7. Establish the Mini loopback tunnel and capture forwarders.
8. Restart LiteLLM and verify readiness.
9. Run config-only OpenCode plain smoke.
10. Run config-only direct noop and retrieval/follow-up probes.
11. Add a temporary pre-call guardrail and a temporary unit test.
12. Run the unit test for the guardrail and verify it passed.
13. Restart LiteLLM and confirm guardrail initialization in journal logs.
14. Run normalize-hook direct noop, retrieval, and follow-up.
15. Run one secondary actual OpenCode tools-bearing smoke.
16. Restore `router.yaml` and `env.local`.
17. Restart LiteLLM back to baseline.
18. Stop loopback forwarders, tunnel, and the Studio backend.
19. Confirm final readiness and baseline runtime state.

Representative command categories used:
- `sed`, `rg`, and `git diff` for repo inspection
- `curl` for LiteLLM readiness, models, and direct HTTP probes
- `uv run python` and direct Python invocations for tiny direct Responses callers and capture helpers
- `journalctl -u litellm-orch.service` for service initialization evidence
- `systemctl restart litellm-orch.service` for controlled runtime refresh
- unit test execution for the temporary guardrail

## Outcome classification

This pass lands in:
- `LiteLLM hook enforcement is sufficient`

Why:
- config-only enforcement was insufficient because `stream=true` still reached the backend
- narrow pre-call normalize enforcement was sufficient because the backend consistently received:
  - `/v1/responses`
  - `stream=false`
  - `temperature=0.0`

This result applies to:
- the primary direct Responses noop-tool scenario
- the primary direct retrieval/follow-up scenario
- one secondary actual OpenCode tools-bearing request

## What this pass does and does not prove

Proven:
- LiteLLM is a clean enough enforcement seam for this narrow GPT-OSS 20B experimental path
- the experimental contract can be preserved without further OpenCode config churn
- a small pre-call normalize guardrail is enough to enforce the already-validated transport constraints

Not proven:
- that config-only LiteLLM enforcement is sufficient
- that reject-mode policy is needed
- that OpenCode tool behavior is broadly validated
- that this should immediately become a permanent production policy
- that the OpenCode tools-bearing serialization is identical to the previously validated noop-function schema

## Caveats and skipped checks

Skipped:
- reject-mode branch was not run because normalize mode was already sufficient

Caveats:
- the temporary guardrail self-trace file remained empty even though the guardrail was active
- enforcement evidence therefore relies on capture artifacts and journal initialization lines rather than the empty hook trace
- the secondary OpenCode tools-bearing smoke was intentionally not broadened into a larger tool-viability pass
- once the tools-bearing request shape and backend invariants were confirmed, the lingering OpenCode process was stopped
- no production alias or canonical lane assignment was changed at any point

## Rollback and final state

The investigation was rolled back to baseline after evidence capture.

Restored:
- `router.yaml`
- `env.local`

Temporary files created and later removed:
- `layer-gateway/litellm-orch/config/responses_contract_guardrail.py`
- `layer-gateway/litellm-orch/tests/test_responses_contract_guardrail.py`

Temporary listeners shut down:
- `127.0.0.1:8874`
- `127.0.0.1:8875`
- `127.0.0.1:8876`

Experimental backend shut down:
- Studio `127.0.0.1:8120`

Final runtime state:
- Mini LiteLLM readiness restored on `127.0.0.1:4000`
- only baseline service listeners remained live
- no temporary alias or temporary guardrail wiring remained active

At the end of the execution pass, the only repo-tracked file still changed was:
- [NOW.md](/home/christopherbailey/homelab-llm/NOW.md)

## Recommended next decision

The next decision should be narrow and explicit:

- either codify the LiteLLM pre-call normalize guardrail for an experimental GPT-OSS 20B lane
- or keep the path fail-closed until that guardrail is productized deliberately

What should not happen next:
- more OpenCode config churn without new evidence
- broad GPT-OSS viability arguments
- conflating this narrow enforcement result with a full multi-interface production readiness claim

## Bottom line

The investigation achieved its goal.

LiteLLM can enforce the already-validated GPT-OSS 20B constrained contract for the OpenCode path, but not with config alone. A narrow pre-call normalize guardrail was sufficient to preserve `/v1/responses`, `stream=false`, and `temperature=0.0` across both the primary direct Responses path and one secondary real OpenCode tools-bearing request.

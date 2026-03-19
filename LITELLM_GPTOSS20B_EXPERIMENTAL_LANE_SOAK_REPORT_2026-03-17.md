# LiteLLM GPT-OSS 20B Experimental Lane Soak Report

Date: 2026-03-17
Host: Mini
Scope: `layer-gateway/litellm-orch` experimental alias `metal-test-gptoss20b-enforce`

## Executive summary
This pass was the bounded day-2 operations confidence soak for the kept GPT-OSS 20B LiteLLM enforcement lane. The question was no longer whether the LiteLLM seam could enforce the constrained transport contract once. That had already been established. The question here was whether the kept experimental lane stayed clean, observable, and operationally understandable over a modest sequence of repeated requests, and whether the resulting evidence was strong enough to justify planning a controlled promotion toward canonical `fast`.

The answer is no, not yet.

The lane remains operationally useful as an experimental lane. Its transport enforcement stayed intact. Requests that reached the backend remained on `/v1/responses` and consistently arrived as `stream=false` and `temperature=0.0`. Guardrail-local JSONL plus journald remained readable enough for debugging. But the pass still surfaced a repeated instability in the narrow tool path: a repeated direct noop-tool turn again exhausted `max_output_tokens` in reasoning and never emitted the expected function call. That prevented the follow-up continuation from being completed in the final round of the soak.

That outcome blocks promotion planning. The transport seam looks good. The repeated narrow tool behavior does not yet look stable enough for a canonical-`fast` promotion plan.

## Why this pass existed
This was a promotion-eligibility gate, not a promotion pass.

At the start of this soak, the following should be treated as already established:
- GPT-OSS 20B had a validated constrained backend contract on the experimental path:
  - `/v1/responses`
  - non-streaming
  - `temperature=0.0`
- OpenCode configuration alone was not sufficient to preserve that contract.
- LiteLLM config-only enforcement was also not sufficient because `stream=true` could still leak through.
- A narrow LiteLLM pre-call normalize guardrail was sufficient to force the backend to see the constrained contract.
- That guardrail had already been codified onto the experimental alias `metal-test-gptoss20b-enforce`.
- A bounded regression had already passed for:
  - direct plain text
  - direct synthesis
  - noop-tool initial turn
  - retrieval plus follow-up continuation
  - one real OpenCode plain smoke
  - one real OpenCode tools-bearing smoke

Because of that, this pass was not another backend viability exercise and not another OpenCode tuning exercise. It was a modest soak intended to answer a narrower operational question:

Can the kept experimental lane stay stable and observable over time, with enough confidence to justify designing a controlled promotion plan toward canonical `fast`?

## Lane and policy under test
Only one lane was in scope:
- `metal-test-gptoss20b-enforce`

Its enforced policy remained narrow:
- Responses-only lane behavior
- normalize `stream=false`
- normalize `temperature=0.0`
- reject non-Responses requests on the lane
- do not rewrite tool schemas
- do not rewrite continuation fields
- do not rewrite response content

That policy was not broadened during this pass.

## Observability model used in this pass
This pass relied on the observability model established during the earlier experimental codification pass:
- convenience trace:
  - `/tmp/litellm_responses_contract_guardrail.jsonl`
- durable source of truth:
  - `journalctl -u litellm-orch.service`
- hop-by-hop capture:
  - caller -> LiteLLM ingress capture
  - LiteLLM -> backend capture
  - backend response capture
  - caller-visible response capture where attributable

That mattered because the soak’s purpose was not just to prove transport normalization; it was to prove that day-2 debugging remained possible once repeated requests accumulated over time.

## Intended soak shape
The soak was intentionally modest, not a load test:
- serialized rounds
- direct caller path plus real OpenCode caller path
- repeated plain non-tool requests
- repeated synthesis-style requests
- repeated noop-tool initial turns
- retrieval plus follow-up continuation where attemptable
- repeated OpenCode plain smokes
- repeated OpenCode tools-bearing smokes
- rejection probes bracketing the soak window

The intended gate was: if all of that remained clean, and the traces stayed readable and correlated, the lane would be strong enough to justify designing a promotion plan toward canonical `fast`.

## What was invalidated during execution
Two early soak attempts were invalidated by temporary harness issues rather than by lane policy behavior.

### Invalidated attempt 1
The first temp ingress forwarder was miswired so that `/v1/...` requests were forwarded to `/v1/v1/...`. That produced a `404` before LiteLLM policy logic was even reached.

Meaning:
- invalid for lane conclusions
- not evidence of lane regression
- temp harness bug only

### Invalidated attempt 2
After the first aborted run, the live guardrail trace no longer contained a clean starting `policy_summary` baseline. The temp runner then failed while trying to compute a start-of-window counter baseline from an empty or disturbed trace.

Meaning:
- invalid for lane conclusions
- again a harness-only issue

These were recovered by rerunning with a corrected harness and an explainability-first interpretation of counters rather than relying on a disturbed exact baseline.

## Recovery window used for findings
The authoritative recovered evidence came from:
- `/tmp/20260317T054747Z-gptoss20b-enforce-soak/`

This recovery window produced clean attributable evidence through:
- sanity reject probe
- sanity direct smoke
- Round 1:
  - direct plain
  - direct synthesis
  - direct noop initial turn
  - retrieval
  - follow-up continuation
  - OpenCode plain ingress
  - OpenCode tool ingress
- Round 2:
  - direct plain
  - direct synthesis
  - direct noop initial turn
  - retrieval
  - follow-up continuation
  - OpenCode plain ingress
- Round 3:
  - direct plain
  - direct synthesis
  - direct noop initial turn

The runner exited before it could write a final classification because Round 3 direct noop failed. A recovered closeout was then written manually into the same artifact root from the preserved evidence.

## Findings
### 1. Transport enforcement remained intact
This was the clearest positive result.

Across attributable backend traffic in the recovery window:
- backend path stayed `/v1/responses`
- `stream` remained `false`
- `temperature` remained `0.0`

The recovered summary recorded:
- `54` attributable backend Responses requests
- `0` attributable backend requests outside the constrained contract

This means the transport seam itself remained stable during the soak.

### 2. Observability remained usable
The guardrail trace and journald remained readable enough to support debugging.

Observed:
- `policy_decision`, `policy_result`, and `policy_summary` events continued to be emitted
- journald correlation remained usable
- no attributable passthrough behavior was observed

This is a meaningful operational improvement compared with earlier investigative phases where the strongest evidence depended more heavily on ad hoc capture and less on trustworthy self-trace.

### 3. Plain text and synthesis remained stable
The repeated direct plain non-tool requests and repeated direct synthesis requests stayed clean through the recovered window.

In practice:
- Round 1 direct plain passed
- Round 2 direct plain passed
- Round 3 direct plain passed
- Round 1 direct synthesis passed
- Round 2 direct synthesis passed
- Round 3 direct synthesis passed

There was no evidence in this pass that the guardrail broke ordinary non-tool Responses behavior.

### 4. The narrow tool path was not stable enough
This is the key negative finding.

Round 1 direct noop initial turn worked, and retrieval plus follow-up worked.

Round 2 direct noop initial turn worked, and retrieval plus follow-up worked.

Round 3 direct noop initial turn did not work. Instead, it returned:
- `status: "incomplete"`
- `incomplete_details.reason: "max_output_tokens"`
- no function call in the response output

That meant:
- the noop turn did not complete its intended tool call
- there was no valid `call_id` to continue with
- the Round 3 retrieval/follow-up path could not even be attempted

This failure mode matters because it is not a transport problem. The request reached the backend with the correct constrained transport. The failure was in the model/runtime behavior of the repeated narrow tool turn itself.

### 5. This repeated the practical risk already seen in the earlier soak
The earlier completed soak window had already ended with a similar practical conclusion: the experimental lane was useful, but repeated narrow tool behavior was not clean enough to justify promotion planning.

The recovered fresh window reproduced that same operational concern in a cleaner way:
- not as a one-off OpenCode artifact
- not as a trace artifact
- not as a transport drift
- but as repeated instability in the direct noop-tool path by the third round

That reproduction is what makes the promotion gate fail.

### 6. OpenCode remained noisy but not transport-drifty
The OpenCode one-shot runs still timed out at the process level in the soak harness.

That is important, but it should be interpreted carefully.

What the soak did show:
- OpenCode-originated ingress requests remained attributable
- they stayed Responses-native at the transport layer
- backend captures still showed `stream=false` and `temperature=0.0`

So the OpenCode issue in this soak is still primarily process/session noisiness, not evidence that the LiteLLM lane stopped enforcing the constrained contract.

## What this means
The experimental lane has now demonstrated two things at once:

First, the enforcement seam is real and stable enough to keep using experimentally.

Second, that is not the same thing as saying the lane is ready to be planned into canonical `fast`.

The promotion gate was supposed to require:
- stable plain behavior
- stable synthesis behavior
- stable repeated narrow tool behavior
- stable retrieval plus follow-up continuity
- readable observability
- no evidence of broad rewriting
- no unexplained operational drift over the soak window

This pass met most of that bar, but not all of it.

The missing piece is repeated narrow tool stability. Until that is understood and made boring, promotion planning would be premature.

## Final classification
Not ready for promotion planning.

More specifically:
- the lane remains operationally useful experimentally
- the transport enforcement policy remains good
- the observability model is usable
- but the repeated narrow tool path is not yet stable enough to justify designing a canonical-`fast` promotion plan

## Recommended next decision
Do not start the canonical-`fast` promotion-planning pass yet.

Instead, keep `metal-test-gptoss20b-enforce` as an experimental lane and run one narrow follow-up specifically on the repeated noop-tool instability:
- same experimental alias
- same constrained transport
- no new OpenCode configuration work
- no 120B drift work
- no broad promotion framing

The next question should be very small:

Why does the repeated direct noop-tool turn sometimes remain in reasoning until `max_output_tokens` and fail to emit the function call, even though the transport contract is preserved?

That is now the blocking question.

## Primary evidence
- Recovered soak classification:
  - [/tmp/20260317T054747Z-gptoss20b-enforce-soak/artifacts/classification.md](/tmp/20260317T054747Z-gptoss20b-enforce-soak/artifacts/classification.md)
- Recovered soak counter summary:
  - [/tmp/20260317T054747Z-gptoss20b-enforce-soak/artifacts/counter-summary.json](/tmp/20260317T054747Z-gptoss20b-enforce-soak/artifacts/counter-summary.json)
- Recovered soak runner log:
  - [/tmp/20260317T054747Z-gptoss20b-enforce-soak/artifacts/soak-runner.log](/tmp/20260317T054747Z-gptoss20b-enforce-soak/artifacts/soak-runner.log)
- Round 3 failing noop response:
  - [/tmp/20260317T054747Z-gptoss20b-enforce-soak/artifacts/R3-direct-noop.response.json](/tmp/20260317T054747Z-gptoss20b-enforce-soak/artifacts/R3-direct-noop.response.json)
- Earlier completed soak classification for comparison:
  - [/tmp/20260317T042134Z-gptoss20b-enforce-soak/artifacts/classification.md](/tmp/20260317T042134Z-gptoss20b-enforce-soak/artifacts/classification.md)

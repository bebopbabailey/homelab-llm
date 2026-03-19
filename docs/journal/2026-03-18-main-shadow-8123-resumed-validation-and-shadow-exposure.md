# 2026-03-18 — `main-shadow` `8123` resumed validation + operator-only exposure

## Summary
- Resumed the `main-shadow` rollout from the last proven direct-backend
  contract on Studio `8123`:
  - `--tool-call-parser hermes`
  - `--enable-auto-tool-choice`
  - no explicit structured-output backend
  - `--generation-config vllm`
  - `--max-model-len 32768`
  - `--no-async-scheduling`
  - `--no-enable-prefix-caching`
  - `VLLM_METAL_MEMORY_FRACTION=auto`
- Kept the known forced-tool defects as inherited, non-blocking limitations for
  this slice:
  - `tool_choice="required"` still broken from prior passes
  - explicit named forced-tool choice still broken from prior passes
- Finished the remaining direct-backend gates:
  - `tool_choice="auto"` full run: PASS (`10/10`)
  - long-context sanity: PASS (`3/3`)
  - bounded generic concurrency: PASS
  - shared-prefix branch-generation probe: PASS
- Exposed `main-shadow` through LiteLLM as an operator-only alias after
  restoring the full shadow env surface expected by the current router.
- Verified through LiteLLM:
  - `main-shadow` structured outputs: PASS
  - `main-shadow` `tool_choice="auto"`: PASS
  - `main`: unchanged
  - `boost`: unchanged
  - `code-reasoning`: unchanged

## Relationship to prior entries
This entry resumes and supersedes the stop condition recorded in:
- `docs/journal/2026-03-18-main-shadow-8123-final-no-forced-backend-retry-no-go.md`

That prior entry ended at the forced-tool failures. This entry records the
explicit decision to continue with the remaining validation phases and the
successful operator-only exposure outcome.

## Direct backend contract reused
- host: `192.168.1.72`
- port: `8123`
- label: `com.bebop.mlx-shadow.8123`
- runtime: `vllm-metal 0.1.0` / `vllm 0.14.1`
- model:
  `LibraxisAI/Qwen3-Next-80B-A3B-Instruct-MLX-MXFP4`
- served model:
  `mlx-qwen3-next-80b-mxfp4-a3b-instruct`
- flags:
  - `--max-model-len 32768`
  - `--generation-config vllm`
  - `--no-async-scheduling`
  - `--enable-auto-tool-choice`
  - `--tool-call-parser hermes`
  - `--no-enable-prefix-caching`

## Direct backend results
### Previously established, carried forward as known limitations
- `GET /v1/models`: PASS
- structured outputs gate: PASS (`5/5`)
- `tool_choice="required"`: FAIL (`0/5`)
- named forced-tool choice: FAIL (`0/5`)

These remain true for the current `vllm-metal` build and are not re-opened by
this entry.

### Resumed validation gates
#### `tool_choice="auto"`
- PASS (`10/10`)
- latency samples (s): `7.776, 0.395, 0.373, 0.377, 0.375, 0.373, 0.377, 0.377, 0.373, 0.375`
- no malformed payloads
- no `5xx`
- no timeouts

#### Long-context sanity
- PASS (`3/3`)
- representative latencies (s): `3.231, 2.306, 2.416`
- expected outputs preserved:
  - `context-ok-0`
  - `context-ok-1`
  - `context-ok-2`
- no listener loss
- no `5xx`
- no timeouts

#### Bounded generic concurrency
- PASS
- request shape:
  - history chars: `12000`
  - one-sentence output target
  - `max_tokens=768`
  - stream enabled for TTFT capture
- concurrency stages:
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
  - sibling suffix deltas: branch-style prompt variants
  - stream enabled for TTFT capture
- concurrency stages:
  - `c2`: `ttft_p95=2.667s`, `latency_p95=4.357s`
  - `c4`: `ttft_p95=5.319s`, `latency_p95=7.169s`
- zero crash
- zero listener loss
- zero `5xx`
- zero timeouts

## LiteLLM exposure notes
### Initial failure
The first Mini exposure attempt caused LiteLLM startup failures.

Root cause:
- the live `env.local` did not contain the full operator-only shadow env
  surface that the current `router.yaml` expects
- restarting LiteLLM against the newer router contract exposed that drift

Failure signature:
- LiteLLM startup raised:
  `TypeError: argument of type 'NoneType' is not iterable`
- the proxy only initialized the stable aliases (`main`, `code-reasoning`,
  `deep`, `fast`, `helper`) before failing

### Recovery
Recovered the gateway by restoring the full shadow env surface from
`config/env.example` into live `env.local`:
- `MAIN_SHADOW_*`
- `MAIN_FALLBACK_SHADOW_*`
- `HELPER_SHADOW_*`
- `LLMSTER_*`

After restart:
- LiteLLM readiness recovered
- `/v1/models` now includes:
  - `main-shadow`
  - `main-fallback-shadow`
  - `helper-shadow`
  - `fast-shadow`
  - `deep-shadow`

## LiteLLM validation results
- readiness: PASS
- authenticated `/v1/models`: PASS
- `main-shadow` structured outputs: PASS
- `main-shadow` `tool_choice="auto"`: PASS
- `main` canary request: PASS (`ok-main`)
- `boost` request: PASS (`ok-boost`)
- `code-reasoning` discovery in `/v1/model/info`: PASS

## Preservation checks
- `main` stayed on `8101`
- `boost*` behavior remained intact
- `code-reasoning` remained present for OpenHands discovery
- public defaults were not changed
- public `main` was not promoted

## Verdict
- `PASS and exposed`

More precisely:
- the resumed direct-backend validation passed
- the operator-only LiteLLM exposure succeeded
- public `main` remains unchanged
- forced-tool semantics remain a known limitation on the current `main-shadow`
  backend

## Next step
Decide whether canonical `main` promotion may tolerate the current forced-tool
limitation, or whether public `main` must still wait for a backend that passes:
- `tool_choice="required"`
- named forced-tool choice

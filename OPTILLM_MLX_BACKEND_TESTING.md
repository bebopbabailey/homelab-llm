# OPTILLM MLX Backend Testing Plan

## Purpose
Define a repeatable test and benchmark protocol for the isolated MLX-LM patch that enables OptiLLM-style decode-time techniques (`n/a on proxy` family), starting with `entropy_decoding`.

This plan is for the **experimental workspace only** and does not modify production services.

## Scope
- In scope:
  - Request-contract correctness (`optillm_approach`, `decoding`, `return_decoding_metadata`)
  - Decode-time behavior validation (entropy technique)
  - Non-streaming quality/latency benchmarking
  - Regression checks against baseline default decoding
- Out of scope (later milestone):
  - Streaming decode-time metadata
  - LiteLLM integration in production path
  - Full implementation of all other decode-time techniques

## Environments
- Primary: Studio isolated endpoint (loopback-only, dedicated port e.g. `127.0.0.1:8130`)
- Comparison targets:
  - `main` alias model (primary correctness bring-up)
  - `gpt-oss-20b` (compatibility pass)
  - `gpt-oss-120b` (final viability pass)

## Test Matrix
| Category | Mode | Model | Concurrency | Expected Outcome |
|---|---|---|---|---|
| Contract | default | main | 1 | 200, no `decoding_metadata` by default |
| Contract | entropy_decoding | main | 1 | 200, metadata present when requested |
| Behavior | default vs entropy | main | 1 | measurable entropy/temperature summary delta |
| Stability | entropy_decoding | main | 4, 8 | no crashes, clean partitioning by decoding signature |
| Compatibility | entropy_decoding | gpt-oss-20b | 1, 4 | feature still functions |
| Final viability | entropy_decoding | gpt-oss-120b | 1, 4 | acceptable overhead with measurable behavior |

## Acceptance Gates
- Gate A: API compatibility
  - OpenAI-ish response remains valid.
  - New fields are additive and opt-in only.
- Gate B: Functional entropy implementation
  - `decoding=entropy_decoding` changes decode behavior.
  - Metadata reports stable keys: `technique`, `steps`, entropy and temperature summary.
- Gate C: Baseline regression safety
  - `decoding` omitted behaves like default server path.
- Gate D: Performance viability
  - Overhead is quantified and judged acceptable for target workloads.

## Metrics to Collect
- Latency:
  - end-to-end response latency (p50/p95)
  - optional TTFT (if/when streaming milestone starts)
- Throughput:
  - requests/sec under fixed concurrency
  - completion tokens/sec
- Reliability:
  - HTTP error rate
  - timeout rate
- Decode metadata:
  - `entropy_mean`, `entropy_p95`, `entropy_max`
  - `temperature_min`, `temperature_max`
- Quality (task-specific):
  - pass@k or rubric score on fixed prompt set
  - deterministic checks on factual/control prompts

## Tooling and Assets
Use existing repo capabilities plus the new experimental harness:
- Existing stack:
  - Prometheus/Grafana dashboards for system-level context
  - LiteLLM-native test paths (for later integration stage)
- New experimental scripts:
  - `layer-inference/optillm-local/scripts/smoke_decode.py`
  - `layer-inference/optillm-local/scripts/bench_decode.py`
  - `layer-inference/optillm-local/scripts/run_benchmark_matrix.py` (batch matrix runner)
  - `layer-inference/optillm-local/scripts/run_viability_gate.py` (automated GO/NO-GO gate runner)
  - `layer-inference/optillm-local/scripts/run_viability_campaign.py` (repeat-run confidence runner)
- Gate contract template:
  - `layer-inference/optillm-local/config/optillm_mlx_viability_gate.example.json`
- Quality report template:
  - `layer-inference/optillm-local/config/optillm_mlx_quality_report.example.json`
- Campaign profile templates:
  - `layer-inference/optillm-local/config/viability_profiles/quick_screen.example.json`
  - `layer-inference/optillm-local/config/viability_profiles/decision_run.example.json`

## Test Procedure
1. Prepare patched workspace
```bash
bash layer-inference/optillm-local/scripts/bootstrap_mlx_optillm_workspace.sh \
  --workspace ~/optillm-mlx-experimental/mlx-lm-optillm
```

2. Launch isolated server (example)
```bash
cd ~/optillm-mlx-experimental/mlx-lm-optillm
python -m mlx_lm.server \
  --model <model-id-or-path> \
  --host 127.0.0.1 \
  --port 8130 \
  --enable-optillm-decoding
```

3. Contract smoke
```bash
uv run python layer-inference/optillm-local/scripts/smoke_decode.py \
  --url http://127.0.0.1:8130/v1/chat/completions \
  --model main \
  --expect-metadata
```

4. Benchmark run
```bash
uv run python layer-inference/optillm-local/scripts/bench_decode.py \
  --url http://127.0.0.1:8130/v1/chat/completions \
  --model main \
  --repeats 3 \
  --concurrency 4 \
  --json-out /tmp/optillm_mlx_bench_main.json
```

5. Repeat for compatibility/final viability models
- run same benchmark on `gpt-oss-20b`
- then run on `gpt-oss-120b`

6. Matrix benchmark run (recommended)
```bash
uv run python layer-inference/optillm-local/scripts/run_benchmark_matrix.py \
  --gate-config layer-inference/optillm-local/config/optillm_mlx_viability_gate.example.json
```

7. Automated viability decision (recommended)
```bash
uv run python layer-inference/optillm-local/scripts/run_viability_gate.py \
  --gate-config layer-inference/optillm-local/config/optillm_mlx_viability_gate.example.json \
  --quality-report /tmp/optillm_mlx_quality_report.json
```
Exit codes:
- `0`: `GO`
- `3`: `CONDITIONAL_GO`
- `2`: `UNVERIFIED`
- `1`: `NO_GO` (or hard execution failure)

Notes:
- If the endpoint is unreachable or no successful baseline/entropy responses are collected,
  the runner classifies that model as `UNVERIFIED` (not a functional failure).
- If `quality.required=true` in gate config and no quality report is supplied,
  final status remains `UNVERIFIED` by design.
- Performance gate now includes throughput delta (`entropy` vs `default`) and
  absolute mode error-rate limits in addition to latency overhead.

8. Campaign stability run (recommended before any GO decision)
```bash
uv run python layer-inference/optillm-local/scripts/run_viability_campaign.py \
  --gate-config layer-inference/optillm-local/config/viability_profiles/quick_screen.example.json \
  --runs 3
```
Then execute stricter decision profile:
```bash
uv run python layer-inference/optillm-local/scripts/run_viability_campaign.py \
  --gate-config layer-inference/optillm-local/config/viability_profiles/decision_run.example.json \
  --runs 3 \
  --quality-report /tmp/optillm_mlx_quality_report.json
```
Campaign outputs include per-run stdout/stderr logs and a
`campaign_summary.json` with `overall_decision`, decision stability, and
decision counts.

## Regression Checks
Run before and after patch refresh/rebase:
- Unit checks:
```bash
uv run python -m unittest layer-inference/optillm-local/tests/test_optillm_decoding.py
```
- Default-path sanity:
  - issue baseline request with no decode fields and compare behavior/latency trend.

## Reporting Template
For each benchmark run, capture:
- model + mode + concurrency
- sample size (requests)
- p50/p95 latency
- tokens/sec
- error rate
- metadata availability rate
- notes on anomalies

For the automated gate run, capture:
- `final_decision` (`GO`, `CONDITIONAL_GO`, `NO_GO`, `UNVERIFIED`)
- decision reasons
- per-model gate status
- path to `viability_report.json`

## Rollback and Safety
- Experimental workspace rollback:
  - delete or reset cloned workspace branch
  - stop isolated server process
- No production rollback required because production services are unchanged.

## Execution Status Snapshot (as of 2026-02-19)
- Historical viability outcomes observed in collected artifacts:
  - `UNVERIFIED` -> early bring-up and unreachable/smoke-unverified runs
  - `CONDITIONAL_GO` -> model gates passed but quality skipped
  - `GO` -> lighter profile with quality report passed
  - `NO_GO` -> stricter profile with quality and throughput failures
- Latest strict report in artifact set:
  - `/tmp/optillm_mlx_viability_20260219-000154/viability_report.json` -> `NO_GO`
- Latest campaign runner artifacts:
  - `/tmp/optillm_mlx_campaign_20260219-134725/campaign_summary.json`
  - `/tmp/optillm_mlx_campaign_20260219-134744/campaign_summary.json`
  - `/tmp/optillm_mlx_campaign_20260219-134848/campaign_summary.json`
  - each reported `UNVERIFIED` from current execution context
- Full chronological execution log:
  - `docs/journal/2026-02-19-optillm-mlx-viability-testing-log.md`

## 2026-02-21 campaign update
- Main-lane only (Qwen snapshot id), quick profile, 3-run campaign:
  - `/tmp/optillm_mlx_campaign_20260221-032317/campaign_summary.json`
  - stable `CONDITIONAL_GO` (`3/3`), driven by skipped quality + unverified maintainability
- Main-lane only (same model), quality-required + maintainability-enabled, 3-run campaign:
  - `/tmp/optillm_mlx_campaign_20260221-032530/campaign_summary.json`
  - stable `NO_GO` (`3/3`)
  - immediate blocker identified as maintainability drift:
    - `server.diff does not apply cleanly to upstream`
    - `patch failed: mlx_lm/server.py:758`
- Detailed run log:
  - `docs/journal/2026-02-21-optillm-mlx-main-campaign-validation.md`

## 2026-02-22 campaign update (after patch rebase)
- Rebased `server.diff` to current upstream `mlx-lm`:
  - `layer-inference/optillm-local/runtime/patches/mlx_lm/server.diff`
  - upstream `git apply --check` now passes
- Strict main-lane campaign rerun (quality required + maintainability enabled):
  - `/tmp/optillm_mlx_campaign_20260222-001410/campaign_summary.json`
  - stable `GO` (`3/3`)
  - maintainability status changed from fail to pass:
    - `server.diff applies cleanly to upstream`
- Detailed run log:
  - `docs/journal/2026-02-22-optillm-mlx-server-diff-rebase-and-go.md`

## Next Expansion (after entropy validation)
- Add one additional decode-time technique (e.g., `cot_decoding` or `deepconf`) behind same contract.
- Add streaming-safe metadata strategy.
- Add LiteLLM/OptiLLM pass-through integration only after isolated viability is proven.

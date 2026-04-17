# 2026-04-17 — SGLang native MLX evaluation plan (`worth a narrow lab evaluation now`)

## Objective

Decide whether SGLang's native MLX backend is mature enough, in April 2026, to
justify a narrow Mac Studio bake-off against the current homelab inference
stack. This is an evaluation decision only, not a migration plan.

## Current-state findings

### Verified

- The current public local trio is `main`, `fast`, and `deep`.
- The Mac Studio is the primary inference host.
- `main` is the only active public MLX lane and runs on Studio `8101`.
- `fast` and `deep` are no longer MLX team lanes; they run on shared
  `llmster` at `8126`.
- The accepted public `main` contract is narrow:
  - non-stream `tool_choice=auto`
  - long-context sanity
  - bounded concurrency
  - branch-style concurrency
- Structured outputs remain outside the accepted public `main` contract.
- `tool_choice="required"` and named forced-tool semantics remain unsupported
  and non-blocking on the current `main` runtime.
- Open WebUI remains LiteLLM-first; direct client-to-backend routing is not the
  supported client contract.
- The repo already has reusable benchmark and validation surfaces:
  - GPT acceptance harness: `services/llama-cpp-server/scripts/run_gpt_oss_acceptance.py`
  - stream TTFT probe: `services/optillm-proxy/scripts/bench_stream.py`
  - LiteLLM Prometheus metrics for latency, TTFT, and token throughput
  - lightweight MLX smoke gate: `platform/ops/scripts/mlx_quality_gate.py`
- Prior repo evidence on Apple-family serving already shows why concurrency
  should be treated skeptically:
  - heavy concurrent vLLM-metal decode failed on the experimental `8121` lane
  - disabling async scheduling stabilized that lane for the reproduced shape
  - earlier MLX viability work stayed at the conservative conclusion
    `not yet proven viable for promotion`
- Upstream SGLang merged native MLX backend support in PR `#20342` on
  `2026-03-26`.
- SGLang release `v0.5.10` on `2026-04-06` called out native MLX backend
  support for Apple Silicon; `v0.5.10.post1` followed on `2026-04-09`.
- Upstream Apple install guidance is still source-build oriented and states the
  Mac path is verified only with Python `3.11`.
- The narrow bake-off candidate can be pinned exactly to:
  - SGLang `v0.5.10.post1`
  - commit `94f03a39dbd39edfc2b118b5357bbbadaaa9ad28`
  - Python `3.11.13`
  - `mlx==0.31.1`
  - `mlx-lm==0.31.2`
  - `mlx-metal==0.31.1`
  Those versions match the currently open Apple crash report and avoid a
  moving-target candidate definition.
- Upstream Apple roadmap work remains open in April 2026 for:
  - radix cache
  - UMA memory management
  - overlap scheduling
  - custom Metal paged attention
  - FusedMoE
  - broader model support
  - broader profiling hooks
  - self-hosted macOS CI
  - accuracy-based correctness tests
- Apple-specific open issues materially weaken trust today:
  - memory management gap: issue `#21443`
  - overlap scheduling still open: issue `#22114`
  - Apple server crash still open on `0.5.10.post1`: issue `#22466`
- The claimed overlap-scheduling fix is still in open PR `#22416`, not merged.
- Apple exposes `MTLDevice.recommendedMaxWorkingSetSize`, so upstream memory
  budgeting gaps are not theoretical on a Mac Studio.

### Inferred

- The Apple path is real enough to test, but still too young to treat as a
  boring default.
- Tiny-model microbench wins do not establish readiness for the lab's accepted
  `main`, `fast`, or `deep` contracts.
- Any convincing evaluation should stay isolated from canonical ports and
  aliases until the direct backend path proves stable first.

## Fit against the current lab

### Where it could realistically help

- Serving performance: native MLX may improve direct decode efficiency relative
  to older Apple-serving paths.
- Concurrency and scheduler behavior: this is the most interesting upside area
  if SGLang MLX can reduce idle gaps without crashing.
- Observability and profiling: SGLang has official bench and profiling
  surfaces, and the lab already has Prometheus-backed latency metrics.
- Controlled direct-serving experiments: the Studio experimental port range
  (`8120-8139`) gives a low-risk place to run it without disturbing the live
  contract.

### Where it is likely weaker or riskier right now

- Long-context serving: less proven than the current accepted `main` posture.
- Shared-prefix and cache-heavy workloads: radix cache is still open upstream.
- Model coverage: upstream Apple roadmap still lists major model families as
  incomplete work.
- Operational simplicity: source build, Python `3.11` caveat, moving `mlx` /
  `mlx-lm` requirements, and missing macOS CI all add churn.
- Production trust: open Apple-specific crash and memory issues are directly in
  the path of the workloads that matter.

## Risk register

| Risk | Why it matters | Likelihood | Impact | Mitigation |
| --- | --- | --- | --- | --- |
| Apple scheduler immaturity | Open crash and open overlap work hit serving concurrency directly | High | High | Make conc=2 a hard early gate; stop on any crash, listener loss, or reproducible `5xx` |
| Apple memory budgeting gap | Metal working-set mistakes can stall badly or destabilize the host | Medium-High | High | Start with small models only; record memory pressure; stop on paging or severe stalls |
| Model support gap | Current lab lanes use model families not yet proven on Apple MLX | High | High | Start with upstream-documented Qwen small models and only add same-family lab models if already local |
| Benchmark instability | Offline or tiny-model wins can hide poor TTFT or unstable serving | High | Medium | Prioritize serving-path TTFT, p95 latency, and repeatability over microbench headlines |
| Operational churn | Candidate may consume time while adding no durable value to the stack | Medium | Medium-High | Keep the pass direct, isolated, and explicitly non-canonical |
| Integration overreach | LiteLLM/Open WebUI integration can make a weak backend look like a routing problem | Medium | Medium | Keep phase 1-3 direct-to-backend only; defer gateway/UI exposure |

## Evaluation scope

- Run only on Studio experimental ports in `8120-8139`.
- Keep the first bake-off direct-backend-only:
  - no LiteLLM
  - no Open WebUI
  - no alias exposure
- Use only existing local models:
  - primary model: `qwen3-4b-instruct-2507`
  - stretch model only if primary passes: `qwen3-next-80b-mxfp4-a3b-instruct`
  - optional candidate-only issue-alignment probe: `Qwen/Qwen2.5-0.5B-Instruct`
    only if it is already cached locally
- Explicitly out of scope:
  - any new model download
  - any canonical alias or UI path
  - GPT-OSS models
  - MoE models
  - branch-style `n=4` generation
- Fair-comparison rule:
  - compare direct backend to direct backend only
  - same host
  - same model artifact
  - same token manifest
  - same token limits
  - serialized run order with quiescence between major run blocks

### Pinned candidate environment

- SGLang tag: `v0.5.10.post1`
- SGLang commit: `94f03a39dbd39edfc2b118b5357bbbadaaa9ad28`
- Python: `3.11.13`
- `mlx`: `0.31.1`
- `mlx-lm`: `0.31.2`
- `mlx-metal`: `0.31.1`
- No candidate drift is allowed inside the first bake-off.
- The current local `vllm-metal` baseline is measured as-is and must have its
  exact runtime/version recorded at test time; it is not mutated to match the
  candidate.

### Token-count workload manifests

Replace all character-count workloads with fixed token manifests validated on
the exact model tokenizer before timed runs begin.

Manifest rules:
- one JSONL manifest per workload family under
  `/tmp/sglang-mlx-bakeoff-<run-id>/manifests/`
- each row must carry:
  - `case_id`
  - `prompt_text`
  - `prompt_sha256`
  - `input_token_count`
  - `max_output_tokens`
  - `stream`
  - `temperature`
- if token counts do not match exactly across baseline and candidate on the
  same model, the workload is invalid and must be regenerated

Required manifests:
- `M01_smoke_064in_128out.jsonl`
  - `10` rows
  - each prompt exactly `64` input tokens
  - `max_output_tokens=128`
- `M02_stream_256in_512out.jsonl`
  - `5` rows
  - each prompt exactly `256` input tokens
  - `max_output_tokens=512`
  - `stream=true`
- `M03_concurrency_256in_128out.jsonl`
  - `6` rows
  - each prompt exactly `256` input tokens
  - `max_output_tokens=128`
- `M04_longctx_4096in_256out.jsonl`
  - `3` rows
  - each prompt exactly `4096` input tokens
  - `max_output_tokens=256`
- `M05_sharedprefix_1024prefix_128suffix_256out.jsonl`
  - `3` rows
  - same `1024`-token prefix
  - unique `128`-token suffix per row
  - `max_output_tokens=256`
- optional candidate-only issue-alignment probe:
  - `M06_issue22466_046in507out__512in032out.jsonl`
  - row 1: `46` input tokens, `507` max output tokens
  - row 2: `512` input tokens, `32` max output tokens

## Benchmark matrix

| Area | Must measure now | Later if promising |
| --- | --- | --- |
| TTFT | `M02` direct HTTP p50/p95 only | gateway/UI-path TTFT |
| Decode throughput | `M01`, `M03`, `M04` output tokens/sec | larger mixed-batch studies |
| Concurrency behavior | `M03` success rate, `5xx` rate, p95 at conc=`2` and `4` | higher conc and mixed-length queue stress |
| Long-context behavior | `M04` at `4096 in / 256 out` | `16k+` and larger-context studies |
| Stability | repeated runs on `M01`-`M04` only | 24-48h operator-only soak |
| Shared-prefix behavior | `M05` diagnostic only unless cache behavior is directly comparable | deeper cache-focused studies |
| Memory behavior | memory pressure, swap, and failure-trace capture at fixed points | larger-artifact headroom studies |
| Operational ergonomics | build friction, version pinning, metrics/log quality | shadow aliasing and dashboards |

### Required promotion scenarios

- `M01` short non-stream smoke
  - `10` runs
  - gate: `0` crashes, `0` listener loss, `0` `5xx`
- `M02` streaming TTFT
  - `5` runs
  - gate: valid TTFT on every run
- `M03` concurrency short-chat
  - conc=`2`, then conc=`4`
  - `6` requests per stage
  - gate: no crash, no listener loss, success rate `>=95%`
- `M04` long-context sanity
  - conc=`1`, then conc=`2`
  - `3` repeats
  - gate: no crash, no listener loss, success rate `>=95%`

### Diagnostic-only scenarios

- `M05` shared-prefix serving
  - diagnostic unless cache behavior is directly comparable on both sides
- simple auto-tool noop and single-arg cases
  - diagnostic only
- `M06` upstream crash-alignment probe
  - candidate only
  - diagnostic only

## Phased execution plan

### Phase 0: evidence review and prerequisites

Goal:
- lock scope so the work cannot turn into migration by momentum

Concrete tasks:
- validate exact candidate versions
- validate exact test models and token manifests
- confirm experimental-port-only posture
- confirm no model download is needed for phase 1
- confirm timed runs will be serialized on one host

Telemetry captures required at:
- `T0` before each server launch
- `T1` after warm-up and before measured runs
- `T2` after each measured workload block
- `T3` after `5` minutes of post-block quiescence

Required Studio host telemetry commands:
- `ssh studio 'memory_pressure -Q'`
- `ssh studio 'vm_stat'`
- `ssh studio 'sysctl vm.swapusage'`
- `ssh studio 'top -l 1 -stats pid,command,mem,cpu,vsize'`

Deliverables:
- source ledger
- workload manifest
- metric list
- stop/go thresholds

Exit criteria:
- sources pinned
- isolated Studio scope confirmed
- first-pass model set available or explicitly deferred

Failure criteria:
- required artifacts are absent and would force a new download
- comparison cannot be made fairly

### Phase 1: minimal local bring-up

Goal:
- establish the boring same-model direct baseline first

Concrete tasks:
- bring up the current local `vllm-metal` baseline on `8121` with
  `qwen3-4b-instruct-2507`
- verify `/v1/models`
- run `M01`, `M02`, `M03`, `M04`
- run `M05` only as diagnostic

Deliverables:
- baseline version/provenance capture
- baseline workload results
- baseline telemetry bundle

Exit criteria:
- same-model direct baseline exists and is clean
- required baseline workloads complete without crash

Failure criteria:
- same-model baseline cannot be established
- baseline requires new model work or download

### Phase 2: controlled profiling

Goal:
- bring up and test the pinned SGLang MLX candidate against the same manifests

Concrete tasks:
- bring up SGLang MLX on `8120` with the same `qwen3-4b` artifact
- verify `/v1/models`
- run `M01`, `M02`, `M03`, `M04`
- run `M05` only as diagnostic
- optionally run `M06` only if `Qwen/Qwen2.5-0.5B-Instruct` is already cached
- capture candidate telemetry and host state at `T0`-`T3`

Deliverables:
- candidate result set
- crash/no-crash table
- TTFT and throughput tables
- telemetry bundle

Exit criteria:
- no crash on required shapes
- no memory-pressure warning signs
- repeatability inside the `15%` band

Failure criteria:
- any reproducible crash at `num-prompts=2` or equivalent conc=`2` serving
  shape
- visible paging or severe instability

### Phase 3: apples-to-apples benchmark comparison

Goal:
- compare the pinned candidate to the established same-model direct baseline

Concrete tasks:
- compare baseline vs candidate on `M01`-`M04`
- keep `M05` separate as diagnostic-only unless direct cache comparability is
  proven
- rerun baseline `M01` and `M02` subset at the end to detect session drift
- report TTFT, p95 latency, output throughput, success rate, memory pressure,
  swap, and failure traces

Deliverables:
- one side-by-side comparison table
- one short verdict on whether the candidate earns more time

Exit criteria:
- crash-free direct comparison
- same-model comparison stays fair
- candidate is at least competitive or clearly better in one high-value area
  without losing on stability

Failure criteria:
- unstable results
- missing model support
- materially worse TTFT or tail latency
- weakened comparison needed to make the candidate look good

### Phase 4: operational trial

Goal:
- stretch relevance check only if the primary conservative bar is met

Concrete tasks:
- load `qwen3-next-80b-mxfp4-a3b-instruct` on `8122`
- run only:
  - `/v1/models`
  - `M01`
  - `M02`
  - `M03` at conc=`2` only
  - `M04` at conc=`1` then conc=`2`
- keep `M05` diagnostic only
- keep the pass direct-backend-only and non-canonical

Deliverables:
- short stretch report covering crashes, restart cleanliness, memory, swap, and
  relevance to current `main`

Exit criteria:
- stretch model loads from existing local artifacts
- stretch smoke and required short/concurrency/long-context checks run without
  crash

Failure criteria:
- restarts
- listener loss
- hidden feature gaps
- repeated operator intervention

## Stop/go gates

### Stop immediately

- any crash, listener loss, or reproducible `5xx` under light concurrency
- any clear memory-pressure, paging, or host-instability symptom
- repeatability worse than the `15%` band on fixed shapes
- benchmark gains that appear only in microbench while serving-path TTFT or
  stability regress
- inability to establish a same-model direct baseline without new downloads or
  extra model work

### Continue cautiously

- bring-up is clean
- same-model direct comparison is stable
- remaining uncertainty is mostly model breadth or stretch relevance

Operating posture:
- keep it Studio-local
- keep it non-canonical
- do not expose it through LiteLLM or Open WebUI

### Promote to deeper trial

- phase 3 comparison is fair and crash-free
- TTFT and output throughput are competitive
- no custom patching or special babysitting is required
- the candidate offers a credible upside without weakening current lab safety
- shared-prefix behavior is not required for promotion unless cache semantics
  were shown to be directly comparable
- branch-style `n=4` behavior is intentionally excluded from this narrow
  bake-off

## Recommendation

Recommendation: `worth a narrow lab evaluation now`

Plain-English defense:
- Native MLX support is now real and shipped upstream, so a bake-off is no
  longer speculative.
- It is still too early for serious adoption planning because the Apple path
  remains source-build-heavy, Python `3.11`-specific in upstream guidance, and
  carries open Apple-specific memory, scheduling, and crash risks.
- The right move is a narrow, direct, Studio-local bake-off with pinned
  versions, fixed token manifests, telemetry capture, and hard stop criteria,
  not a migration slice and not a challenge to the current
  `main` / `fast` / `deep` contract.

## Appendix: source ledger

### Current-state sources

- `docs/PLATFORM_DOSSIER.md`
- `docs/foundation/topology.md`
- `docs/foundation/mlx-registry.md`
- `docs/foundation/runtime-lock.md`
- `platform/ops/runtime-lock.json`
- `services/litellm-orch/SERVICE_SPEC.md`
- `services/open-webui/SERVICE_SPEC.md`
- `services/llama-cpp-server/SERVICE_SPEC.md`
- `platform/registry/models.jsonl`
- `platform/registry/handles.jsonl`

### Benchmark sources

- `docs/INTEGRATIONS.md`
- `docs/foundation/testing.md`
- `services/llama-cpp-server/scripts/run_gpt_oss_acceptance.py`
- `services/optillm-proxy/scripts/bench_stream.py`
- `platform/ops/scripts/mlx_quality_gate.py`
- SGLang `bench_serving` documentation:
  `https://docs.sglang.io/developer_guide/bench_serving.html`
- SGLang observability documentation:
  `https://docs.sglang.io/advanced_features/observability.html`

### Risk sources

- `docs/journal/2026-02-25-vllm-metal-8121-failure-forensics.md`
- `docs/journal/2026-02-25-vllm-metal-8121-async-scheduler-root-cause.md`
- `docs/journal/2026-02-19-optillm-mlx-viability-testing-log.md`
- `docs/journal/2026-03-18-main-closeout-and-gpt-transition.md`
- SGLang releases page:
  `https://github.com/sgl-project/sglang/releases`
- SGLang issue `#19137` Apple roadmap:
  `https://github.com/sgl-project/sglang/issues/19137`
- SGLang issue `#21443` Apple memory management:
  `https://github.com/sgl-project/sglang/issues/21443`
- SGLang issue `#22114` overlap scheduling:
  `https://github.com/sgl-project/sglang/issues/22114`
- SGLang issue `#22466` Apple server crash:
  `https://github.com/sgl-project/sglang/issues/22466`
- SGLang PR `#20342` native MLX backend:
  `https://github.com/sgl-project/sglang/pull/20342`
- SGLang PR `#21509` radix cache:
  `https://github.com/sgl-project/sglang/pull/21509`
- SGLang PR `#21770` Apple correctness tests:
  `https://github.com/sgl-project/sglang/pull/21770`
- SGLang PR `#22162` Apple dependencies:
  `https://github.com/sgl-project/sglang/pull/22162`
- SGLang PR `#22416` overlap-scheduling / crash fix candidate:
  `https://github.com/sgl-project/sglang/pull/22416`
- SGLang docs home:
  `https://docs.sglang.io/`
- SGLang install guide:
  `https://docs.sglang.io/get_started/install.html`
- Apple `MTLDevice.recommendedMaxWorkingSetSize`:
  `https://developer.apple.com/documentation/metal/mtldevice/recommendedmaxworkingsetsize`

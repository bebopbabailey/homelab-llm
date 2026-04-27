# 2026-04-27 — omlx-runtime phase 3 live validation

## Summary

Validated the phase-2 `omlx-runtime` adapter against a real Studio-local oMLX
listener and a real Mini-owned SSH-forwarded endpoint, then cleaned the runtime
back down to no active listener and no active forward.

Result: **the adapter is good enough to serve as the stable portal for a future
orchestration prototype**, with one important caveat. The live parity timings
were dominated by cache warmth and call order, not by adapter overhead alone.
What phase 3 proves cleanly is:

- the adapter preserves the frozen non-stream `/v1/chat/completions` contract
- the adapter rejects out-of-scope requests locally
- the adapter survives a 45-minute `S02`/`S04` soak with zero failures
- the adapter survives a real Studio restart-restore cycle
- late direct control requests still succeed, so no silent runtime drift was
  introduced by the adapter exercise

It does **not** prove a perfect apples-to-apples latency delta between raw HTTP
and adapter calls, because direct and adapter blocks were run sequentially
against a cache-sensitive runtime on the same forwarded path.

## Runtime shape

- Worktree: `/home/christopherbailey/homelab-llm-omlx-runtime-phase3-validation-20260427`
- Artifacts dir: `/tmp/omlx-runtime-phase3-20260427T035217Z`
- Studio listener: `127.0.0.1:8120`
- Mini forwarded endpoint: `127.0.0.1:8129 -> Studio 127.0.0.1:8120`
- Listener runtime: `/opt/homebrew/bin/omlx`
- Model: `/Users/thestudio/models/omlx-eval/mlx-community/Qwen3-4B-Instruct-2507-4bit`
- Served model id: `Qwen3-4B-Instruct-2507-4bit`
- API key mode: fixed eval key (`eval-key`)
- Cache posture:
  - `--paged-ssd-cache-dir /Users/thestudio/.omlx/cache/shadow`
  - `--paged-ssd-cache-max-size 64GB`
  - `--hot-cache-max-size 8GB`
- Listener cleanup state:
  - Mini `8129` clear after cleanup
  - Studio `8120` clear after cleanup

Listener command:

```bash
omlx serve \
  --model-dir /Users/thestudio/models/omlx-eval \
  --base-path /Users/thestudio/.omlx \
  --host 127.0.0.1 \
  --port 8120 \
  --api-key eval-key \
  --max-process-memory 75% \
  --max-concurrent-requests 4 \
  --paged-ssd-cache-dir /Users/thestudio/.omlx/cache/shadow \
  --paged-ssd-cache-max-size 64GB \
  --hot-cache-max-size 8GB
```

Forwarded endpoint command:

```bash
ssh -o ExitOnForwardFailure=yes -f -N \
  -L 127.0.0.1:8129:127.0.0.1:8120 studio
```

## Frozen contract and fixtures

- Primary contract:
  - `POST /v1/chat/completions`
  - bearer auth
  - `model`, `messages`, `temperature=0`, `top_p=1`, `max_tokens`,
    `stream=false`
  - exactly two messages: `system`, then `user`
  - plain string `content` only
- Out-of-scope requests rejected locally:
  - `stream=true`
  - `tools`
  - `tool_choice`
  - structured outputs / `response_format`
  - content arrays
  - responses-style `input`
- Fixture manifest:
  - repo spec: `services/omlx-runtime/fixtures/phase3_fixture_specs.json`
  - manifest hash:
    `b36474669e84acd2c53a860b16393da0e4b3c2b21022f99f805d527ab7000acf`
- Important caveat:
  - phase 3 used a deterministic pseudo-repository repeated-prefix fixture
    family derived from the validated `G01/G02/S01-S04` workload classes
  - it did not recover the exact historical `manifests.json` from the April 21
    isolated Studio runs

## Results

### Negative contract block

- `6/6` out-of-scope request families were rejected locally
- no transport or upstream traffic was required to reject them

### Liveness checkpoints

- All required liveness probes passed
- Forwarded-endpoint model surface consistently reported:
  - `Qwen3-4B-Instruct-2507-4bit`

Observed liveness latencies:
- pre-first-pass: `0.010s`
- pre-full-pass: `0.047s`
- pre-soak: succeeded
- pre-restart block: succeeded
- post-restart: succeeded

### First-pass parity

All eight block summaries succeeded:
- direct `G01`, `G02`, `S02`, `S04`
- adapter `G01`, `G02`, `S02`, `S04`

Observed block p50s:

| Fixture | Direct p50 | Adapter p50 |
| --- | ---: | ---: |
| `G01` | `1.686s` | `0.666s` |
| `G02` | `1.922s` | `0.829s` |
| `S02` | `4.635s` | `1.788s` |
| `S04` | `5.293s` | `1.705s` |

Interpretation:
- the adapter did not introduce failures or shape drift
- these timing deltas are **not** a clean adapter-overhead measurement because
  the direct requests were issued first and the adapter then benefited from the
  warmed runtime state on the same forwarded path

### Full parity

All four block summaries succeeded:
- direct `S01`, `S03`
- adapter `S01`, `S03`

Observed block p50s:

| Fixture | Direct p50 | Adapter p50 |
| --- | ---: | ---: |
| `S01` | `1.090s` | `1.017s` |
| `S03` | `0.957s` | `0.960s` |

Interpretation:
- no shape drift
- no adapter-only failure mode
- warm-state ordering still applies, but here the difference is small

### Adapter soak

- Duration: `45` minutes
- Fixture mix:
  - `80%` `S02`
  - `20%` `S04`
- Total blocks: `1,438`
- Total measured requests: `2,876`
- Failed blocks: `0`
- Request failures: `0`
- Adapter parse failures: `0`
- Upstream `5xx`: `0`
- SSH transport failures: `0`

Soak p50 ranges:

| Fixture | Blocks | p50 min | p50 median | p50 max |
| --- | ---: | ---: | ---: | ---: |
| `S02` | `1,151` | `1.745s` | `1.807s` | `1.935s` |
| `S04` | `287` | `1.708s` | `1.756s` | `1.883s` |

Interpretation:
- no throughput degradation or queue-growth signature appeared in the adapter
  path
- the forwarded endpoint remained stable for the entire soak

### Restart-restore

The Studio listener was stopped and restarted with the same private localhost
config. The first post-restart liveness request triggered a normal model reload
and SSD cache scan, then the adapter checks passed:

| Fixture | Adapter post-restart p50 |
| --- | ---: |
| `G01` | `1.633s` |
| `S02` | `1.966s` |
| `S04` | `1.842s` |

No adapter code changes, request-shape changes, or transport recovery tricks
were needed beyond the normal listener restart.

### Post-soak direct control rerun

Late direct reruns also succeeded:

| Fixture | Direct rerun p50 |
| --- | ---: |
| `G01` | `0.669s` |
| `S02` | `1.804s` |

Interpretation:
- the runtime itself remained healthy after the full adapter exercise
- any future late anomaly should be investigated as adapter or transport
  behavior first, not assumed to be silent oMLX runtime drift

## Artifacts

This journal is the durable repo record. Supporting local evidence was left in:

- `/tmp/omlx-runtime-phase3-20260427T035217Z/negative/negative_contract.jsonl`
- `/tmp/omlx-runtime-phase3-20260427T035217Z/liveness-*/liveness.jsonl`
- `/tmp/omlx-runtime-phase3-20260427T035217Z/first-pass/summary.jsonl`
- `/tmp/omlx-runtime-phase3-20260427T035217Z/full-pass/summary.jsonl`
- `/tmp/omlx-runtime-phase3-20260427T035217Z/soak/{summary.jsonl,requests.jsonl}`
- `/tmp/omlx-runtime-phase3-20260427T035217Z/post-restart/summary.jsonl`
- `/tmp/omlx-runtime-phase3-20260427T035217Z/direct-control/summary.jsonl`
- `/tmp/omlx-runtime-phase3-20260427T035217Z/ssh-tunnel.stderr.log`
- Studio listener logs:
  - `/tmp/omlx-runtime-phase3-20260427T035217Z/omlx.stderr.log`
  - `/tmp/omlx-runtime-phase3-20260427T035217Z/omlx-restart.stderr.log`

## Cleanup

- Studio listener `8120`: stopped and verified clear
- Mini forwarded endpoint `8129`: stopped and verified clear
- No LiteLLM, Open WebUI, public routing, or launchd changes were made

## Recommendation

Treat the current `omlx-runtime` client as a **stable specialized-runtime
portal** for a future orchestration-plane prototype.

What phase 3 justifies:
- use the current adapter as the first Mini-side ingress for private oMLX
  runtime experiments
- keep the contract narrow and non-stream
- keep transport externally managed and observable

What phase 3 does **not** justify:
- public routing
- LiteLLM aliasing
- Open WebUI exposure
- broad OpenAI compatibility claims

The next step, if desired, should be a small orchestration-plane prototype that
consumes this adapter as-is rather than trying to widen the runtime contract.

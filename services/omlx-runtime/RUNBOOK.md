# Runbook: omlx-runtime

## Phase 2 posture
- The first ingress is a thin repo-owned library/client.
- No repo-managed shared service, launchd label, or public route is approved in
  this phase.

## Operator intent
- Use this service bundle as the contract source for the first private ingress.
- Keep direct runtime experiments separate from commodity gateway work.

## Ingress precondition
- The adapter does not own SSH tunnel lifecycle.
- Before calling the client, establish a Mini-local forwarded endpoint to the
  Studio localhost oMLX listener.
- This keeps tunnel/setup failures separate from adapter request failures and
  preserves clean fault attribution.

## Primary contract checks
- primary callable surface: non-stream `POST /v1/chat/completions`
- exact frozen fixtures: smoke, 4k guardrail, `S01`, `S02`, `S03`, `S04`
- direct parity target:
  - no request-shape rewriting
  - no adapter-only `5xx`
  - bounded latency overhead vs direct path

## Local verification
```bash
uv run --project services/omlx-runtime python -m unittest discover -s services/omlx-runtime/tests -p 'test_*.py'
```

## Phase 3 live validation
- Run phase 3 only from the linked `omlx-runtime` validation lane, not from
  `master`.
- Keep the Studio listener localhost-only and reach it through a
  pre-established Mini-local forwarded endpoint.
- Recommended runtime shape:
  - Studio listener: `127.0.0.1:8120`
  - Mini forwarded endpoint: `127.0.0.1:8129 -> Studio 127.0.0.1:8120`
- Primary script:

```bash
uv run --project services/omlx-runtime \
  python services/omlx-runtime/scripts/phase3_live_validate.py \
  --mode first-pass \
  --base-url http://127.0.0.1:8129 \
  --bearer-token eval-key \
  --model Qwen3-4B-Instruct-2507-4bit \
  --artifacts-dir /tmp/omlx-runtime-phase3/first-pass
```

- Required stage order:
  - `negative-contract`
  - forwarded-endpoint liveness probe
  - `first-pass`
  - forwarded-endpoint liveness probe
  - `full-pass`
  - forwarded-endpoint liveness probe
  - `soak`
  - restart listener / re-establish forward if needed
  - forwarded-endpoint liveness probe
  - `post-restart`
  - `direct-control`

## Artifact expectations
- adapter per-request JSONL ledger
- adapter stdout/stderr log
- raw upstream body capture on parse or HTTP failure
- tunnel lifecycle logs collected outside the adapter
- Studio oMLX logs kept separate from adapter logs
- forwarded-endpoint liveness results before each major validation stage

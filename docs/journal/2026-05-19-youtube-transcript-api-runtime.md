# YouTube Transcript API Runtime Smoke

Date: 2026-05-19

## Objective

Validate the new `youtube-transcript-api` primitive as a localhost-only OpenAI-compatible backend before closeout to `master`.

## Runtime Shape

- Worktree: `/home/christopherbailey/homelab-llm-youtube-transcript-api`
- Service command: `uv run youtube-transcript-api --host 127.0.0.1 --port 8014`
- Bind: `127.0.0.1:8014`
- No systemd install, no live LiteLLM restart, and no LAN exposure were used.

## Checks

- `GET /health` returned `{"status":"ok"}`.
- `GET /v1/models` returned the `youtube-transcript` model.
- `POST /v1/chat/completions` with one YouTube watch URL returned HTTP 200, plain timestamped transcript text in `choices[0].message.content`, and the canonical `transcript` object with `source_id`, canonical URL, caption metadata, segments, and content hash.

## Decision

The direct service smoke passed. Pre-merge validation is sufficient for the service itself; LiteLLM end-to-end validation should happen after merge and deployment of the new service unit/env on Mini.

## Cleanup

The dev server was stopped with Ctrl-C. `ss -ltn 'sport = :8014'` showed no listener after shutdown.

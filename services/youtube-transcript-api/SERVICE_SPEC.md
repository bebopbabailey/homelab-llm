# Service Spec: youtube-transcript-api

## Purpose
Localhost-only OpenAI-compatible service on the Mini for deterministic YouTube
timed-text acquisition. It is the canonical source of truth for YouTube
transcript retrieval.

## Host & Runtime
- Host: Mini
- Runtime: Python/FastAPI under systemd
- Bind: `127.0.0.1:8014`
- Public access path: LiteLLM alias `task-youtube-transcript`

## Endpoints
- `GET /health`
- `GET /v1/models`
- `POST /v1/chat/completions`

## Chat Contract
Input:
- latest user message contains exactly one supported YouTube URL

Supported URL forms:
- `https://www.youtube.com/watch?v=...`
- `https://youtu.be/...`
- `https://www.youtube.com/shorts/...`
- `https://www.youtube.com/live/...`

Output:
- `choices[0].message.content` is plain timestamped transcript text
- response also includes a `transcript` object for internal callers with:
  - `source_type`
  - `source_id`
  - `canonical_url`
  - `language`
  - `language_code`
  - `caption_type`
  - `transcript_text`
  - `content_hash`
  - `segments[]`

## Behavior
- Prefer the first manually created caption track YouTube exposes.
- Otherwise use the first generated caption track.
- Preserve source caption language.
- Apply only light whitespace/noise normalization.
- Return the full available transcript.

## Error Contract
OpenAI-style JSON errors:
- `invalid_request` -> 400
- `invalid_url` -> 400
- `unsupported_url` -> 400
- `no_transcript` -> 404
- `upstream_failure` -> 502
- `unsupported_request` -> 400

# `task-youtube-summary`

This document covers both:
- how to use the YouTube summary lane as a caller
- how the stack works as an operator

## What It Is

`task-youtube-summary` is a LiteLLM task alias that turns a supported YouTube
video URL into:
- a comprehensive first-turn summary
- a follow-up chat surface over the same video

It is designed for two main client styles:
- direct API callers such as iOS Shortcuts
- chat-style clients such as Open WebUI

The lane is backed by a two-step architecture:
- `media-fetch-mcp` on Mini for deterministic transcript acquisition
- `vector-db` on Studio for durable retrieval over long transcripts

## User Guide

### Supported inputs

The first turn must include one supported single-video YouTube URL:
- `https://www.youtube.com/watch?v=...`
- `https://youtu.be/...`
- `https://www.youtube.com/shorts/...`
- `https://www.youtube.com/live/...`

You may optionally add a short focus request on the same turn, for example:

```text
https://youtu.be/-QFHIoCo-Ko focus on the engineering workflow and examples
```

Playlist-only, channel, search, and other non-single-video pages are rejected.

### What the first response looks like

The lane returns readable markdown. The first line includes durable metadata:

```text
Video: <video_id> | Document: youtube:<video_id> | Transcript: <language> | Captions: <caption_type>
```

That `Document: youtube:<video_id>` handle matters. It is the durable identity
for the indexed transcript and can be reused conceptually as the document
handle for follow-up retrieval.

### Direct API usage

Canonical endpoint:
- `POST /v1/responses`

Initial request shape:

```json
{
  "model": "task-youtube-summary",
  "input": [
    {
      "role": "user",
      "content": "https://youtu.be/-QFHIoCo-Ko focus on the main workflow"
    }
  ],
  "max_output_tokens": 2048
}
```

Follow-up request shape:

```json
{
  "model": "task-youtube-summary",
  "previous_response_id": "<prior response id>",
  "input": [
    {
      "role": "user",
      "content": "What was the core workflow?"
    }
  ],
  "max_output_tokens": 1024
}
```

Ergonomic handles:
- `model = task-youtube-summary`
- `previous_response_id` for direct follow-up chaining
- visible document handle `youtube:<video_id>`

Important detail:
- `previous_response_id` is an ergonomic handle only
- the real continuity comes from `response_id -> document_id` resolution in the
  retrieval layer, not from provider-side conversation state

### iOS Shortcuts usage

Recommended shape:
- `Get Contents of URL`
- endpoint: `http://<mini>:4000/v1/responses`
- method: `POST`
- headers:
  - `Authorization: Bearer <your LiteLLM key>`
  - `Content-Type: application/json`
- body:

```json
{
  "model": "task-youtube-summary",
  "input": [
    {
      "role": "user",
      "content": "https://youtu.be/-QFHIoCo-Ko"
    }
  ],
  "max_output_tokens": 2048
}
```

Notes:
- JSON-escaped slashes like `https:\/\/youtu.be\/...` are fine
- store the returned `id` if you want follow-up requests through
  `previous_response_id`

### Open WebUI usage

Recommended shape:
- create a dedicated model or preset that points at `task-youtube-summary`
- start a fresh chat
- paste only the YouTube URL on turn 1
- ask normal follow-up questions on later turns

Current behavior:
- first turn returns the summary
- later turns do not require repeating the URL
- the lane attempts to recover document context from:
  - `previous_response_id`
  - explicit `document_id`
  - prior assistant metadata line
  - prior URL in chat history

If no prior context can be recovered, it fails clearly instead of guessing.

### Language behavior

Transcript acquisition stays source-faithful:
- the transcript service preserves the source caption language

Caller-facing summary behavior stays English-first:
- `task-youtube-summary` produces English summaries and answers by default
- translation is treated as summarization behavior, not transcript acquisition

### Error behavior

Typical outcomes:
- bad or unsupported URL -> `400`
- no usable transcript -> `404`
- transcript service or upstream failure -> `502` or `503`

## Operator Guide

### Stack and responsibilities

#### 1. `media-fetch-mcp`

Location:
- `services/media-fetch-mcp`

Runtime:
- Mini
- localhost-only
- `http://127.0.0.1:8012/mcp`

Responsibility:
- deterministic YouTube transcript acquisition only

Tool:
- `youtube.transcript`

Current output contract:
- `video_id`
- `source_url`
- `language`
- `language_code`
- `caption_type`
- `transcript_text`
- `segments[]`
  - `text`
  - `start`
  - `duration`
  - `timestamp_label`

Non-goals:
- no summarization
- no translation
- no chunking for storage
- no vector indexing

#### 2. `litellm-orch`

Location:
- `services/litellm-orch`

Runtime:
- Mini
- public API gateway
- `http://127.0.0.1:4000/v1`

Responsibility:
- expose `task-youtube-summary`
- parse the initial request
- call `media-fetch-mcp`
- choose short vs long path
- write transcript documents into retrieval when needed
- handle follow-up routing

The lane is intentionally narrow. It is not a general MCP orchestrator.

#### 3. `vector-db`

Location:
- `services/vector-db`

Runtime:
- Studio
- memory API on `192.168.1.72:55440`
- Elasticsearch-backed retrieval store

Responsibility:
- store long-form transcript chunks
- store embeddings and metadata
- store timestamp spans
- resolve `response_id -> document_id`
- perform document-scoped retrieval for follow-up questions

This substrate is not YouTube-specific. It is the same retrieval backbone for
other long-form document-style pipelines.

### End-to-end flow

For the first turn:

```text
YouTube URL
-> task-youtube-summary
-> media-fetch-mcp youtube.transcript
-> structured transcript payload
-> direct summary if short
-> or chunk/index into vector-db if long
-> final summary response
-> response_id -> document_id mapping write
```

For follow-up turns:

```text
previous_response_id or chat history
-> document_id recovery
-> vector-db document-scoped retrieval
-> transcript excerpts
-> answer synthesis grounded in retrieved chunks
```

### Short vs long transcript behavior

Short transcript path:
- summarize directly from transcript data
- return markdown summary
- write response-map entry for follow-up continuity

Long transcript path:
- chunk transcript using structured `segments[]`
- upsert transcript document into `vector-db`
- summarize with the long-content path
- follow-ups are retrieval-backed against the indexed document

### Follow-up context recovery

#### Responses path

Preferred path:
- caller sends `previous_response_id`
- lane resolves that to `document_id`
- retrieval is scoped to that document

#### Chat-completions path

Recovery order:
1. `previous_response_id`
2. explicit `document_id` in prompt/history
3. `Document: youtube:<id>` in prior assistant summary
4. original URL in prior chat history
5. otherwise fail clearly

### Important knobs and handles

#### Caller-facing handles
- model alias: `task-youtube-summary`
- response chaining handle: `previous_response_id`
- visible document handle: `youtube:<video_id>`

#### Service endpoints
- LiteLLM: `127.0.0.1:4000/v1`
- transcript MCP: `127.0.0.1:8012/mcp`
- memory API: `192.168.1.72:55440`

#### Retrieval behavior

The retrieval substrate supports internal profiles:
- `precise`
- `balanced`
- `broad`

The YouTube lane currently uses those internally rather than exposing them as a
public user knob.

#### Auth-sensitive pieces
- LiteLLM key for public client access
- `MEMORY_API_BEARER_TOKEN` in Mini `litellm-orch` runtime for write-side
  transcript upserts and response-map writes

### Where this is reused elsewhere

The current design generalizes beyond YouTube:
- the transcript/document retrieval substrate in `vector-db` is shared
  infrastructure for long-form content
- the `response_id -> document_id` durability model is reusable for other
  “summarize first, chat later” pipelines
- `media-fetch-mcp` establishes the pattern of keeping acquisition separate
  from reasoning

The broader architecture is:

```text
source acquisition service
-> normalized spans/segments
-> retrieval/indexing layer
-> summary lane
-> durable follow-up chat over the indexed document
```

That same shape is meant to work for:
- YouTube transcripts
- PDFs
- article/plain-text publications
- other long-form document ingestion pipelines

### Current limitations

- Broad vague follow-ups are still weaker than precise transcript-grounded
  questions on the direct Responses path.
- Chat-completions follow-ups are safer now, but in weak-retrieval cases they
  may refuse instead of inferring a broad answer.
- The architecture is now the right one; the next tuning work is retrieval
  quality and vague-follow-up answer quality, not transcript acquisition.

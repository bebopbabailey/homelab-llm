# `vector-db` Guide

This document covers both:
- the practical mental model for using `vector-db`
- the operator view of how it fits into the stack

## What It Is

`vector-db` is the durable retrieval substrate for long-form content in this
repo.

It is not just “the thing behind the YouTube lane.” It is the general service
that stores and retrieves:
- chunked source passages
- embeddings
- metadata
- source spans
- durable `response_id -> document_id` mappings

Its job is to let other services talk over long documents without pretending
provider conversation state is durable memory.

The current primary backend is Elasticsearch. `pgvector` remains only as a
temporary rollback path.

## How It Is Used Right Now

The most important practical point is:

- `vector-db` is live and useful now as a retrieval service
- the polished everyday UX on top of it is still arriving in phases

So the current reality is:

1. **Specialized pipelines already use it**
- `task-youtube-summary` uses it for long-video follow-up retrieval
- `docs-mcp` now uses it for curated document ingest and evidence search over
  Studio-local manuals

2. **Direct service/API use is available now**
- operators and local tools can upsert/search documents directly against the
  memory API
- this is already enough to build reliable retrieval-backed workflows without
  waiting for a bigger front-end integration pass

3. **The broad end-user UX is still a later layer**
- LiteLLM-brokered generic doc chat is a later phase
- Open WebUI-native ergonomic document workflows are also a later phase
- `vector-db` is the durable substrate underneath those future surfaces, not
  the final UX by itself

If you want the blunt version:

- **today**: use `vector-db` through `docs-mcp`, `task-youtube-summary`, or
  direct API calls
- **later**: richer “just chat with my whole library” UX gets layered on top

## Concrete Current Examples

### 1. YouTube follow-up retrieval

Current path:

```text
YouTube URL
-> media-fetch-mcp gets transcript
-> litellm-orch indexes long transcript into vector-db
-> vector-db stores chunks + spans + response-map
-> follow-up question resolves previous_response_id
-> vector-db returns grounded transcript chunks
```

Why `vector-db` matters here:
- the long video does not live only in provider conversation state
- retrieval stays durable across turns and restarts
- hits include transcript spans and chunk text

### 2. `docs-mcp` over music manuals

Current phase-1 path:

```text
registered library on Studio
-> docs-mcp extracts/chunks one manual
-> docs-mcp upserts into vector-db
-> docs-mcp searches vector-db by document handle
-> caller gets evidence-only hits with page spans
```

This is now the cleanest non-YouTube example of how `vector-db` is meant to be
used:

- files stay on Studio
- the ingest/search boundary is a small MCP service by responsibility
- `vector-db` remains the canonical durable store
- answers are synthesized elsewhere, not in the retrieval layer

Concrete handle examples:
- library handle: `library:music-manuals`
- document handle: `manual:music-manuals:reface-en-om-b0`

### 3. Direct API retrieval

You can also use `vector-db` directly with no MCP or LiteLLM layer in between.

That is appropriate when:
- you are building a small service around one corpus
- you want explicit control over `document_id`
- you want evidence retrieval without another orchestration layer

Minimal pattern:

```text
normalize content
-> POST /v1/memory/upsert
-> later POST /v1/memory/search
-> synthesize answers in your own caller
```

This is already a valid production shape in this repo.

## Core Mental Model

Think of `vector-db` as a document memory service with three responsibilities:

1. **Ingest**
- accept normalized documents and chunks
- generate embeddings
- store text, vectors, metadata, and spans

2. **Retrieve**
- search by text and vector similarity
- filter by `document_id`, `source_type`, and metadata
- return the best grounded chunks

3. **Resolve follow-up state**
- map public `response_id` values back to durable `document_id`
- support long-running Q&A flows that survive beyond one provider turn

The pattern is:

```text
source acquisition
-> normalized chunks/spans
-> vector-db upsert
-> retrieval search
-> grounded answer synthesis elsewhere
```

`vector-db` owns retrieval durability. It does not own inference.

## What Lives In It

### Documents

At the document level, `vector-db` tracks things like:
- `document_id`
- `source_type`
- `title`
- `uri`
- metadata

Examples:
- `youtube:-QFHIoCo-Ko`
- `pdf:team-handbook-v3`
- `article:llm-evals-2026-04`

### Chunks

At the chunk level, it stores:
- `chunk_id`
- `document_id`
- `source_type`
- `text`
- optional `title` / `section_title`
- filterable metadata
- embedding vector

### Spans

The service is grounded in source spans, not just text blobs.

For transcripts:
- `timestamp_label`
- `start_ms`
- `end_ms`

For publications:
- `page_start`
- `page_end`
- optional character offsets

That means downstream clients can answer from retrieved content with real source
anchors, even when citations are not rendered by default.

### Response-map state

This is one of the most important internal capabilities.

The response-map stores:
- `response_id`
- `document_id`
- `source_type`
- `summary_mode`
- `created_at`

This lets other services do:

```text
previous_response_id
-> resolve to document_id
-> retrieve grounded chunks
-> answer follow-up question
```

That is the durable continuity model.

## API Surface

Primary endpoints:
- `GET /health`
- `GET /v1/memory/stats`
- `POST /v1/embeddings`
- `POST /v1/memory/upsert`
- `POST /v1/memory/search`
- `POST /v1/memory/delete`
- `POST /v1/memory/response-map/upsert`
- `POST /v1/memory/response-map/resolve`

### `POST /v1/memory/upsert`

Use this to store documents and chunks.

The preferred v1 path is explicit document-oriented ingest:

```json
{
  "documents": [
    {
      "document_id": "youtube:-QFHIoCo-Ko",
      "source_type": "youtube",
      "title": "-QFHIoCo-Ko",
      "uri": "https://youtu.be/-QFHIoCo-Ko",
      "metadata": {
        "caption_type": "generated",
        "transcript_language": "English (auto-generated)"
      },
      "chunks": [
        {
          "chunk_index": 0,
          "text": "[00:14] ...",
          "timestamp_label": "00:14",
          "start_ms": 14960,
          "end_ms": 1664200,
          "metadata": {
            "caption_type": "generated"
          }
        }
      ]
    }
  ]
}
```

Old single-text upserts still work, but they are not the preferred long-form
path.

### `POST /v1/memory/search`

Use this to retrieve grounded chunks.

Example:

```json
{
  "query": "What did they say about the night shift workflow?",
  "profile": "balanced",
  "document_id": "youtube:-QFHIoCo-Ko",
  "source_type": "youtube",
  "render_citations": false
}
```

Typical filters:
- `document_id`
- `source_type`
- `source_types`
- metadata filters

For current practice, prefer these patterns:
- exact document search when you have a stable handle like
  `manual:music-manuals:reface-en-om-b0`
- source-type search when the corpus is intentionally narrow
- metadata filters only when the indexed mapping for that field is part of the
  active contract for your caller

### `POST /v1/memory/response-map/upsert`

Use this when another service has returned a public response id and wants to
bind that answer to a durable document.

Example:

```json
{
  "response_id": "resp_123",
  "document_id": "youtube:-QFHIoCo-Ko",
  "source_type": "youtube",
  "summary_mode": "indexed_long"
}
```

### `POST /v1/memory/response-map/resolve`

Use this to recover the document behind a public response id.

Example:

```json
{
  "response_id": "resp_123"
}
```

## Retrieval Behavior

### Hybrid search

`vector-db` is not “vector only.”

It uses hybrid retrieval:
- lexical search for exact terminology and phrase-style recall
- vector search for semantic similarity
- fusion of both result sets

That is important because long-form technical material usually needs both:
- exact matches for names, APIs, or phrases
- semantic matches for paraphrased concepts

### Retrieval profiles

The service supports internal retrieval profiles:
- `precise`
- `balanced`
- `broad`

These tune things like:
- lexical candidate count
- vector candidate count
- fusion breadth
- final hit count
- default citation rendering behavior

The meaning of the profiles is roughly:
- `precise`: narrower factual retrieval
- `balanced`: default general-purpose mode
- `broad`: wider recall when the query is vague or exploratory

### Exact vs approximate search

For single-document retrieval, the service does not blindly assume HNSW is
always best.

That matters in current real usage:
- `docs-mcp` document search benefits from exact single-document routing
- long-form YouTube follow-ups also benefit when a request resolves to one
  durable `document_id`

## What It Is Not

`vector-db` is not:
- a user-facing chat app
- a generic MCP broker
- a summarizer
- a file-upload UI
- a replacement for source acquisition services

Keep the responsibility split clean:
- source acquisition: `media-fetch-mcp` or another ingestion boundary
- curated document ingest/search surface: `docs-mcp`
- user-facing orchestration: LiteLLM lanes or future UI flows
- durable retrieval: `vector-db`

## Current UX Boundary

If you are trying to decide “is this the thing I talk to directly in daily
life?”, the answer is:

- **sometimes yes for operators and service authors**
- **usually no for end users**

Today the normal consumer surfaces are:
- `docs-mcp` for curated manuals/doc evidence
- `task-youtube-summary` for YouTube transcript conversations
- direct API calls for service-to-service workflows

The broader “chat naturally with my personal libraries in one UI” experience is
still a later layer to build on top of this retrieval substrate.

It supports:
- exact brute-force vector scoring for smaller document scopes
- filtered approximate kNN for larger scopes

This matters because a document-scoped search over a small transcript or PDF
does not always benefit from approximate indexing.

### Spans and citations

Spans are always stored and returned internally on hits.

But citations are not rendered by default. That is a caller choice.

This means:
- the retrieval layer stays grounded
- the user-facing lane decides whether to show timestamps/pages or keep the
  answer cleaner

## Backend and Storage Shape

### Elasticsearch as primary backend

Primary backend:
- Elasticsearch on Studio

Key properties:
- one shared chunk index
- separate document index
- separate response-map index
- `dense_vector`
- HNSW vector indexing
- hybrid retrieval

This service does not need a separate vector DB alongside Elasticsearch.

### Shared index model

The shared chunk index exists so multiple content types can use one retrieval
surface:
- YouTube transcripts
- PDFs
- plain/article text

The service is intentionally broader than one source type.

### Versioned index discipline

The chunk index is versioned by:
- embedding model
- dims
- index type

This is important because retrieval changes are evaluated through fresh index
generations and alias swaps, not by pretending a mapping tweak rewrites old
vectors in place.

## Where It Fits In The Current Stack

### 1. Source acquisition

Another service or helper acquires source content.

Examples:
- `media-fetch-mcp` for YouTube transcripts
- future PDF/article extractors

### 2. Normalization

The content is normalized into:
- document metadata
- explicit chunks
- explicit spans

### 3. `vector-db` ingest

`vector-db` stores the chunks, embeddings, metadata, and identifiers.

### 4. Retrieval-backed answering

Another service retrieves from `vector-db` and performs answer synthesis.

Current main example:
- `litellm-orch` `task-youtube-summary`

So the architecture is:

```text
acquisition service
-> normalized chunks
-> vector-db
-> gateway/task lane
-> grounded answer
```

## How It Is Used Today

### YouTube transcript chat

Current production-style consumer:
- `task-youtube-summary`

Flow:
- gets transcript via `media-fetch-mcp`
- indexes long transcript into `vector-db`
- writes `response_id -> document_id`
- retrieves transcript chunks for follow-up Q&A

### Future publication pipelines

The same retrieval substrate is intended for:
- PDFs
- manuals
- article text
- long-form internal documentation

That is why the service is shaped around `source_type`, spans, shared indexes,
and response-map state rather than a YouTube-only schema.

## Practical Operator Knobs

These are the knobs that matter most.

### Backend mode
- `MEMORY_BACKEND=elastic|legacy|haystack`

Current intended steady state:
- `elastic`

### Embedding model

Current default:
- `studio-nomic-embed-text-v1.5`

This affects:
- vector dimensions
- index generation
- retrieval behavior

### Retrieval profile

Search callers can choose:
- `precise`
- `balanced`
- `broad`

This is one of the first knobs to touch when recall quality looks wrong.

### Exact-search cutoff

The service supports a configurable threshold for when document-scoped retrieval
should use exact vector scoring instead of approximate kNN.

This matters for:
- small single-document scopes
- benchmark tuning

### Reindex path

Any serious change to:
- embedding model
- vector dims
- HNSW/index type
- mapping shape

should be treated as a new index generation, not a tiny in-place tweak.

## Health and Stats

### `GET /health`

Use this to confirm:
- backend mode
- Elastic connectivity
- Elastic version
- license state

### `GET /v1/memory/stats`

Use this to confirm:
- active backend
- current index alias and physical index
- document count
- chunk count
- response-map count
- embedding model
- embedding dims
- vector index type
- HNSW params
- exact-search cutoff
- retriever mode

This is the best quick introspection surface for the live service.

## Examples Of How Other Pipelines Should Use It

### YouTube transcript pipeline

```text
YouTube URL
-> media-fetch-mcp
-> normalized transcript segments
-> /v1/memory/upsert
-> /v1/memory/response-map/upsert
-> /v1/memory/search for follow-up questions
```

### PDF pipeline

```text
PDF
-> deterministic extraction
-> page-aware chunking
-> /v1/memory/upsert
-> document-scoped /v1/memory/search
```

### Article/plain-text pipeline

```text
article text
-> section-aware chunking
-> /v1/memory/upsert
-> retrieval-backed Q&A or summary follow-up
```

The important pattern is always the same:
- normalize first
- keep spans
- upsert once
- retrieve many times

## What It Is Not

`vector-db` is not:
- a summarizer
- an inference service
- a transcript fetcher
- a UI/chat product by itself

It is the durable retrieval and memory layer that other pipelines should build
on top of.

## Current Limitations

- Retrieval quality for vague questions still needs tuning in at least one live
  consumer path.
- The service is architecturally ready for broader document ingestion, but the
  strongest real consumer today is still the YouTube transcript flow.
- `legacy` rollback still exists and should not be retired until the retrieval
  eval pack and longer runtime confidence are in better shape.

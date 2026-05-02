# media-fetch-mcp

`media-fetch-mcp` is the localhost-only MCP retrieval boundary for:
- YouTube transcript retrieval
- live web search through local SearXNG
- cleaned webpage fetch/extraction
- per-conversation web research sessions stored in `vector-db`

It is intentionally `retrieval-only`. It does not summarize, reason, or call a
model internally. Callers use it to gather evidence, then do answer synthesis
elsewhere.

## What To Use

Use these tools by intent:

- `youtube.transcript`
  - Get the full transcript for one supported YouTube video URL.
  - Best when you already know the URL and want source-faithful text.

- `media-fetch.web.search`
  - Get normalized live web candidates from local SearXNG.
  - Best when you want links/snippets only and plan to decide what to fetch.

- `media-fetch.web.fetch`
  - Fetch one public page and turn it into a cleaned evidence payload.
  - Best when you already know the URL you want to read.

- `media-fetch.web.session.upsert`
  - Store cleaned fetch payloads into a per-conversation `vector-db` session.
  - Best when you want durable follow-up retrieval over fetched pages.

- `media-fetch.web.session.search`
  - Retrieve grounded chunks from a stored session.
  - Best for follow-up questions over previously fetched material.

- `media-fetch.web.session.delete`
  - Delete a per-conversation research session.
  - Best for cleanup after a temporary research pass.

- `media-fetch.web.quick`
  - Search -> fetch -> persist -> retrieve in one step.
  - Best when you want a fast web-research evidence bundle for a single query.

- `media-fetch.web.research`
  - Broader search -> broader fetch -> persist -> retrieve.
  - Best when you want to build a richer short-lived research corpus first.

## Mental Model

The service owns the retrieval pipeline, not the answer:

```text
query or URL
-> search candidate URLs (optional)
-> fetch + clean page content
-> persist cleaned chunks to vector-db (optional)
-> retrieve grounded chunks
-> answer synthesis elsewhere
```

Important boundaries:
- `SearXNG` supplies live search candidates.
- `media-fetch.web.fetch` handles extraction/normalization.
- `vector-db` handles durable chunk retrieval.
- your model or agent handles reasoning.

## Tool Surface

Current MCP tools:
- `youtube.transcript`
- `media-fetch.web.search`
- `media-fetch.web.fetch`
- `media-fetch.web.session.upsert`
- `media-fetch.web.session.search`
- `media-fetch.web.session.delete`
- `media-fetch.web.quick`
- `media-fetch.web.research`

See [SERVICE_SPEC.md](./SERVICE_SPEC.md) for the exact contract.

## Run Locally

```bash
cd /home/christopherbailey/homelab-llm/services/media-fetch-mcp
uv venv .venv
uv pip install -e .
uv run python -m media_fetch_mcp --transport streamable-http --host 127.0.0.1 --port 8012
```

Environment knobs that matter most:
- `MEDIA_FETCH_SEARXNG_API_BASE`
- `MEDIA_FETCH_VECTOR_DB_API_BASE`
- `MEDIA_FETCH_VECTOR_DB_WRITE_BEARER_TOKEN`
- `MEDIA_FETCH_SESSION_TTL_SECONDS`

See [RUNBOOK.md](./RUNBOOK.md) for install/restart/log details.

## How To Test

### 1. List tools

```bash
cd /home/christopherbailey/homelab-llm/services/media-fetch-mcp
uv run python - <<'PY'
import asyncio
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

async def main():
    async with streamable_http_client("http://127.0.0.1:8012/mcp") as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            print(sorted(tool.name for tool in tools.tools))

asyncio.run(main())
PY
```

Expect all 8 tools to be present.

### 2. Transcript smoke

```bash
cd /home/christopherbailey/homelab-llm/services/media-fetch-mcp
uv run python - <<'PY'
import asyncio, json
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

URL = "https://youtu.be/-QFHIoCo-Ko?si=EP5WGz2PLVLPWU9j"

async def main():
    async with streamable_http_client("http://127.0.0.1:8012/mcp") as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("youtube.transcript", {"url": URL})
            payload = json.loads(result.content[0].text)
            print(payload["video_id"], payload["language"], payload["caption_type"])
            print("segments", len(payload["segments"]))

asyncio.run(main())
PY
```

### 3. Search smoke

```bash
cd /home/christopherbailey/homelab-llm/services/media-fetch-mcp
uv run python - <<'PY'
import asyncio, json
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

async def main():
    async with streamable_http_client("http://127.0.0.1:8012/mcp") as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                "media-fetch.web.search",
                {"query": "IANA example domain", "max_results": 5},
            )
            payload = json.loads(result.content[0].text)
            print(payload["provider"], len(payload["results"]))
            print(payload["results"][0]["url"])

asyncio.run(main())
PY
```

### 4. Fetch smoke

Use a stable page that actually responds cleanly.

```bash
cd /home/christopherbailey/homelab-llm/services/media-fetch-mcp
uv run python - <<'PY'
import asyncio, json
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

async def main():
    async with streamable_http_client("http://127.0.0.1:8012/mcp") as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("media-fetch.web.fetch", {"url": "https://example.com"})
            payload = json.loads(result.content[0].text)
            print(payload["extractor_used"], payload["quality_label"])
            print(payload["canonical_url"])
            print(payload["clean_text"][:120])

asyncio.run(main())
PY
```

### 5. Quick-mode end-to-end smoke

```bash
TOKEN="$(platform/ops/scripts/studio_run_utility.sh --host studio -- \
  'cat /Users/thestudio/data/memory-main/secrets/memory-api-write-token')"
export MEDIA_FETCH_VECTOR_DB_WRITE_BEARER_TOKEN="$TOKEN"

cd /home/christopherbailey/homelab-llm/services/media-fetch-mcp
uv run python - <<'PY'
import asyncio, json
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

QUERY = "IANA example domain"
CONVERSATION_ID = "smoke-web-readme"

async def main():
    async with streamable_http_client("http://127.0.0.1:8012/mcp") as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                "media-fetch.web.quick",
                {"conversation_id": CONVERSATION_ID, "query": QUERY},
            )
            payload = json.loads(result.content[0].text)
            print(payload["document_id"], len(payload["sources"]), len(payload["evidence"]))
            cleanup = await session.call_tool(
                "media-fetch.web.session.delete",
                {"conversation_id": CONVERSATION_ID},
            )
            print(json.loads(cleanup.content[0].text)["deleted_documents"])

asyncio.run(main())
PY
```

## Open WebUI Use

Register the MCP backend directly:
- URL: `http://127.0.0.1:8012/mcp`
- path: empty
- auth: `none`

Useful first filters:
- `youtube.transcript`
- `media-fetch.web.fetch`
- `media-fetch.web.quick`
- `media-fetch.web.research`

Practical OWUI prompts:
- `Use youtube.transcript on this URL and summarize the video: <url>`
- `Use media-fetch.web.quick to research "IANA example domain", then answer from the returned evidence.`
- `Search for sources about <topic>, fetch the strongest ones, store them in session <id>, and answer only from retrieved chunks.`

## Reusable Pipeline Recipes

These recipes are MCP-first and do not assume a specific UI or gateway.

### Recipe 1: Search -> Fetch -> Answer

Use when you want a quick answer without session persistence.

```text
media-fetch.web.search(query)
-> pick 1-3 URLs
-> media-fetch.web.fetch(url)
-> answer from cleaned evidence
```

### Recipe 2: Search -> Fetch -> Session -> Retrieve

Use when you expect follow-up questions.

```text
media-fetch.web.search(query)
-> media-fetch.web.fetch(url) for selected URLs
-> media-fetch.web.session.upsert(conversation_id, documents)
-> media-fetch.web.session.search(conversation_id, followup_query)
-> answer from retrieved chunks
```

### Recipe 3: Quick mode

Use when you want the service to do the search/fetch/store/retrieve sequence.

```text
media-fetch.web.quick(conversation_id, query)
-> source list
-> top grounded chunks
-> answer from those chunks
```

### Recipe 4: Research mode

Use when you want a broader temporary corpus first.

```text
media-fetch.web.research(conversation_id, query)
-> broader search/fetch set
-> stored corpus metadata
-> retrieved chunks for continued work
```

## Known Caveats

This service is real-world useful, but not magic.

- SearXNG candidate quality is upstream-dependent.
  - a bad result set can still contain weak or blocked URLs
  - some queries may return `403` or irrelevant pages

- `media-fetch.web.fetch` only handles public `http(s)` HTML/plain-text pages.
  - PDFs and other binaries are out of scope here
  - JS-heavy pages are not handled with browser automation in this slice

- Extraction is best-effort.
  - `trafilatura` is preferred
  - `readability-lxml` is rescue-only
  - visible-text fallback is last resort

- `vector-db` currently does not return every piece of original chunk metadata
  in search hits.
  - expect grounded chunk text, ids, titles, scores, and spans
  - do not assume all stored metadata round-trips in each hit yet

- Helper tools do not synthesize answers.
  - if you want summaries or reasoning, your caller must do that after
    retrieval

## Evals

Service-local eval artifacts live in:
- [eval/README.md](./eval/README.md)
- [eval/query_pack.web.v1.jsonl](./eval/query_pack.web.v1.jsonl)

Use that area for:
- starter regression queries
- manual expected-behavior cases
- future service-local eval fixtures

The first pass is intentionally lightweight: document cases and keep them close
to the service before adding a dedicated runner.

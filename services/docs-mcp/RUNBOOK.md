# Runbook: docs-mcp

## Scope
Studio-hosted MCP operations for curated document-library ingest and evidence retrieval.

Canonical source tree:
- `/home/christopherbailey/homelab-llm/services/docs-mcp`

Current Studio runtime target:
- `/Users/thestudio/optillm-proxy/layer-tools/docs-mcp`

## Utility wrapper
Use the Studio utility wrapper for transient remote commands:
`platform/ops/scripts/studio_run_utility.sh`.

## Preflight (Mini)
```bash
uv run python platform/ops/scripts/validate_studio_policy.py --json
uv run python platform/ops/scripts/audit_studio_scheduling.py --policy-only --json
uv run python platform/ops/scripts/audit_studio_scheduling.py --host studio --json
```

## Deploy service code to Studio
```bash
cd /home/christopherbailey/homelab-llm
./services/docs-mcp/scripts/deploy_studio.sh
```

Preview sync first:
```bash
cd /home/christopherbailey/homelab-llm
./services/docs-mcp/scripts/deploy_studio.sh --dry-run
```

## Start/restart Studio launchd label
```bash
platform/ops/scripts/studio_run_utility.sh --host studio --sudo -- \
  "launchctl bootstrap system /Library/LaunchDaemons/com.bebop.docs-mcp-main.plist || true"
platform/ops/scripts/studio_run_utility.sh --host studio --sudo -- \
  "launchctl kickstart -k system/com.bebop.docs-mcp-main"
```

## Health/smoke
Streamable HTTP MCP should respond on:
- `http://127.0.0.1:8013/mcp`

Basic listener check:
```bash
platform/ops/scripts/studio_run_utility.sh --host studio -- \
  "lsof -nP -iTCP:8013 -sTCP:LISTEN"
curl -fsS http://127.0.0.1:8013/mcp >/dev/null
```

## Direct MCP smoke
```bash
cd /home/christopherbailey/homelab-llm/services/docs-mcp
uv run python - <<'PY'
import asyncio
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client

async def main():
    async with streamable_http_client("http://127.0.0.1:8013/mcp") as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print(await session.call_tool("docs.library.list", {}))
            print(await session.call_tool("docs.library.ingest", {
                "library_handle": "library:music-manuals",
                "relative_path": "reface_en_om_b0.pdf",
                "dry_run": True,
            }))

asyncio.run(main())
PY
```

## Acceptance ingest/search
```bash
cd /home/christopherbailey/homelab-llm/services/docs-mcp
uv run python - <<'PY'
import asyncio
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client

QUERY = "battery"
DOC = "manual:music-manuals:reface-en-om-b0"

async def main():
    async with streamable_http_client("http://127.0.0.1:8013/mcp") as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print(await session.call_tool("docs.library.ingest", {
                "library_handle": "library:music-manuals",
                "relative_path": "reface_en_om_b0.pdf",
            }))
            print(await session.call_tool("docs.document.search", {
                "document_handle": DOC,
                "query": QUERY,
            }))
            print(await session.call_tool("docs.library.search", {
                "library_handle": "library:music-manuals",
                "query": QUERY,
            }))

asyncio.run(main())
PY
```

Expected:
- targeted ingest succeeds
- `document_handle` is `manual:music-manuals:reface-en-om-b0`
- at least one search hit contains `page_start` and `page_end`

## Runtime config notes
- `DOCS_MCP_VECTOR_DB_BASE` should point to the active Studio-local `vector-db`
  API, normally `http://127.0.0.1:55440`.
- `DOCS_MCP_VECTOR_DB_WRITE_TOKEN_FILE` should point to the existing memory API write token file.
- The service stores logical `file://library:...` URIs, not absolute paths.
- Phase-1 defaults intentionally use smaller chunks (`300` chars with `40`
  overlap) to stay below the currently known Nomic embedding failure envelope
  in `vector-db`.

## Rollback
```bash
platform/ops/scripts/studio_run_utility.sh --host studio --sudo -- \
  "launchctl bootout system/com.bebop.docs-mcp-main || true"
platform/ops/scripts/studio_run_utility.sh --host studio --sudo -- \
  "rm -f /Library/LaunchDaemons/com.bebop.docs-mcp-main.plist"
```

If you need to remove the phase-1 acceptance document from `vector-db`, delete only:
```bash
TOKEN="$(platform/ops/scripts/studio_run_utility.sh --host studio -- \
  'cat /Users/thestudio/data/memory-main/secrets/memory-api-write-token')"
curl -fsS http://127.0.0.1:55440/v1/memory/delete \
  -H "Authorization: Bearer ${TOKEN}" \
  -H 'Content-Type: application/json' \
  -d '{"document_id":"manual:music-manuals:reface-en-om-b0"}' | jq .
```

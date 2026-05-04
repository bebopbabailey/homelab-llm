# Runbook: docs-mcp

## Scope
Studio-hosted MCP operations for curated document-library ingest and evidence retrieval.

Canonical source tree:
- `/home/christopherbailey/homelab-llm/services/docs-mcp`

Current Studio runtime target:
- `/Users/thestudio/optillm-proxy/layer-tools/docs-mcp`

Canonical LAN endpoint:
- `http://192.168.1.72:8013/mcp`

Auth and network posture:
- bearer token required on every MCP request
- Studio pf anchor allows Mini `192.168.1.71` plus Studio self-access only

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

What deploy now does:
- syncs the service tree to Studio
- syncs the service venv
- ensures the docs-mcp bearer token exists
- stages the launchd plist
- installs/refreshes the pf anchor
- restarts `com.bebop.docs-mcp-main`

## Manual launchd restart
```bash
platform/ops/scripts/studio_run_utility.sh --host studio --sudo -- \
  "launchctl bootstrap system /Library/LaunchDaemons/com.bebop.docs-mcp-main.plist || true"
platform/ops/scripts/studio_run_utility.sh --host studio --sudo -- \
  "launchctl kickstart -k system/com.bebop.docs-mcp-main"
```

## Token and firewall bootstrap
Bearer token file:
- `/Users/thestudio/data/docs-mcp/secrets/docs-mcp-bearer-token`

Inspect or create it:
```bash
platform/ops/scripts/studio_run_utility.sh --host studio -- \
  "cd /Users/thestudio/optillm-proxy/layer-tools/docs-mcp && ./scripts/ensure_docs_mcp_bearer_token.sh"
```

Install/refresh the pf anchor:
```bash
platform/ops/scripts/studio_run_utility.sh --host studio --sudo -- \
  "cd /Users/thestudio/optillm-proxy/layer-tools/docs-mcp && ./scripts/install_docs_mcp_firewall.sh"
```

## Health and auth smoke
Listener check on Studio:
```bash
platform/ops/scripts/studio_run_utility.sh --host studio -- \
  "lsof -nP -iTCP:8013 -sTCP:LISTEN"
```

Unauthorized request should fail:
```bash
curl -sS -o /tmp/docs-mcp-unauth.txt -w '%{http_code}\n' http://192.168.1.72:8013/mcp
cat /tmp/docs-mcp-unauth.txt
```

Expected:
- HTTP status `401`

Studio-local authenticated probe:
```bash
platform/ops/scripts/studio_run_utility.sh --host studio -- '
TOKEN="$(cat /Users/thestudio/data/docs-mcp/secrets/docs-mcp-bearer-token)"
export DOCS_MCP_TOKEN="$TOKEN"
python - <<'"'"'PY'"'"'
import anyio
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
import os

async def main():
    token = os.environ["DOCS_MCP_TOKEN"]
    async with streamablehttp_client(
        "http://192.168.1.72:8013/mcp",
        headers={"Authorization": f"Bearer {token}"},
    ) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print(await session.call_tool("docs.library.list", {}))

anyio.run(main)
PY'
```

## One-command helper
If you do not want to paste Python snippets, use:

```bash
cd /home/christopherbailey/homelab-llm/services/docs-mcp
uv run python scripts/manual_lookup.py list
uv run python scripts/manual_lookup.py search-document --query "battery power"
uv run python scripts/manual_lookup.py search-library --query "battery power"
```

Status:
- `manual_lookup.py` is currently a read-only convenience helper.
- `ingest` is parked as under construction because the helper client lifecycle
  is still flaky on longer write operations.
- Use the direct MCP Python examples below for authoritative ingest.

This helper assumes the current phase-1 defaults:
- MCP URL: `http://192.168.1.72:8013/mcp`
- library handle: `library:music-manuals`
- document handle: `manual:music-manuals:reface-en-om-b0`
- relative path: `reface_en_om_b0.pdf`
- token file: `/Users/thestudio/data/docs-mcp/secrets/docs-mcp-bearer-token`

Override the endpoint or token if needed:
```bash
uv run python scripts/manual_lookup.py \
  --url http://192.168.1.72:8013/mcp \
  --token-file /Users/thestudio/data/docs-mcp/secrets/docs-mcp-bearer-token \
  search-document --query "battery power"
```

Emit machine-readable output:
```bash
uv run python scripts/manual_lookup.py --json search-document --query "battery power"
```

## Direct MCP smoke
```bash
cd /home/christopherbailey/homelab-llm/services/docs-mcp
uv run python - <<'PY'
import asyncio
from pathlib import Path
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamablehttp_client

TOKEN = Path("/Users/thestudio/data/docs-mcp/secrets/docs-mcp-bearer-token").read_text(encoding="utf-8").strip()

async def main():
    async with streamablehttp_client(
        "http://192.168.1.72:8013/mcp",
        headers={"Authorization": f"Bearer {TOKEN}"},
    ) as (read, write, _):
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
from pathlib import Path
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamablehttp_client

QUERY = "battery"
DOC = "manual:music-manuals:reface-en-om-b0"
TOKEN = Path("/Users/thestudio/data/docs-mcp/secrets/docs-mcp-bearer-token").read_text(encoding="utf-8").strip()

async def main():
    async with streamablehttp_client(
        "http://192.168.1.72:8013/mcp",
        headers={"Authorization": f"Bearer {TOKEN}"},
    ) as (read, write, _):
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
- `DOCS_MCP_BEARER_TOKEN_FILE` should point to the docs-mcp service token file.
- The service stores logical `file://library:...` URIs, not absolute paths.
- Phase-1 defaults intentionally use smaller chunks (`300` chars with `40`
  overlap) to stay below the currently known Nomic embedding failure envelope
  in `vector-db`.

## Rollback
Restore localhost-only service bind and remove the LAN pf rule:
```bash
platform/ops/scripts/studio_run_utility.sh --host studio --sudo -- \
  "launchctl bootout system/com.bebop.docs-mcp-main || true"
platform/ops/scripts/studio_run_utility.sh --host studio --sudo -- \
  "rm -f /etc/pf.anchors/com.bebop.docs-mcp-main"
platform/ops/scripts/studio_run_utility.sh --host studio --sudo -- \
  "pfctl -a com.bebop.docs-mcp-main -F all || true"
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

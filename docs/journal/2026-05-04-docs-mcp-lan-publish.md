# 2026-05-04 docs-mcp LAN publish

## Objective
- Publish `docs-mcp` as a narrow LAN-visible MCP service from Studio so other
  internal callers can reach it.
- Keep the existing `docs-mcp` tool contract and `vector-db` backend intact.

## Runtime shape
- Host: Studio
- Bind: `192.168.1.72:8013`
- Transport: MCP Streamable HTTP
- Launchd label: `com.bebop.docs-mcp-main`
- Backend: Studio-local `vector-db` at `http://127.0.0.1:55440`

## Security posture
- HTTP bearer auth is required on every request.
- Bearer token file:
  - `/Users/thestudio/data/docs-mcp/secrets/docs-mcp-bearer-token`
- Studio pf anchor restricts the listener to:
  - Studio self-access `192.168.1.72`
  - Mini `192.168.1.71`
- Broader LAN access is blocked.

## Notes
- `docs-mcp` moved from localhost-only to explicit Studio LAN bind
  `192.168.1.72:8013`; `0.0.0.0` was not used.
- The launchd deploy path now stages the plist, ensures the bearer token file,
  installs the pf anchor, and restarts the managed label.
- FastMCP Streamable HTTP initially rejected LAN requests with
  `421 Invalid Host header` because its default transport security only allowed
  loopback hosts. `docs-mcp` now appends the configured bind host to the
  allowed host/origin sets before creating the ASGI app.
- Bearer auth initially used Starlette `BaseHTTPMiddleware`, which interfered
  with longer MCP stream lifecycles. The service now uses a plain ASGI auth
  gate instead.
- `docs.library.search` briefly tried to use `vector-db` metadata filtering on
  `library_handle`, but the current Elastic chunk mapping stores `metadata`
  with `dynamic: false`, so that field is not indexed for filtering. Phase 1
  therefore stays on the safe document-fanout search path inside `docs-mcp`.
- The convenience helper `services/docs-mcp/scripts/manual_lookup.py` remains
  useful for `list`, `search-document`, and `search-library`, but its `ingest`
  path is now explicitly parked as under construction. The authoritative ingest
  interface is the MCP tool itself, not the helper.

## Runtime proof
- Unauthenticated request to `http://192.168.1.72:8013/mcp` returns `401` with
  `{"error":"unauthorized","message":"missing bearer token"}`.
- Authenticated `docs.library.list` succeeds over the LAN endpoint.
- Authenticated `docs.document.search` succeeds over the LAN endpoint and
  returns grounded Reface-manual hits with `page_start` / `page_end`.
- Authenticated `docs.library.search` succeeds over the LAN endpoint and
  returns the same grounded Reface-manual evidence.
- Live Studio logs show successful backend calls during authenticated requests:
  - `POST /v1/memory/delete` -> `200 OK`
  - `POST /v1/memory/upsert` -> `200 OK`
  - `POST /v1/memory/search` -> `200 OK`

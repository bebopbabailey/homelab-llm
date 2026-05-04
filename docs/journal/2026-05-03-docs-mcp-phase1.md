# 2026-05-03 docs-mcp phase 1

## Objective
- Add a new Studio-local MCP service, `docs-mcp`, for curated document-library
  ingest and evidence retrieval backed by `vector-db`.
- Keep phase 1 narrow: one library (`library:music-manuals`) and one acceptance
  fixture (`reface_en_om_b0.pdf`).

## Runtime shape
- Host: Studio
- Bind: `127.0.0.1:8013`
- Transport: MCP Streamable HTTP
- Launchd label: `com.bebop.docs-mcp-main`
- Backing store: existing `vector-db`

## Notes
- `docs-mcp` was deployed to the Studio runtime tree at
  `/Users/thestudio/optillm-proxy/layer-tools/docs-mcp` and bootstrapped as
  `com.bebop.docs-mcp-main`.
- `DOCS_MCP_VECTOR_DB_BASE` was switched to `http://127.0.0.1:55440` after an
  approved Studio-local bind fix on the memory API. The memory API launchd
  bind now uses `0.0.0.0:55440` so Studio-local callers can use loopback while
  Mini callers still use the LAN address.
- The Studio Elastic node had unrecoverable local data corruption
  (`CorruptIndexException` under `.../elasticsearch-data/_state`). Per user
  direction, the data directory was reset instead of preserved, then Elastic
  was reinstalled cleanly and brought back up on `127.0.0.1:9200`.
- The first live `docs.library.ingest` run failed because `docs-mcp` was
  sending `section_title=null` for PDF chunks and `vector-db` validates that
  field as a string. `docs-mcp` now normalizes missing section titles to `""`
  before upsert.
- The Reface manual acceptance target was confirmed as:
  - `reface_en_om_b0.pdf`
  - document handle `manual:music-manuals:reface-en-om-b0`
- Live MCP smoke on Studio covered:
  - `docs.library.list`
  - `docs.library.ingest` dry-run for `reface_en_om_b0.pdf`
  - `docs.library.ingest` real run for `reface_en_om_b0.pdf`
  - `docs.document.search` for `manual:music-manuals:reface-en-om-b0`
  - `docs.library.search` for `library:music-manuals`
- After the fix and service restart, the live logs show:
  - `POST /v1/memory/delete` -> `200 OK`
  - `POST /v1/memory/upsert` -> `200 OK`
  - document and library search requests -> `200 OK`
- Acceptance evidence from the stored retrieval payload:
  - query: `battery power`
  - document search returns grounded evidence from
    `file://library:music-manuals/reface_en_om_b0.pdf`
  - `page_start` / `page_end` are present on returned hits
  - example hit includes battery-related text on page `2`
  - additional hit includes the specifications page on page `54`
- `docs.library.search` was tightened for phase 1 to enumerate registered
  document handles and run document-scoped searches, then merge evidence
  locally. This stays within the existing `vector-db` API and avoids relying on
  ad hoc metadata filters for exact library scoping in phase 1.

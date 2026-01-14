# Monitoring DB Schema (SQLite-first, Postgres-ready)

Purpose: store monitoring snapshots + registry index in a minimal relational
schema that can migrate to Postgres later. Designed to keep ops data out of the
RAG memory store.

## Core principles
- SQLite first (single file, low ops)
- Portable to Postgres without schema changes
- Separate ops telemetry from user memory (RAG)

## Tables

### 1) entities
Represents things we monitor or index (services, backends, tools, endpoints).

```sql
CREATE TABLE entities (
  id TEXT PRIMARY KEY,              -- stable ID (e.g., "mlx:8100", "ov:benny-clean-s")
  type TEXT NOT NULL,               -- service | backend | tool | gateway | registry
  label TEXT NOT NULL,              -- human label (e.g., "jerry-xl")
  owner TEXT NOT NULL,              -- owning service (e.g., "mlx", "ov-llm-server")
  docs_ref TEXT,                    -- path to doc or reference
  notes TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

### 2) endpoints
Network endpoints or health URLs for each entity.

```sql
CREATE TABLE endpoints (
  id TEXT PRIMARY KEY,              -- stable ID (e.g., "mlx:8100:v1-models")
  entity_id TEXT NOT NULL,
  kind TEXT NOT NULL,               -- api | health | models | metrics
  url TEXT NOT NULL,
  method TEXT DEFAULT 'GET',
  FOREIGN KEY(entity_id) REFERENCES entities(id)
);
```

### 3) registry_index
Minimal index of registry entries (source-of-truth stays with service).

```sql
CREATE TABLE registry_index (
  id TEXT PRIMARY KEY,              -- stable ID (e.g., "registry:mlx")
  entity_id TEXT NOT NULL,
  registry_path TEXT NOT NULL,      -- filesystem path or URL
  authority TEXT NOT NULL,          -- e.g., "mlx-registry", "ov-registry"
  format TEXT DEFAULT 'json',
  FOREIGN KEY(entity_id) REFERENCES entities(id)
);
```

### 4) snapshots
Time-series snapshots of health or status checks.

```sql
CREATE TABLE snapshots (
  id TEXT PRIMARY KEY,              -- UUID
  entity_id TEXT NOT NULL,
  endpoint_id TEXT,
  status TEXT NOT NULL,             -- ok | warn | error
  detail TEXT,                      -- short message
  payload_json TEXT,                -- raw response (JSON string)
  observed_at TEXT DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(entity_id) REFERENCES entities(id),
  FOREIGN KEY(endpoint_id) REFERENCES endpoints(id)
);
```

## Example IDs
- `entity_id`: `litellm`, `ov:9000`, `mlx:8100`, `mcp:web-fetch`
- `endpoint_id`: `litellm:health`, `mlx:8100:models`

## Migration notes (SQLite → Postgres)
- Use `TEXT` for timestamps initially; migrate to `TIMESTAMPTZ` later.
- Keep IDs as strings (UUIDs or stable names).
- Use JSONB in Postgres for `payload_json` if desired.

## RAG separation
Do not store user memory or summaries here. This DB is for ops telemetry only.
RAG memory should live in a separate store (vector DB + metadata table).

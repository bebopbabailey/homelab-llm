# System Documentation DB Schema (SQLite-first, Postgres-ready)

Purpose: single source of truth for system documentation, model registries, and
service metadata. Monitoring data is derived from **views**, not stored as a
separate truth source.

## Principles
- SQLite first; migrate to Postgres later without schema changes.
- Models are first-class entities (rich metadata).
- Monitoring = **views** over canonical tables + optional logs.

## Core Tables (truth)

### services
```sql
CREATE TABLE services (
  service_id TEXT PRIMARY KEY,
  layer TEXT NOT NULL,            -- interface | gateway | inference | tools | data
  label TEXT NOT NULL,
  host TEXT,
  port INTEGER,
  base_url TEXT,
  health_url TEXT,
  notes TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

### endpoints
```sql
CREATE TABLE endpoints (
  endpoint_id TEXT PRIMARY KEY,
  service_id TEXT NOT NULL,
  kind TEXT NOT NULL,             -- api | health | models | metrics | tool
  url TEXT NOT NULL,
  method TEXT DEFAULT 'GET',
  FOREIGN KEY(service_id) REFERENCES services(service_id)
);
```

### models (first-class)
```sql
CREATE TABLE models (
  model_id TEXT PRIMARY KEY,      -- stable ID (e.g., "ov-phi4-mini")
  family TEXT,                    -- e.g., "phi", "qwen", "llama"
  size TEXT,                      -- e.g., "1.7B", "3B"
  format TEXT,                    -- ov-ir | onnx | mlx | gguf
  quantization TEXT,              -- fp16 | int8 | int4
  platform TEXT,                  -- openvino | mlx | afm
  source_ref TEXT,                -- repo/path
  notes TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

### deployments (model ↔ endpoint)
```sql
CREATE TABLE deployments (
  deployment_id TEXT PRIMARY KEY,
  endpoint_id TEXT NOT NULL,
  model_id TEXT NOT NULL,
  active INTEGER DEFAULT 1,
  config_ref TEXT,                -- optional link to config
  observed_at TEXT DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(endpoint_id) REFERENCES endpoints(endpoint_id),
  FOREIGN KEY(model_id) REFERENCES models(model_id)
);
```

### tools (optional, for MCP)
```sql
CREATE TABLE tools (
  tool_id TEXT PRIMARY KEY,
  service_id TEXT NOT NULL,
  name TEXT NOT NULL,
  transport TEXT,                 -- stdio | http | sse
  spec_ref TEXT,                  -- doc/spec link
  notes TEXT,
  FOREIGN KEY(service_id) REFERENCES services(service_id)
);
```

### events (optional log index)
```sql
CREATE TABLE events (
  event_id TEXT PRIMARY KEY,
  service_id TEXT NOT NULL,
  level TEXT,                     -- info | warn | error
  event TEXT,
  detail TEXT,
  observed_at TEXT DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(service_id) REFERENCES services(service_id)
);
```

## Monitoring Views (derived)
These are computed from core tables + events.

```sql
CREATE VIEW v_service_health AS
SELECT s.service_id, s.label, s.health_url, e.level, e.detail, e.observed_at
FROM services s
LEFT JOIN events e ON s.service_id = e.service_id
WHERE e.level IN ('warn','error');
```

```sql
CREATE VIEW v_model_deployments AS
SELECT d.deployment_id, d.endpoint_id, d.model_id, m.quantization, m.format, d.active
FROM deployments d
JOIN models m ON d.model_id = m.model_id;
```

## Migration notes (SQLite → Postgres)
- Use TEXT for timestamps now; migrate to TIMESTAMPTZ later.
- Keep IDs as strings (UUIDs or stable names).
- In Postgres, you can add JSONB columns if needed.

## RAG separation
This DB is for system documentation + ops metadata. User memory and summaries
should live in a separate store (vector DB + metadata table).

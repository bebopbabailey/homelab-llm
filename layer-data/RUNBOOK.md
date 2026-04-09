# Data Layer Runbook

This layer includes both registries and an active Studio-local vector-store
service boundary.

## Safe checks
```bash
ls -la layer-data/registry || true
rg -n "registry|memory|vector" layer-data -S || true
```

## Active service
- `vector-db` owns the current Studio main memory store.
- Read `layer-data/vector-db/RUNBOOK.md` for health checks, deploy steps, and
  evaluation flow.

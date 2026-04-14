# Data Layer Runbook

This layer includes registries and transitional taxonomy docs only.

## Safe checks
```bash
ls -la layer-data/registry || true
rg -n "registry|memory|vector" layer-data -S || true
```

## Active service
- `vector-db` owns the current Studio main memory store.
- Read `services/vector-db/RUNBOOK.md` for health checks, deploy steps, and
  evaluation flow.

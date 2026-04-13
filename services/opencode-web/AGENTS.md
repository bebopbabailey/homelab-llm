# Agent Guidance: OpenCode Web

## Scope
This service boundary covers the repo-managed `opencode-web.service` contract on the Mini.

## Read First
- `SERVICE_SPEC.md`
- `CONSTRAINTS.md`
- `RUNBOOK.md`

## Supporting Docs
- `ARCHITECTURE.md` for service shape and trust boundaries
- `TASKS.md` for any remaining service-local follow-up

## Key Paths
- Repo-managed unit: `platform/ops/systemd/opencode-web.service`
- Live unit: `/etc/systemd/system/opencode-web.service`
- Local env: `/etc/opencode/env`

## Runtime Contract
- Bind stays `0.0.0.0:4096`
- Tailnet exposure uses `svc:codeagent` only
- Existing Basic Auth stays in place
- Hardening stays enabled
- Writable workspace is limited to `/home/christopherbailey/homelab-llm` plus OpenCode state/cache dirs

## Validation
Use the runbook checks, especially the `nsenter` mount-namespace write test.

# OpenCode Web

OpenCode Web is the Mini-hosted browser UI for this repo. The canonical service contract is:
- Unit: `platform/ops/systemd/opencode-web.service`
- Live bind: `0.0.0.0:4096`
- Tailnet operator URL: `https://codeagent.tailfd1400.ts.net/`
- Tailscale exposure: `svc:codeagent`
- Auth: Basic Auth from `/etc/opencode/env`
- Writable workspace: `/home/christopherbailey/homelab-llm` only, plus OpenCode state/cache paths

Read:
- `SERVICE_SPEC.md`
- `RUNBOOK.md`
- `CONSTRAINTS.md`
- `ARCHITECTURE.md`
- `TASKS.md`

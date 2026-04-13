# Service Spec: OpenCode Web

## Purpose
Browser UI for OpenCode on the Mini, using the same local repo and LiteLLM-backed client configuration as the CLI.

## Interface
- HTTP UI: `0.0.0.0:4096`
- Tailnet operator URL: `https://codeagent.tailfd1400.ts.net/`
- Tailscale exposure: dedicated Service `svc:codeagent`
- Auth: HTTP Basic Auth via `/etc/opencode/env`

## Runtime
- Host: Mini
- User: `christopherbailey`
- Working directory: `/home/christopherbailey/homelab-llm`
- Live unit path: `/etc/systemd/system/opencode-web.service`
- Repo-managed unit path: `platform/ops/systemd/opencode-web.service`

## Hardening
- `NoNewPrivileges=true`
- `PrivateTmp=true`
- `ProtectSystem=strict`
- `ProtectHome=read-only`

## Writable Allowlist
- `/home/christopherbailey/.local/share/opencode`
- `/home/christopherbailey/.local/state/opencode`
- `/home/christopherbailey/.cache/opencode`
- `/home/christopherbailey/homelab-llm`

## Important Behavior
- OpenCode tool approval and systemd filesystem writeability are separate controls.
- Approval prompts for `bash` or `edit` do not override the service sandbox.
- Repo edits and git writes require the repo root to be present in `ReadWritePaths=`.

## Dependencies
- Local OpenCode install at `/home/christopherbailey/.opencode/bin/opencode`
- LiteLLM provider config under `~/.config/opencode/`
- Local auth env file at `/etc/opencode/env`

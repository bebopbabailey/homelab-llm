# Architecture: OpenCode Web

## Purpose
Run the OpenCode browser UI on the Mini with the repo root as the working
directory and a hardened filesystem boundary.

## Process Shape
- systemd service: `opencode-web.service`
- repo-managed unit: `platform/ops/systemd/opencode-web.service`
- live unit: `/etc/systemd/system/opencode-web.service`
- working directory: `/home/christopherbailey/homelab-llm`
- local auth env: `/etc/opencode/env`

## Trust Boundaries
- HTTP Basic Auth gates the UI before the OpenCode session starts.
- OpenCode approval prompts control tool execution only; they do not widen
  filesystem access.
- Model/provider configuration stays in the user-global OpenCode config under
  `~/.config/opencode/`.
- LiteLLM remains the provider path for repo work.

## Filesystem Boundary
- Writable:
  - `/home/christopherbailey/homelab-llm`
  - `/home/christopherbailey/.local/share/opencode`
  - `/home/christopherbailey/.local/state/opencode`
  - `/home/christopherbailey/.cache/opencode`
- Not writable:
  - unrelated home-directory paths outside the explicit allowlist

## Dependency Summary
- Local OpenCode install at `/home/christopherbailey/.opencode/bin/opencode`
- LiteLLM gateway on the Mini via the user's OpenCode provider configuration
- systemd sandboxing and local auth env for runtime enforcement

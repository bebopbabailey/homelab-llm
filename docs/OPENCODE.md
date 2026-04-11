# OpenCode

## Purpose
OpenCode is the primary coding client for this repo. It uses LiteLLM aliases and
keeps clients on the gateway contract.

## Install (MacBook)
OpenCode installs into `~/.opencode/bin/opencode`. Ensure it is on PATH:
```bash
mkdir -p ~/.local/bin
ln -sf "$HOME/.opencode/bin/opencode" "$HOME/.local/bin/opencode"
```

## Bootstrap (recommended)
Use the repo bootstrap script on each machine:
```bash
bash /home/christopherbailey/homelab-llm/platform/ops/scripts/setup-opencode.sh
```

Default behavior:
- auto-select first reachable base URL in this order:
  1) `http://192.168.1.71:4000/v1`
  2) `http://127.0.0.1:4000/v1`
  3) `https://gateway.tailfd1400.ts.net/v1`
- machine-local default model can be overridden by repo-local `opencode.json`
- machine-local small-model default can be overridden by repo-local `opencode.json`

Optional override:
```bash
OPENCODE_LITELLM_BASE_URL=http://192.168.1.71:4000/v1 \
  bash /home/christopherbailey/homelab-llm/platform/ops/scripts/setup-opencode.sh
```

## Manual config
Config file:
- `~/.config/opencode/opencode.json`

Key file:
- `~/.config/opencode/litellm_api_key`
- Keep this local-only and never commit keys.

Base URL:
- LAN devices: `http://192.168.1.71:4000/v1`
- Mini on-host: `http://127.0.0.1:4000/v1`
- Remote operator path: `https://gateway.tailfd1400.ts.net/v1`

## Prerequisite machine-local config
Before relying on the repo-local OpenCode contract in this repo, the user-global
OpenCode config must already:
- define the `litellm` provider
- expose `litellm/deep`, `litellm/main`, and `litellm/fast`
- own machine-local provider settings such as base URL, API key, and provider
  options

Repo-local `opencode.json` overrides defaults and adds repo-shared
instructions, agents, skills, and permissions. It does not redefine provider
URLs, API keys, or other machine-local settings.

Minimal config example:
```bash
cat > ~/.config/opencode/opencode.json <<'JSON'
{
  "$schema": "https://opencode.ai/config.json",
  "provider": {
    "litellm": {
      "npm": "@ai-sdk/openai-compatible",
      "options": {
        "baseURL": "http://192.168.1.71:4000/v1",
        "apiKey": "{file:~/.config/opencode/litellm_api_key}"
      },
      "models": {
        "deep": { "name": "Deep" },
        "fast": { "name": "Fast" },
        "main": { "name": "Main" }
      }
    }
  },
  "model": "litellm/deep",
  "small_model": "litellm/fast",
  "permission": {
    "bash": "ask",
    "edit": "ask"
  }
}
JSON
```

## Repo-local control surface
Repo-shared OpenCode behavior in this repo should live in:
- `opencode.json`
- `.opencode/instructions/`
- `.opencode/agents/`
- `.opencode/skills/`

These files are the repo-local OpenCode control plane. They are checked into
git and apply only inside this repo.

## Behavior surfaces
- `AGENTS.md`: native OpenCode project rules surface
- `instructions`: explicit extra instruction files loaded through `opencode.json`
- `agents`: locked model/prompt/permission bundles
- `skills`: on-demand reusable workflows loaded through the `skill` tool
- `commands`: thin prompt entrypoints, not the primary policy surface

In this repo, agents and skills are the primary OpenCode control surface.

Repo-local durability posture:
- use `homelab-durability` or `homelab_durability` for repo-local durable work
- stages are `Discover`, `Design`, `Build`, and `Verify`
- the startup declaration is conditional, not universal: require it before
  proposing commands or file edits, not for every read-only turn
- rollback is conditional, not universal: require it for restarts,
  running-system config changes, destructive operations, and host-level
  mutations
- concurrent implementation work should use a separate worktree per agent/effort
- the primary worktree is baseline-only and must not host `Build`/`Verify`
  mutations
- start new implementation work from the clean primary worktree with
  `uv run python scripts/start_effort.py --id <effort-id> --scope <repo-path>`
  or `uv run python scripts/start_effort.py --id <effort-id> --service <service-id>`
- dirty context-only worktrees should use `uv run python scripts/worktree_effort.py park --notes "<reason>" --json`
- local `Build`/`Verify` passes should run
  `uv run python scripts/worktree_effort.py preflight --stage <stage> --json`
  before repo writes
- land a finished linked lane from the clean primary worktree with
  `uv run python scripts/closeout_effort.py --worktree <path> --json`
- concurrent-effort metadata is local to each worktree; `NOW.md` is not the
  effort registry
- the compatibility-first service registry lives at
  `platform/registry/services.jsonl`, with `scripts/service_registry.py` as the
  canonical resolver
- `uv run python scripts/worktree_effort.py close --json` is metadata-only
- broad parallel docs/layer lanes are not allowed while another implementation
  lane is active; the same rule applies to broad `services` and `experiments`
  scopes
- first-party services under `layer-*`, `services/`, and `experiments/` are
  plain tracked directories; lane bootstrap and closeout should not require
  submodule sync or gitlink audits
- closeout is local-only and deterministic: no auto-rebase, no push, and no
  automatic `NOW.md` edits
- root/doc placement hygiene is enforced separately by
  `scripts/repo_hygiene_audit.py`
- internal markdown-link integrity is enforced by `scripts/docs_link_audit.py`

Lane note:
- `main` (`qwen3-next-80b`) supports `tool_choice:"auto"` via `mlxctl`-managed
  vLLM launch settings.
  The active `8101` runtime uses `--tool-call-parser hermes` and no
  `--reasoning-parser`.
- `main` is currently accepted for public repo work on the basis of
  `tool_choice:"auto"`, long-context sanity, and concurrency validation.
  Forced-tool semantics remain unsupported on the current build, and
  structured outputs remain outside the accepted public `main` contract on the
  current backend path.
- `fast` remains the canonical small-model alias for repo-local OpenCode policy,
  and the settled GPT backend family is `llmster`/llama.cpp on shared `8126`.

Backend flag tuning for `main` and `deep` is separate from repo-local OpenCode
hardening.

## Lane policy
- `deep`: trusted default repo-work lane
- `main`: canary repo-work lane with a fail-closed repo-evidence rule
- `fast`: synthesis-only lane

Approved runtime contract:
- active public LLM aliases are `fast`, `main`, and `deep`
- `main` is the hardened Qwen3-Next canary on canonical Studio port `8101`
- MAIN validation is currently satisfied by `tool_choice:"auto"`, long-context
  sanity, branch-generation suitability, and concurrency posture
- structured outputs are a known accepted limitation on the current runtime and
  are not part of the closed public `main` contract
- MAIN forced-tool semantics are intentionally not part of the accepted baseline

Repo-local OpenCode defaults in this repo:
- default model: `litellm/deep`
- small model: `litellm/fast`

## Commands
Canonical markdown command locations:
- user-global commands: `~/.config/opencode/commands/`
- project-local commands: `.opencode/commands/`

Current local convention:
- user-global custom commands on this machine should be created under `~/.config/opencode/commands/`
- the older `~/.opencode/commands/` path is treated as legacy compatibility only and should not be used for new commands

Current Phase A command:
- canonical path: `~/.config/opencode/commands/phase-a.md`
- deprecated legacy copy: `~/.opencode/commands/phase-a.md.deprecated`

Scope note:
- command-path normalization is separate from prompt or lane-behavior fixes
- moving a command into repo-local `.opencode/commands/` would make it a project-shared surface and is a separate decision

## OpenCode Web on Mini
The browser UI is a separate systemd service:
- repo-managed unit: `platform/ops/systemd/opencode-web.service`
- live unit: `/etc/systemd/system/opencode-web.service`
- bind: `0.0.0.0:4096`
- tailnet operator URL: `https://codeagent.tailfd1400.ts.net/`
- Tailscale exposure: dedicated Service `svc:codeagent`
- auth: HTTP Basic Auth via `/etc/opencode/env`
- working directory: `/home/christopherbailey/homelab-llm`

Writable sandbox contract:
- OpenCode approval prompts (`permission.bash=ask`, `permission.edit=ask`) only approve tool execution.
- Filesystem writeability is enforced separately by the `opencode-web.service` systemd sandbox.
- The canonical writable workspace for the web service is `/home/christopherbailey/homelab-llm`.
- OpenCode state/cache dirs remain writable under `~/.local/share/opencode`, `~/.local/state/opencode`, and `~/.cache/opencode`.

Do not commit secrets:
- local auth env file: `/etc/opencode/env`
- template only: `platform/ops/templates/opencode.env.example`

Service boundary docs:
- `layer-interface/opencode-web/SERVICE_SPEC.md`
- `layer-interface/opencode-web/RUNBOOK.md`

## Quick checks
List models:
```bash
opencode models litellm
```

One-shot run:
```bash
opencode run -m litellm/deep "Reply with exactly: plan-ok"
```

Run a named command:
```bash
opencode run --command phase-a "Inspect docs/OPENCODE.md and summarize the commands section."
```

Start (TUI):
```bash
opencode
```

Web auth check:
```bash
curl -i http://127.0.0.1:4096/ | sed -n '1,20p'
```

## MCP tools
MCP parity is out of scope for this simple setup and can be added later.

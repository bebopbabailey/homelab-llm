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
  1) `https://gateway.tailfd1400.ts.net/v1`
  2) `http://100.69.99.60:4443/v1`
  3) `http://127.0.0.1:4000/v1`
- `model=litellm/boost-plan`
- `small_model=litellm/boost-fastdraft`

Optional override:
```bash
OPENCODE_LITELLM_BASE_URL=http://127.0.0.1:4000/v1 \
  bash /home/christopherbailey/homelab-llm/platform/ops/scripts/setup-opencode.sh
```

## Manual config
Config file:
- `~/.config/opencode/opencode.json`

Key file:
- `~/.config/opencode/litellm_api_key`
- Keep this local-only and never commit keys.

Base URL:
- Mini: `http://127.0.0.1:4000/v1`
- Tailnet devices (MacBook): `https://gateway.tailfd1400.ts.net/v1`

Minimal config example:
```bash
cat > ~/.config/opencode/opencode.json <<'JSON'
{
  "$schema": "https://opencode.ai/config.json",
  "provider": {
    "litellm": {
      "npm": "@ai-sdk/openai-compatible",
      "options": {
        "baseURL": "https://gateway.tailfd1400.ts.net/v1",
        "apiKey": "{file:~/.config/opencode/litellm_api_key}"
      },
      "models": {
        "deep": { "name": "Deep" },
        "fast": { "name": "Fast" },
        "main": { "name": "Main" },
        "boost": { "name": "Boost" },
        "boost-plan": { "name": "Boost Plan" },
        "boost-plan-verify": { "name": "Boost Plan Verify" },
        "boost-ideate": { "name": "Boost Ideate" },
        "boost-fastdraft": { "name": "Boost Fastdraft" }
      }
    }
  },
  "model": "litellm/boost-plan",
  "small_model": "litellm/boost-fastdraft",
  "permission": {
    "bash": "ask",
    "edit": "ask"
  }
}
JSON
```

Lane note:
- `main` (`qwen3-next-80b`) supports `tool_choice:"auto"` via `mlxctl`-managed
  vLLM parser resolution (logical `qwen3` -> runtime `qwen3_xml` on current build).

## Quick checks
List models:
```bash
opencode models litellm
```

One-shot run:
```bash
opencode run -m litellm/boost-plan "Reply with exactly: plan-ok"
```

Start (TUI):
```bash
opencode
```

## MCP tools
MCP parity is out of scope for this simple setup and can be added later.

## Coding-quality profiles (OptiLLM on Studio)
Use these aliases when high-quality coding plans are the priority:
- `litellm/boost-plan`: `plansearch` over `deep` lane (default).
- `litellm/boost-plan-verify`: `self_consistency` over `deep` lane for critique pass.
- `litellm/boost-ideate`: `moa` over `deep` lane for divergent architecture exploration.
- `litellm/boost-fastdraft`: `bon` over `fast` lane for lower-cost drafting.

Recommended two-pass workflow:
1. `opencode run -m litellm/boost-plan "<task>"`
2. `opencode run -m litellm/boost-plan-verify "Critique and harden this plan: <paste output>"`

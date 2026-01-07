# Aider Setup (3-Model Routing via LiteLLM)

This repo exposes a single OpenAI-compatible endpoint via LiteLLM and routes
requests to three backend models. Aider can use separate main, editor, and weak
models while still talking to a single API base URL.

## Prerequisites
- LiteLLM proxy running and reachable (default in this repo: `http://<mini-host>:4000`).
- Three upstream OpenAI-compatible backends (e.g., `mlx-openai-server`) running
  on distinct ports and defined in `config/router.yaml`.
- Environment variables set for each upstream (see `config/env.example`).

## Aider config
Create `.aider.conf.yml` in your project or home directory:

```yaml
openai-api-base: http://<mini-host>:4000
openai-api-key: dummy

model: jerry-architect
editor-model: jerry-editor
weak-model: jerry-weak
```

Notes:
- Aider uses the OpenAI-compatible API base URL but passes the model name string you configure (plain `jerry-*` names are expected).
- Architect mode uses the main model plus the editor model for edits.

## Optional: model aliases
If you prefer shorthand:

```yaml
alias:
  - "arch:jerry-architect"
  - "edit:jerry-editor"
  - "weak:jerry-weak"
model: arch
editor-model: edit
weak-model: weak
```

## Usage
- Start Aider normally, then use `/architect` to enable architect mode.
- Use `/model` or update `.aider.conf.yml` to switch models if needed.

## Optional: switch to `jerry-chat` for planning
If you load the standalone GPT-OSS model on the Studio, you can switch your main model
for planning sessions:
- `/model jerry-chat`
Note: `jerry-chat` is now included in the default LiteLLM config.

## Troubleshooting
- If Aider says a model is unknown, ensure the model name matches a
  `model_name` entry in `config/router.yaml`.
- Confirm LiteLLM can reach each backend using the URLs in your env file.

## Launch Checklist
1. Start three `mlx-openai-server` instances on distinct ports (for example: `8103`, `8101`, `8102`).
   - Studio helper: `scripts/run-mlx-studio.sh`
   - Stop helper: `scripts/stop-mlx-studio.sh`
2. Set the LiteLLM env vars in `config/env.local` and export them (or load via systemd).
3. Start the LiteLLM proxy on the Mini (default port `4000`).
4. From a client, verify `GET /v1/models` shows `jerry-*` and `lil-jerry`.
5. Launch Aider and run `/architect` to ensure both main and editor models route correctly.

# Service Spec: Open WebUI

## Purpose
Human-facing UI for LLM and voice interactions routed through LiteLLM.

## Interface
- HTTP UI: `0.0.0.0:3000`
- Health: `GET /health`

## Dependencies
- LiteLLM proxy at `http://127.0.0.1:4000/v1`
- Human-chat model traffic uses the LiteLLM/OpenAI connection on the standard
  Chat Completions path.
- Speech path:
  - Open WebUI -> LiteLLM only
  - LiteLLM -> Orin `voice-gateway` only
  - Open WebUI must not call the Orin directly for STT or TTS
- Local SearXNG JSON endpoint via documented Open WebUI config
- Restart-time hotfix script at `scripts/openwebui_querygen_hotfix.py`, which
  hardens query generation and pre-fetch result hygiene inside the installed
  Open WebUI runtime without changing the supported topology
- Local Open Terminal integrations on the Mini:
  - native terminal server at `http://127.0.0.1:8010`
  - read-only MCP tool server at `http://127.0.0.1:8011/mcp`

## Configuration
- `/etc/open-webui/env` (systemd `EnvironmentFile`)
- `/etc/systemd/system/open-webui.service.d/*.conf` (service overrides)
- data stored in `/home/christopherbailey/.open-webui`
- terminal/tool server registrations are currently persisted through the Open
  WebUI admin config API, not env-only authority
- restart-time runtime patching currently targets:
  - `open_webui/utils/middleware.py`
  - `open_webui/routers/retrieval.py`

## Audio configuration surface
- `AUDIO_STT_ENGINE`
- `AUDIO_STT_OPENAI_API_BASE_URL`
- `AUDIO_STT_OPENAI_API_KEY`
- `AUDIO_STT_MODEL`
- `AUDIO_TTS_ENGINE`
- `AUDIO_TTS_OPENAI_API_BASE_URL`
- `AUDIO_TTS_OPENAI_API_KEY`
- `AUDIO_TTS_MODEL`
- `AUDIO_TTS_VOICE`
- `AUDIO_TTS_OPENAI_PARAMS`
- `AUDIO_TTS_SPLIT_ON`

## Canonical canary values
- `AUDIO_STT_ENGINE=openai`
- `AUDIO_STT_OPENAI_API_BASE_URL=http://127.0.0.1:4000/v1`
- `AUDIO_STT_MODEL=voice-stt-canary`
- `AUDIO_TTS_ENGINE=openai`
- `AUDIO_TTS_OPENAI_API_BASE_URL=http://127.0.0.1:4000/v1`
- `AUDIO_TTS_MODEL=voice-tts-canary`
- `AUDIO_TTS_VOICE=alloy`

## Config authority
- Audio env in `/etc/open-webui/env` remains the authority for the speech path.
- Terminal/tool server registrations currently use Open WebUI persistent config.
- The LiteLLM/OpenAI provider connection also persists in Open WebUI state in
  practice. `ENABLE_PERSISTENT_CONFIG=False` does not prevent stale provider
  mode from surviving in the DB, so the DB plus authenticated `/openai/config`
  is the authority for whether the live connection is still pinned to
  `api_type=responses`.
- `chatgpt-5` is an Open WebUI Chat Completions lane only.
- `chatgpt-5` is treated as text-only in Open WebUI.
- Open WebUI strips terminal, MCP, direct-tool-server, and caller-supplied
  OpenAI tool wiring for `chatgpt-5` before request execution.
- Open WebUI also clears `function_calling` for `chatgpt-5`, so this lane does
  not participate in native or non-native tool loops in the UI.
- The live deployment enforces that clamp through the Open WebUI middleware
  runtime hotfix path on service restart, and the terminal-tool resolution step
  must not re-default `chatgpt-5` back onto `open-terminal`.
- The gateway alias remains available for plain chat/text generation through the
  existing LiteLLM path.

## Ownership boundary
- Open WebUI owns the human UI and audio UX.
- Open WebUI also owns the direct localhost Open Terminal tool/terminal
  registrations on the Mini.
- LiteLLM remains the single client-facing gateway for LLM, STT, and TTS.
- `voice-gateway` remains the repo-owned speech boundary on the Orin.

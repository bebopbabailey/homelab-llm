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
- Local Open Terminal integrations on the Mini:
  - native terminal server at `http://127.0.0.1:8010`
  - read-only MCP tool server at `http://127.0.0.1:8011/mcp`

## Configuration
- `/etc/open-webui/env` (systemd `EnvironmentFile`)
- `/etc/systemd/system/open-webui.service.d/*.conf` (service overrides)
- data stored in `/home/christopherbailey/.open-webui`
- terminal/tool server registrations are currently persisted through the Open
  WebUI admin config API, not env-only authority

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
- For repo review in Open WebUI, keep native tool calling off for `chatgpt-5`.
- If a `chatgpt-5` chat arrives without an explicit terminal or tool selection,
  Open WebUI defaults the lane to the regular `open-terminal` integration.
- After a tool result, Open WebUI retries the known transient `chatgpt-5`
  upstream `502`/response-conversion failure up to two times before giving up.
- Explicit caller selections still win: existing `terminal_id`, `tool_ids`, or
  caller-supplied OpenAI `tools` disable the defaulting behavior.

## Ownership boundary
- Open WebUI owns the human UI and audio UX.
- Open WebUI also owns the direct localhost Open Terminal tool/terminal
  registrations on the Mini.
- LiteLLM remains the single client-facing gateway for LLM, STT, and TTS.
- `voice-gateway` remains the repo-owned speech boundary on the Orin.

# Service Spec: Open WebUI

## Purpose
Human-facing UI for LLM interactions routed through LiteLLM.

## Interface
- HTTP UI: `0.0.0.0:3000` (LAN + tailnet exposure in current deployment)
- Health: `GET /health`

## Dependencies
- LiteLLM proxy at `http://127.0.0.1:4000/v1`
- Current TTS integration target:
  - Voice Gateway on the Orin via dedicated Open WebUI TTS config, not the global LiteLLM OpenAI config
  - proof-only reachability path on the Mini:
    - `127.0.0.1:18081 -> orin:127.0.0.1:18080`
  - TTS-only in this phase; STT is out of scope
- Local SearXNG JSON endpoint via documented Open WebUI config:
  - `WEB_SEARCH_ENGINE=searxng`
  - `SEARXNG_QUERY_URL=http://127.0.0.1:8888/search?q=<query>&format=json`
  - `WEB_SEARCH_RESULT_COUNT=6`
  - `WEB_SEARCH_CONCURRENT_REQUESTS=1`
  - `WEB_SEARCH_DOMAIN_FILTER_LIST=["!localhost","!127.0.0.1","!192.168.1.70","!192.168.1.71","!192.168.1.72","!100.69.99.60","!code.tailfd1400.ts.net","!chat.tailfd1400.ts.net","!gateway.tailfd1400.ts.net","!search.tailfd1400.ts.net"]`
- Built-in Open WebUI loader via documented config:
  - `WEB_LOADER_ENGINE=safe_web`
  - `WEB_LOADER_TIMEOUT=15`
  - `WEB_LOADER_CONCURRENT_REQUESTS=2`
  - `WEB_FETCH_FILTER_LIST=!localhost,!127.0.0.1,!192.168.1.70,!192.168.1.71,!192.168.1.72,!100.69.99.60,!code.tailfd1400.ts.net,!chat.tailfd1400.ts.net,!gateway.tailfd1400.ts.net,!search.tailfd1400.ts.net`

## Configuration
- `/etc/open-webui/env` (systemd `EnvironmentFile`)
- `/etc/systemd/system/open-webui.service.d/*.conf` (service overrides)
- `/etc/systemd/system/open-webui.service.d/50-querygen-hotfix.conf`
  (`ExecStartPre` runtime patch for query-generation fallback hardening)
- Runtime patch helper:
  `/home/christopherbailey/homelab-llm/scripts/openwebui_querygen_hotfix.py`
- Data stored in `/home/christopherbailey/.open-webui`
- Dedicated TTS config surface in the installed build:
  - `AUDIO_TTS_ENGINE`
  - `AUDIO_TTS_OPENAI_API_BASE_URL`
  - `AUDIO_TTS_OPENAI_API_KEY`
  - `AUDIO_TTS_MODEL`
  - `AUDIO_TTS_VOICE`
  - `AUDIO_TTS_OPENAI_PARAMS`
  - `AUDIO_TTS_SPLIT_ON`

## Ownership Boundary
- Open WebUI owns web-search UX plus provider/loader configuration.
- LiteLLM remains the single LLM gateway and does not inject web-search-specific schemas or citations.
- `websearch-orch` is not part of the supported Open WebUI path.

## Config Authority
- Current deployment sets `ENABLE_PERSISTENT_CONFIG=False`.
- Systemd env/drop-ins remain authoritative across restarts.
- Admin UI changes to these env-backed settings are non-persistent after restart.

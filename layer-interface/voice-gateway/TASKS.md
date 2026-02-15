# Tasks: voice-gateway

## Next
- Update docs + contract to reflect Orin-hosted Voice Gateway (STT/TTS) and Mini-hosted LiteLLM.
- Implement minimal v1 loop on Orin (PTT -> record -> STT -> LiteLLM -> TTS).
- Add deterministic timeouts and JSONL timing logs.
- Add smoke checks:
  - Orin-local health
  - Mini-to-Orin reachability
  - Orin-to-LiteLLM connectivity

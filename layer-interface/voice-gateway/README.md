# Voice Gateway

Voice Gateway is the homelab’s **voice I/O service** running on the Orin. It
provides STT and TTS for other internal clients, and uses LiteLLM (on the Mini)
for LLM calls.

Mic audio -> STT -> LiteLLM -> TTS -> speaker output

Start here:
- `SERVICE_SPEC.md` (contracts, env)
- `RUNBOOK.md` (operations)

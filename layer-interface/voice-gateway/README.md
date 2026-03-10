# Voice Gateway

Voice Gateway is the homelab’s **voice I/O service** designated for deployment
on the Orin. A live deployment is not documented yet. When deployed, it will
provide STT and TTS for internal clients and use LiteLLM (on the Mini) for LLM
calls.

Mic audio -> STT -> LiteLLM -> TTS -> speaker output

Start here:
- `SERVICE_SPEC.md` (contracts, env)
- `RUNBOOK.md` (operations)

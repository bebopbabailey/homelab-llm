# Voice Gateway — ARCHITECTURE

## Why This Exists
The platform already supports text interaction via Open WebUI routed through LiteLLM.
Voice Gateway adds a local voice loop while preserving platform constraints:

- LiteLLM remains the single gateway.
- Clients do not call backends directly.
- New capability is added via a thin Interface-layer service.

## v1 Data Flow
1) Capture audio (push-to-talk)
2) STT: audio → text
3) LLM: text → response (via LiteLLM)
4) TTS: response → audio
5) Play audio locally

## Boundary Rules
- Voice Gateway is an Interface-layer client.
- Routing decisions belong to LiteLLM config (logical model names).
- Voice Gateway may choose between logical names (fast vs smart), but must not embed backend URLs.

## Component Diagram (logical)
[Mic] → (Voice Gateway)
  ├─ STT backend (local)
  ├─ LiteLLM API client (gateway)
  ├─ TTS backend (local)
  └─ Audio output (speaker)

## Degradation Strategy
- If preferred model fails: retry once, then fallback to a “fast” logical model if configured.
- If all LLM attempts fail: speak a short apology and log the failure.
- If STT fails: speak “I didn’t catch that” and log.
- If TTS fails: log and optionally print response text to console.

## Observability
Voice Gateway logs structured timing for each stage so the system can be tuned and compared later
(MLX vs OpenVINO vs other inference backends) without rewriting the interface layer.

## Security / Exposure
- v1 runs locally on the Mac Mini.
- Any optional control endpoint must bind to localhost only.
- No LAN exposure without an explicit topology update and approval.

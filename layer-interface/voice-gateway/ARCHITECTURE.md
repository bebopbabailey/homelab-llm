# Voice Gateway — ARCHITECTURE

## Why This Exists
The platform already supports text interaction via Open WebUI routed through LiteLLM.
Voice Gateway adds a local voice loop while preserving platform constraints:

- LiteLLM remains the single gateway.
- Clients do not call backends directly.
- New capability is added via a thin Interface-layer service.

## Topology (current plan)
- **Orin** hosts Voice Gateway (STT/TTS): `192.168.1.93`
- **Mini** hosts LiteLLM gateway and Open WebUI
- Voice Gateway calls LiteLLM over the LAN (not localhost).
- Mini/Open WebUI can call Voice Gateway over the LAN for STT/TTS.

## v1 Data Flow
1) Capture audio (push-to-talk) on the Orin (Voice Gateway)
2) STT: audio → text (on Orin)
3) LLM: text → response (via LiteLLM on Mini)
4) TTS: response → audio (on Orin)
5) Play audio locally (Orin)

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
- Voice Gateway is LAN-private on the Orin. It must not be exposed to the public internet.
- Only internal callers (Mini services) should reach it.
- Any optional admin/control endpoint must bind to localhost only on the Orin.

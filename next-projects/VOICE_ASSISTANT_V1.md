# Voice Assistant v1 — Local-First, Reliable, Multi-Backend

> Status: planning artifact only (non-canonical). Validate active runtime ports,
> handles, and service bindings against canonical docs before implementation.

## Purpose

This document defines **Voice Assistant v1**, a local-first voice interaction loop built on top of the homelab-llm platform.

The goal of v1 is not novelty or breadth of features, but **reliable, measurable, and explainable voice interaction** that integrates cleanly with an existing multi-backend LLM platform.

This system exists to answer one question clearly:

> Can I speak to my home assistant and receive a timely, spoken response without relying on cloud services, while remaining resilient to partial system failure?

If the answer is “yes,” v1 is successful.

---

## High-Level Narrative (Hiring Context)

Voice Assistant v1 demonstrates:
- multi-modal interaction (speech ↔ text)
- hardware-aware system design
- strict gateway boundaries (LiteLLM as the single entry point)
- local-first privacy and reliability
- measurable performance characteristics

Rather than building a monolithic assistant, this system is intentionally decomposed into:
- an **interface layer** that owns audio I/O
- a **gateway layer** that owns model routing and policy
- **inference layers** that can evolve independently

This mirrors how production AI systems are built and operated.

---

## Scope (v1)

### In Scope
- Push-to-talk voice input
- Speech-to-Text (STT) running locally on the Mac Mini
- Text reasoning via LiteLLM (single gateway)
- Text-to-Speech (TTS) running locally on the Mac Mini
- Spoken audio output on the same machine
- Clear failure signaling (spoken or logged)
- Measurable end-to-end latency

### Explicitly Out of Scope (v1)
- Wake-word detection
- Remote microphone streaming
- Multi-turn conversational memory
- RAG / document retrieval
- Agent orchestration
- MCP tools beyond basic experimentation
- Home Assistant control (planned v1.5+)

Anything not listed as “In Scope” is deferred by design.

---

## Supported Interaction Flow

1. User presses push-to-talk and speaks
2. Audio is captured locally on the Mac Mini
3. STT transcribes speech to text
4. Text is sent to LiteLLM (`/v1/chat/completions`)
5. LiteLLM routes to an appropriate backend model
6. Response text is returned
7. TTS synthesizes speech locally
8. Audio response is played to the user

At no point does the interface layer call inference backends directly.

---

## Architecture Boundaries

### Interface Layer
- Owns microphone input and speaker output
- Owns user interaction timing
- Owns failure signaling to the user
- Does **not** own model selection logic

### Gateway Layer
- LiteLLM is the single OpenAI-compatible entry point
- Owns routing, fallback, and policy
- Backends remain opaque to clients

### Inference Layers
- May include MLX, OpenVINO, or other backends
- Are interchangeable without changing the voice interface
- Are never called directly by the voice gateway

---

## Hardware Placement (v1)

- **Mac Mini (Ubuntu)**
    - Voice Gateway service
    - STT
    - TTS
    - LiteLLM gateway (existing)

- **Mac Studio**
    - “Smart” LLM backends via MLX (behind LiteLLM)

- **Jetson Orin AGX**
    - Not used in v1
    - Reserved for future low-latency or multimodal extensions

---

## Performance Targets (Initial)

These are targets, not guarantees.

- STT latency: ≤ 500 ms
- LLM reasoning latency: ≤ 1,200 ms (median)
- TTS latency: ≤ 400 ms
- End-to-end (speech end → audio start): ≤ 2.5 seconds

Actual measurements will be logged and documented as part of v1 evaluation.

---

## Reliability Expectations

The system must:
- Fail loudly (spoken or logged), never silently
- Timeout cleanly on STT, LLM, or TTS failure
- Remain usable after service restarts
- Degrade gracefully (e.g., switch to faster model tier if configured)

A system that occasionally refuses to answer clearly is preferable to one that hangs.

---

## Evaluation Artifacts

The following artifacts are expected as part of v1:

- Latency logs per request (STT / LLM / TTS / total)
- At least one documented failure mode and recovery
- A short demo recording showing the full loop
- This document kept in sync with reality

If something works but is not measured or documented, it is treated as experimental.

---

## Definition of Done (v1)

Voice Assistant v1 is considered complete when:
- A user can reliably speak and receive a spoken response
- The system runs unattended for multiple days
- Latency is measurable and repeatable
- The architecture matches the documented boundaries
- No additional features are added “just because”

Anything beyond this is v1.5 or v2.

---

## Future Directions (Non-Binding)

Possible future extensions include:
- Wake-word detection
- Home Assistant command execution
- Multimodal inputs (vision + voice)
- Memory and personalization
- Edge-accelerated audio pipelines

These are intentionally excluded from v1 to protect focus and reliability.
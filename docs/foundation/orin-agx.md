# Jetson Orin AGX

## Purpose
Edge compute host for targeted on-device experiments.

## Source of truth
- Host and runtime endpoints: `docs/foundation/topology.md`

## Access
- Hostname: `orin`
- IP: `192.168.1.93`
- Access method: SSH (`ssh orin`)

## Runtime role (current)
- No inference backends are currently deployed on Orin.
- Voice Gateway (Interface-layer STT/TTS) is planned to run on Orin and will call
  LiteLLM on the Mini for LLM requests.

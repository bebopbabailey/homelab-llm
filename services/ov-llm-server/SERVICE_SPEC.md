# Service Spec: ov-llm-server

## Purpose
Provide a standalone OpenVINO-backed OpenAI-compatible service on the Mini.

## Current posture
- maintenance-only backend
- not part of the active LiteLLM handle surface

## Runtime
- Host: Mini
- Port: `9000`
- Health: `/health`

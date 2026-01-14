# Jetson Orin Inference Node (Bare Metal) — OpenAI-Compatible Endpoint

This doc describes how THE ORIN (Jetson Orin, L4T R35.4.1 / Ubuntu 20.04) is integrated into the homelab as a **headless inference node** with a **stable OpenAI-compatible endpoint**.

**Control plane / orchestrator:** THE MINI (Ubuntu 24), `192.168.1.71`  
**Orin host:** `theorin` (static IP recommended; see “Static IP” section)

## Goals

- Headless-first, LAN-first operation
- OpenAI-compatible REST API for LiteLLM integration (`/v1/*`)
- systemd-managed service
- Least privilege runtime user (`orin-llm`)
- Works with existing forced-command deploy workflow (`deploy` user) by restarting a single target

## Current platform state

- OS: Ubuntu 20.04.6 LTS (Jetson Linux / L4T R35.4.1, JetPack 5.1.2-era)
- CUDA: 11.4 (nvcc present)
- TensorRT: python bindings present (8.5.2.2)
- Service: `llama-cpp-python` OpenAI server, running under systemd

## Endpoint details

- Base URL (LAN): `http://<ORIN_STATIC_IP>:9210`
- OpenAI-compatible API prefix: `/v1`
- Health/model list: `GET /v1/models`
- Chat: `POST /v1/chat/completions`

### Local sanity checks (on Orin)

```bash
curl -fsS http://127.0.0.1:9210/v1/models | jq .
curl -fsS http://127.0.0.1:9210/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "messages":[{"role":"user","content":"Say hello in exactly 5 words."}],
    "temperature":0.2
  }' | jq -r '.choices[0].message.content'

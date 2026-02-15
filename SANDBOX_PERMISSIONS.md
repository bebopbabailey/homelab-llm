# Sandbox Permissions (Draft)

This defines what an agent sandbox is allowed to read/write/execute by scope.

## Sources of truth
Resolve cross-document conflicts using `docs/_core/SOURCES_OF_TRUTH.md`.

## Scope note
- Keep this file pointer-first and concise.
- Layer-level `CONSTRAINTS.md` files remain the most specific sandbox rules for each layer.

## Root (Monorepo Overseer)
- **Read:** full repo (all layers + docs)
- **Write:** root docs only
- **Execute:** read‑only diagnostics (status/logs), no restarts
- **Forbidden:** editing service code/config, changing ports, network exposure

## Code Execution (All Scopes)
- Treat code execution as a **privileged capability**.
- Default: execute untrusted/generated code only inside a containerized sandbox
  (Docker snippet executor pattern). Do not mount secrets into the sandbox.
- If a task requires secrets, networking, or privileged host access, escalate to
  a purpose-built ops agent or require explicit human approval.

## Layer: Interface
- **Read:** layer-interface/*
- **Write:** layer-interface/* docs and configs
- **Execute:** restart interface services only (e.g., Open WebUI)
- **Forbidden:** changes to gateway/inference/tools/data layers

## Layer: Gateway
- **Read:** layer-gateway/*
- **Write:** gateway configs + docs (LiteLLM routing, OptiLLM configs)
- **Execute:** restart gateway services only (LiteLLM, OptiLLM, system monitor)
- **Forbidden:** direct inference changes, port reuse without plan

## Layer: Inference
- **Read:** layer-inference/*
- **Write:** inference configs + docs
- **Execute:** restart inference services only (OpenVINO, MLX/Studio via ops)
- **Forbidden:** system driver installs, global pip, touching ollama

## Layer: Tools
- **Read:** layer-tools/*
- **Write:** tool configs + docs
- **Execute:** restart tool services only (SearXNG); MCP tools remain stdio
- **Forbidden:** new LAN exposure, adding tools without registry updates

## Layer: Data
- **Read:** layer-data/*
- **Write:** data schemas + docs
- **Execute:** no service restarts by default
- **Forbidden:** introducing new DBs without migration plan

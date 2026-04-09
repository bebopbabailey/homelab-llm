# Sandbox Permissions

This defines what an agent sandbox is allowed to read/write/execute by scope.

## Sources of truth
Resolve cross-document conflicts using `docs/_core/SOURCES_OF_TRUTH.md`.

## Scope note
- Keep this file pointer-first and concise.
- Layer-level `CONSTRAINTS.md` files remain the most specific sandbox rules for
  each layer.
- Layer docs define boundary defaults. Service docs may explicitly narrow or
  expand service-local docs/code/config work inside that layer when the service
  contract says so.

## Root (Monorepo Overseer)
- **Read:** full repo (all layers + docs)
- **Write:** root docs only
- **Execute:** read-only diagnostics (status/logs), no restarts
- **Forbidden:** editing service code/config, changing ports, network exposure

## Code Execution (All Scopes)
- Treat code execution as a privileged capability.
- Default: execute untrusted/generated code only inside a containerized
  sandbox. Do not mount secrets into the sandbox.
- If a task requires secrets, networking, or privileged host access, escalate
  to a purpose-built ops agent or require explicit human approval.

## Layer: Interface
- **Read:** `layer-interface/*`
- **Write:** interface docs/configs by default; service-local docs/code/configs
  only when the service bundle explicitly allows them
- **Execute:** service-local diagnostics and restarts only when the service
  runbook explicitly allows them
- **Forbidden:** changes to gateway/inference/tools/data layers

## Layer: Gateway
- **Read:** `layer-gateway/*`
- **Write:** gateway docs/configs; service-local docs/code/configs only when the
  service bundle explicitly allows them
- **Execute:** service-local diagnostics and restarts only when the service
  runbook explicitly allows them
- **Forbidden:** direct inference changes, port reuse without plan

## Layer: Inference
- **Read:** `layer-inference/*`
- **Write:** inference docs/configs by default; service-local docs/code/configs
  only when the service bundle explicitly allows them
- **Execute:** service-local diagnostics and restarts only when the service
  runbook explicitly allows them
- **Forbidden:** system driver installs, global pip, touching ollama

## Layer: Tools
- **Read:** `layer-tools/*`
- **Write:** tool configs + docs
- **Execute:** restart tool services only when the service runbook explicitly
  allows them
- **Forbidden:** new LAN exposure, adding tools without registry updates

## Layer: Data
- **Read:** `layer-data/*`
- **Write:** data schemas + docs
- **Execute:** no service restarts by default unless a service runbook
  explicitly allows them
- **Forbidden:** introducing new DBs without migration plan

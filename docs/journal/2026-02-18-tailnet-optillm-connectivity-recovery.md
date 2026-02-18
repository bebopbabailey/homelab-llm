# 2026-02-18 — Tailnet + OptiLLM connectivity recovery (Studio offline incident)

## Goal / question
Restore `boost` and `boost-deep` after Studio appeared offline in Tailscale Admin and
OptiLLM returned upstream connection failures.

## Incident symptoms
- Studio showed offline in tailnet admin.
- Studio could not reach Mini tailnet endpoints.
- OptiLLM returned `{"error":"Connection error."}` when serving boost traffic.

## Root cause
- Studio `tailscaled` was running but in `NeedsLogin` state (logged out).
- Tailnet dataplane route was down, so Studio could not reach Mini via tailnet.

## Recovery actions
- Re-authenticated Studio through generated Tailscale login URL.
- Confirmed Studio returned to `BackendState=Running` with valid tailnet IP.
- Validated tailnet reachability to Mini (`100.69.99.60`).
- Confirmed single Studio OptiLLM instance still serves both `boost` and `boost-deep`.

## Upstream transport stabilization
- Studio OptiLLM upstream was set to Mini tailnet TCP forward:
  - `http://100.69.99.60:4443/v1`
- Mini Tailscale mapping:
  - `100.69.99.60:4443 -> 127.0.0.1:4000` (LiteLLM localhost)

## Validation snapshot
- Studio local through OptiLLM:
  - `main` returned `boost-ok`
  - `deep` returned `boost-deep-ok`
- Mini-to-Studio OptiLLM path also returned successful response.

## Operational notes
- Keep LiteLLM localhost-only on Mini.
- Use tailnet ingress for remote clients and Studio upstream bridging.
- If service-hostname TLS path regresses, tailnet-IP TCP forward remains a reliable internal fallback.

# 2026-03-16 — LAN-first Studio gateway contract reset

## Summary
- Reset the canonical Mini ↔ Studio service contract to a simple LAN-first topology.
- Normalized Mini LiteLLM to listen on `0.0.0.0:4000` so Studio services can reach it directly at `http://192.168.1.71:4000/v1`.
- Normalized Studio OptiLLM to listen on `192.168.1.72:4020` and call Mini LiteLLM over LAN instead of the broken tailnet bridge.
- Updated runtime lock, validation, health checks, deployment templates, and canonical docs to treat tailnet access as optional operator convenience rather than the primary service path.

## Why
- The Studio Tailscale installation broke and the old tailnet bridge contract was no longer durable enough to treat as the canonical path.
- Live MLX recovery work had already rebound Studio MLX lanes to the LAN IP `192.168.1.72`, so the remaining mixed contract was leaving LiteLLM and OptiLLM on an inconsistent transport story.
- The repo needed one boring source of truth for service-to-service traffic:
  - Mini LiteLLM on the Mini LAN IP
  - Studio MLX and OptiLLM on the Studio LAN IP
  - same ports and same service purposes as before

## Contract changes
- Mini LiteLLM is canonical on:
  - `http://192.168.1.71:4000/v1`
  - localhost remains valid for on-host clients, but is no longer the canonical Studio upstream path
- Studio MLX team lanes remain canonical on:
  - `http://192.168.1.72:8100/v1`
  - `http://192.168.1.72:8101/v1`
  - `http://192.168.1.72:8102/v1`
- Studio OptiLLM is canonical on:
  - `http://192.168.1.72:4020/v1`
- Experimental Studio GPT ports remain:
  - `http://192.168.1.72:8120-8139/v1`
- Tailscale remains optional/manual operator access only and is not the canonical Mini ↔ Studio runtime path.

## Runtime repairs
- Mini LiteLLM systemd runtime was changed from `--host 127.0.0.1` to `--host 0.0.0.0`.
- Studio `com.bebop.optillm-proxy` launchd runtime was changed from:
  - `--host 127.0.0.1`
  - `--base-url http://100.69.99.60:4443/v1`
  to:
  - `--host 192.168.1.72`
  - `--base-url http://192.168.1.71:4000/v1`
- A repo-managed launchd template was added for the Studio OptiLLM label so the runtime is no longer an undocumented snowflake.
- Runtime lock and validators were extended so both Mini LiteLLM and Studio OptiLLM now have explicit bind/upstream contract checks.

## Evidence
- `./platform/ops/scripts/mlxctl studio-cli-sha` matched local and Studio CLI state.
- `./platform/ops/scripts/mlxctl status --checks --json` remained green for `8100/8101/8102`.
- `./platform/ops/scripts/mlxctl verify` remained green after the transport reset.
- Mini LiteLLM readiness succeeded on both:
  - `http://127.0.0.1:4000/health/readiness`
  - `http://192.168.1.71:4000/health/readiness`
- Direct Mini → Studio LAN checks succeeded for:
  - `http://192.168.1.72:8100/v1/models`
  - `http://192.168.1.72:8101/v1/models`
  - `http://192.168.1.72:8102/v1/models`
  - `http://192.168.1.72:4020/v1/models`
- Studio launchd inspection showed `com.bebop.optillm-proxy` listening on `192.168.1.72:4020`.
- Full runtime-lock validation was extended to enforce the new Mini LiteLLM and Studio OptiLLM contract.

## Superseded entry
This entry supersedes the transport assumptions recorded in:
- `docs/journal/2026-03-10-studio-backend-auth-removal-and-tailnet-boundary.md`

That earlier entry remains historically correct for the temporary recovery path at the time, but its tailnet-only service boundary is no longer the canonical contract.

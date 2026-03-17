# 2026-03-10 — Studio backend auth removal and tailnet-only boundary

## Summary
- Removed MLX backend auth enforcement from `mlxctl` and the runtime lock.
- Updated LiteLLM routing/docs to use Studio tailnet endpoints instead of direct LAN URLs.
- Updated the intended runtime contract so Mini LiteLLM is localhost-only and Studio MLX/OptiLLM are localhost-only behind Tailscale Serve.

## Why
- Live inspection showed the Mini gateway and Studio backends were more exposed than intended.
- `mlxctl status --checks` already treated unauthenticated MLX checks as normal, so backend auth had become an inconsistent layer rather than the real trust boundary.
- The intended boundary is LiteLLM auth plus Tailscale policy, not per-lane backend secrets on the Studio.

## Contract changes
- Mini LiteLLM bind is now canonical at `127.0.0.1:4000`.
- Studio MLX team lanes are canonical at `127.0.0.1:8100/8101/8102`.
- Studio OptiLLM is canonical at `127.0.0.1:4020`.
- Remote Studio backend access is canonical over `thestudio.tailfd1400.ts.net:<port>`.
- Active Studio MLX and Studio OptiLLM listeners no longer require backend bearer auth.

## Evidence
- Control-plane changes landed in `platform/ops/scripts/mlxctl`, `platform/ops/runtime-lock.json`, and `platform/ops/scripts/validate_runtime_lock.py`.
- Router/env/docs were updated to the tailnet endpoint contract and the no-backend-auth contract.
- Mini LiteLLM was returned to `127.0.0.1:4000` and the temporary bridge override was later removed after Studio tailnet ingress was verified.
- Studio `mlxctl` was synced; active MLX lanes on `8100/8101/8102` were relaunched through managed `mlxctl` lane labels with `--host 127.0.0.1` and no backend `--api-key`.
- Studio OptiLLM launchd was re-bootstrapped from the staged plist and now runs on `127.0.0.1:4020` without backend bearer auth.
- Studio Tailscale Serve now forwards `4020`, `8100`, `8101`, and `8102` to localhost listeners.
- The current Tailscale-issued Studio device name remains `thestudio-1.tailfd1400.ts.net`; to preserve the canonical single-Studio alias, the Mini pins `thestudio.tailfd1400.ts.net` to the tagged Studio tailnet IP in `/etc/hosts`.
- Final validation succeeded for direct Mini -> Studio tailnet backend access and for LiteLLM `main`, `deep`, `fast`, and `boost` client paths.

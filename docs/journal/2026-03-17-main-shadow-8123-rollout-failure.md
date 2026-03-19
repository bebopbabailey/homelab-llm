# 2026-03-17 — `main-shadow` `8123` live rollout failure and containment

## Summary
- Attempted the first live `main-shadow` rollout on Studio port `8123` using
  the approved baseline `vllm-metal` contract.
- The new shadow lane never reached a healthy `/v1/models` listener.
- Mini LiteLLM was deliberately left unchanged: no `MAIN_SHADOW_*` wiring, no
  LiteLLM restart, and no client-facing alias change.
- After the failed bring-up, Studio became contaminated enough that canonical
  Mini-to-Studio checks for `8100`, `8101`, and `4020` failed, while Mini
  LiteLLM itself remained healthy.

## Goal
Bring up `Qwen3-Next-80B-A3B-Instruct` on Studio `8123` as `main-shadow`,
prove the direct backend contract first, and expose it through LiteLLM only if
the direct backend passed.

## Launch contract used
- Label: `com.bebop.mlx-shadow.8123`
- Bind: `192.168.1.72:8123`
- Runtime: `vllm-metal`
- Model path:
  `/Users/thestudio/models/hf/models--LibraxisAI--Qwen3-Next-80B-A3B-Instruct-MLX-MXFP4/snapshots/35386111fd494a54a4e3a3705758e280c44d9e9e`
- Served model name: `mlx-qwen3-next-80b-mxfp4-a3b-instruct`
- Flags:
  - `--max-model-len 32768`
  - `--generation-config vllm`
  - `--no-async-scheduling`
  - `--enable-auto-tool-choice`
  - `--tool-call-parser qwen3_xml`
- Env:
  - `VLLM_METAL_MEMORY_FRACTION=auto`

## Preflight actions
- Confirmed current canonical Studio lanes `8100`, `8101`, and `8102` were
  healthy before rollout.
- Confirmed `8123` was idle and not yet deployed.
- Quiesced the unmanaged experimental `8120` listener before attempting any
  `8123` runtime conclusions.
- Installed `/Library/LaunchDaemons/com.bebop.mlx-shadow.8123.plist` from the
  repo-owned template and validated plist syntax.

## What happened
- Launchd accepted the new label and showed it as a managed inference service.
- The `vllm serve` process for `8123` started under launchd and remained present
  long enough to be observed via `ps`.
- The lane never reached a healthy HTTP listener on `192.168.1.72:8123`.
- Repeated direct checks to `http://192.168.1.72:8123/v1/models` timed out.
- A 90-second out-of-band monitor also failed to observe a successful response
  from `/v1/models`.

## Blast radius and containment
- No Mini gateway change was made:
  - live `config/env.local` still had no `MAIN_SHADOW_*`
  - LiteLLM was not restarted
  - `/v1/models` on Mini did not expose `main-shadow`
- Mini LiteLLM remained healthy and continued to serve the existing alias set.
- During the failed Studio bring-up, direct Mini-to-Studio checks for:
  - `http://192.168.1.72:8100/v1/models`
  - `http://192.168.1.72:8101/v1/models`
  - `http://192.168.1.72:4020/v1/models`
  all failed.

## Evidence collected
- `launchctl print` showed `com.bebop.mlx-shadow.8123` as the active label and
  reflected the expected argv/env contract.
- `ps` on Studio showed the `vllm serve ... --port 8123` process with the
  intended Qwen model path and flags.
- `/Users/thestudio/vllm-8123.log` and `/Users/thestudio/vllm-8123.err.log`
  existed but did not yield useful startup output before Studio became
  inaccessible enough to block follow-up evidence collection.
- ICMP and TCP port `22` remained reachable on `192.168.1.72`, but later SSH
  attempts failed before further rollback/evidence commands could be run.

## Result
- Status: FAIL
- `main-shadow` is not proven and must not be considered live.
- The rollout did not advance to LiteLLM exposure.

## Next step
- Recover or regain Studio access first.
- Confirm whether `com.bebop.mlx-shadow.8123` is still loaded and boot it out if
  necessary.
- Re-verify canonical Studio listeners `8100`, `8101`, `8102`, and `4020`.
- Capture direct startup failure evidence from a narrower `8123` retry before
  making any more gateway changes.

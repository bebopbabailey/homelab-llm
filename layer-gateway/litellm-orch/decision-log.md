# Decision Log

## 2026-02-27 — Runtime Contract Clarification (supersedes old runtime note)
- Active Studio MLX runtime for team lanes is `vllm-metal` (`vllm serve`) under `com.bebop.mlx-launch`.
- Historical references to `mlx_lm.server` in older entries are retained for chronology only and are not current runtime guidance.

## 2026-01-13 — Naming Expansion + Backend Slots
- Expanded logical model names to `mlx-*`, `ov-*`, `opt-*`.
- MLX ports standardized to `8100-8139` (team 8100-8119, experimental 8120-8139); OpenVINO remains on `9000`.
- `lil-jerry` retired in favor of `ov-*` aliases for OpenVINO.

## 2026-01-03 — Gateway & Naming Decisions
- Chose LiteLLM proxy mode for the gateway (no custom FastAPI forwarder in Phase 1).
- Standardized OpenAI-compatible endpoints: `/v1/chat/completions` and `/v1/models`.
- Adopted plain client-facing model names (superseded; see 2026-01-13 update).

## 2026-01-03 — Backend Topology & Aider Roles
- Historical note (superseded): MLX `mlx_lm.server` lanes ran on the Studio at ports `8100-8139`; OpenVINO remains on the Mini at `9000`.
- Aider uses three roles: main, editor, weak (model names updated in `AIDER.md`).

## 2026-01-03 — MLX Chat Template Issue
- Observed MLX server failures when `apply_chat_template` returns `BatchEncoding`.
- Applied a local patch in the Studio MLX server environment to coerce `BatchEncoding → input_ids`.
- Tracked a durable upstream fix as a “Nice to Have” (fork MLX server or upstream patch).

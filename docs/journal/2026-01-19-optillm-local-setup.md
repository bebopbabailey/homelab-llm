# 2026-01-19 — OptiLLM Local Setup + Showroom Rule

## Summary
- Set up OptiLLM local inference on the Studio with two live ports:
  - `4040` (opt-router-high) → `Qwen/Qwen2.5-72B-Instruct`
  - `4041` (opt-router-balanced) → `Qwen/Qwen2-57B-A14B-Instruct`
- Added showroom/backroom rule: only models present on the Mini or Studio are
  exposed as LiteLLM handles. Seagate is storage-only.

## Notes
- OptiLLM local runs via launchd on the Studio.
- Handles added: `opt-router-high`, `opt-router-balanced`.
- LiteLLM routes these handles to `http://192.168.1.72:4040/v1` and
  `http://192.168.1.72:4041/v1`.

# Tasks: optillm-local

- [x] Create isolated MLX-LM patch kit with OptiLLM-compatible decode contract.
- [x] Implement first decode-time technique (`entropy_decoding`) in overlay module.
- [x] Add direct smoke and benchmark harness (no LiteLLM dependency).
- [x] Document test/benchmark protocol in `OPTILLM_MLX_BACKEND_TESTING.md`.
- [x] Add automated viability gate runner with GO/NO-GO/UNVERIFIED decision output.
- [x] Add repeated viability campaign runner with manifest + per-run log bundles.
- [x] Rebase `runtime/patches/mlx_lm/server.diff` to current upstream and clear maintainability gate.
- [ ] Add second decode-time technique after entropy validation gate.
- [ ] Add streaming decode metadata strategy (separate milestone).
- [ ] Evaluate optional LiteLLM pass-through after isolated viability proof.

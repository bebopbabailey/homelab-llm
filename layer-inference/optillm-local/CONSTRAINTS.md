# Constraints — optillm-local (Orin)

- Inference backend only; no routing or orchestration.
- Must remain on Orin AGX.
- LAN‑reachable only (no public exposure).
- Use `uv` for dependencies; no global `pip`.
- Do not install CUDA drivers or system packages from this repo.

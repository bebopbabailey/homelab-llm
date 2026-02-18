# NOW

Active
- `mlxctl` backend alignment in progress: make `status/verify/load/unload` match
  live Studio `mlx_lm.server` runtime so inference readiness checks are
  trustworthy before further hardening.

NEXT UP
- Validate lane quality gates (`fast/main/deep`) and parser leakage checks after
  `mlxctl` runtime parity lands, then proceed with launchd durability hardening.

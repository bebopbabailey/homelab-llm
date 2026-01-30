# Jetson Orin AGX (Planned)

## Purpose
Edge inference and optimization experiments (non-critical path).

## Source of truth
- Host/ports: `docs/foundation/topology.md`
- Operating rhythm: `docs/foundation/operating-rhythm.md`

## Access
- Hostname: TBD
- Access method: SSH (headless)

## Expected responsibilities
- Run targeted experiments (quantization, runtime profiling, on-device pipelines).
- Avoid becoming a production dependency until stability is proven.

## Onboarding checklist (when added)
- Record OS image + version
- Record services + ports
- Record model cache location + size policy
- Add health checks and rollback commands

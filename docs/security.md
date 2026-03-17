# Security & Exposure Notes

## Network Exposure Model
- **Primary entry point:** LiteLLM on the Mini (port `4000`).
- **Default infra access:** LiteLLM is intended to be reached on the Mini LAN URL
  `http://192.168.1.71:4000/v1`.
- **On-host access:** `http://127.0.0.1:4000/v1` remains valid on the Mini.
- **Optional remote access:** Tailscale may still be used for operator access,
  but it is not the canonical service-to-service contract.

## Backend Services
- **OpenVINO (Mini):** binds `0.0.0.0:9000` for maintenance, but callers use `127.0.0.1:9000`.
- **MLX (Studio):** LAN-only ports `8100–8139`; accessible via Tailscale as needed.

## Tailscale Notes
- Tailnet access is optional/operator-only for this stack contract.
- Do not treat tailnet URLs as the canonical Mini ↔ Studio service path.

## Operational Guidance
- Keep LiteLLM as the only public-facing API endpoint.
- Use SSH over Tailscale for maintenance on backend nodes.

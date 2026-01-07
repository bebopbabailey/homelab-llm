# Security & Exposure Notes

## Network Exposure Model
- **Primary entry point:** LiteLLM on the Mini (port `4000`).
- **Default access:** LiteLLM is intended to be accessed over Tailscale.
- **Fallback access:** SSH into machines via Tailscale if the Mini is unreachable.

## Backend Services
- **OpenVINO (Mini):** `localhost:9000` only (not exposed on LAN/Tailscale).
- **MLX (Studio):** LAN-only ports `8100–8109`; accessible via Tailscale as needed.

## Tailscale Notes
- All machines are members of the same tailnet.
- Use Tailscale ACLs to restrict which devices can access LiteLLM when non-local access is required.
- Current Mini Tailscale IP: `100.69.99.60` (update if it changes).

## Operational Guidance
- Keep LiteLLM as the only public-facing API endpoint.
- Use SSH over Tailscale for maintenance on backend nodes.

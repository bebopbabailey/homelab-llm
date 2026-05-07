# V2 Planning Material: Host Inventory Summary

Not current runtime truth. This file compresses the current five-node baseline set for V2 rebuild planning.

Sources:

- [docs/v2/inventory/MINI_BASELINE.md](MINI_BASELINE.md)
- [docs/v2/inventory/STUDIO_BASELINE.md](STUDIO_BASELINE.md)
- [docs/v2/inventory/ORIN_BASELINE.md](ORIN_BASELINE.md)
- [docs/v2/inventory/HP_BASELINE.md](HP_BASELINE.md)
- [docs/v2/inventory/HAOS_BASELINE.md](HAOS_BASELINE.md)

## Mini baseline summary

- Mini is the active LAN-facing control host with the current public surfaces for gateway, chat UI, code UI, search UI, monitoring, and operator tooling. Evidence: [MINI_BASELINE.md](MINI_BASELINE.md)
- Core live Mini surfaces observed were LiteLLM, Open WebUI, OpenCode Web, OpenHands, SearXNG, Prometheus, Grafana, CCProxy API, Open Terminal MCP, Media Fetch MCP, Samba, Docker, and Tailscale. Evidence: [MINI_BASELINE.md](MINI_BASELINE.md)
- Mini also carries drift that should not be normalized into V2: crash-looping `ov-server.service`, failed `qwen-agent-proxy.service`, inactive `ollama.service`, a shadow LiteLLM on `127.0.0.1:4001`, and Prometheus listening on `*:9090` instead of localhost-only. Evidence: [MINI_BASELINE.md](MINI_BASELINE.md)

## Studio baseline summary

- Studio is the current heavy-runtime host with the incumbent GPT/GGUF compatibility path, a private specialized-runtime signal, and the live retrieval backend. Evidence: [STUDIO_BASELINE.md](STUDIO_BASELINE.md)
- Observed live Studio listeners included `8126`, `4020`, `8120`, `9200`, `55432`, `55440`, and `5601`. Evidence: [STUDIO_BASELINE.md](STUDIO_BASELINE.md)
- Studio also carries unresolved drift: repo canon still points at `8101`, but this baseline observed no `8101` listener, disabled `com.bebop.mlx-lane.8101`, and `mlxctl` unusable from the default shell. Evidence: [STUDIO_BASELINE.md](STUDIO_BASELINE.md)

## Orin baseline summary

- Orin is a live speech appliance host, not just a pending future node. Evidence: [ORIN_BASELINE.md](ORIN_BASELINE.md)
- Observed live Orin speech surfaces included `voice-gateway.service` on `192.168.1.93:18080`, localhost `speaches` on `127.0.0.1:8000`, and `voice-gateway-native-stt.service`. Evidence: [ORIN_BASELINE.md](ORIN_BASELINE.md)
- Orin also carries planning constraints: the offload path appeared through `autofs`, and this pass did not establish any broader inference-runtime role beyond the speech stack. Evidence: [ORIN_BASELINE.md](ORIN_BASELINE.md)

## HP baseline summary

- HP is a separate physical Ubuntu host at `192.168.1.70`, not the live Home Assistant endpoint by observed evidence. Evidence: [HP_BASELINE.md](HP_BASELINE.md)
- The current observed role is light: SSH plus desktop/remote-desktop surfaces, with no observed Home Assistant listener and no observed container workload. Evidence: [HP_BASELINE.md](HP_BASELINE.md)

## HAOS baseline summary

- HAOS is a separate `virsh` VM on Mini, currently running and bridged on `br0`. Evidence: [HAOS_BASELINE.md](HAOS_BASELINE.md)
- Observed evidence places HAOS at `192.168.1.40`, with a live Home Assistant web surface on `:8123`. Evidence: [HAOS_BASELINE.md](HAOS_BASELINE.md)
- This split resolves the earlier ambiguity between the physical HP host and the Home Assistant endpoint. Evidence: [HP_BASELINE.md](HP_BASELINE.md), [HAOS_BASELINE.md](HAOS_BASELINE.md)

## Preserve candidates

- Mini public chat and gateway surfaces: `open-webui.service`, current public gateway surface, `searxng.service`. Evidence: [MINI_BASELINE.md](MINI_BASELINE.md)
- Mini operator and observability surfaces: `opencode-web.service`, `prometheus.service`, `prometheus-node-exporter.service`, `grafana-server.service`, `tailscaled.service`, `docker.service`. Evidence: [MINI_BASELINE.md](MINI_BASELINE.md)
- Mini utility surfaces worth preserving until replaced: `open-terminal-mcp.service`, `media-fetch-mcp.service`, `ccproxy-api.service`, `open-webui-elasticsearch-bridge.service`, Samba. Evidence: [MINI_BASELINE.md](MINI_BASELINE.md)
- Studio incumbent GPT/GGUF compatibility path on `8126`. Evidence: [STUDIO_BASELINE.md](STUDIO_BASELINE.md)
- Studio private specialized-runtime evidence on `127.0.0.1:8120`. Evidence: [STUDIO_BASELINE.md](STUDIO_BASELINE.md)
- Studio retrieval surfaces: Elasticsearch plus memory API, with pgvector preserved as present evidence until reviewed. Evidence: [STUDIO_BASELINE.md](STUDIO_BASELINE.md)
- Studio model stores in `~/.lmstudio`, `~/models`, and `~/.cache/huggingface`. Evidence: [STUDIO_BASELINE.md](STUDIO_BASELINE.md)
- Orin speech surfaces: `voice-gateway.service`, `voice-gateway-native-stt.service`, `speaches.service`, and the `speaches` container. Evidence: [ORIN_BASELINE.md](ORIN_BASELINE.md)
- Orin hardware capture/playback path including the `Shure MV51`. Evidence: [ORIN_BASELINE.md](ORIN_BASELINE.md)
- HAOS qcow2 backing file and live Home Assistant web surface. Evidence: [HAOS_BASELINE.md](HAOS_BASELINE.md)
- HP host identity and SSH entrypoint should be preserved until its future role is explicitly decided. Evidence: [HP_BASELINE.md](HP_BASELINE.md)

## Rebuild-clean candidates

- The public gateway contract on Mini should be rebuilt clean around ADR 0001 and ADR 0003, not inherited from current implementation names. Current evidence: [MINI_BASELINE.md](MINI_BASELINE.md), [../adr/0001-one-public-gateway.md](../adr/0001-one-public-gateway.md), [../adr/0003-registry-derived-routing.md](../adr/0003-registry-derived-routing.md)
- The V2 command-center doc set itself should now become the operator entrypoint for rebuild planning. Evidence: [../README.md](../README.md)
- The Mini monitoring posture should be rebuilt clean to match the documented localhost-only doctrine before any exposure assumptions carry forward. Evidence: [MINI_BASELINE.md](MINI_BASELINE.md), [../V1_DO_NOT_REPEAT.md](../V1_DO_NOT_REPEAT.md)
- The Studio MLX lane story should be rebuilt clean only after host/canon reconciliation, not presumed continuous from V1 docs. Evidence: [STUDIO_BASELINE.md](STUDIO_BASELINE.md)
- The old HP-equals-Home-Assistant shorthand should be rebuilt clean into an explicit HP/HAOS split. Evidence: [HP_BASELINE.md](HP_BASELINE.md), [HAOS_BASELINE.md](HAOS_BASELINE.md)

## Safe-to-stop-later candidates

- Mini prototype cockpit services: `orchestration-cockpit-graph.service`, `orchestration-cockpit-ui.service`. Evidence: [MINI_BASELINE.md](MINI_BASELINE.md)
- Mini failed shadow sidecar: `qwen-agent-proxy.service`. Evidence: [MINI_BASELINE.md](MINI_BASELINE.md)
- Studio already-disabled shadow labels `8123-8125` and disabled non-core MLX/OptiLLM labels. Evidence: [STUDIO_BASELINE.md](STUDIO_BASELINE.md)
- Any current shadow LiteLLM path on Mini should be treated as stop-later only after human review confirms there is no hidden dependency. Evidence: [MINI_BASELINE.md](MINI_BASELINE.md)
- No strong stop-later candidates were asserted for Orin, HP, or HAOS from this pass. Evidence: [ORIN_BASELINE.md](ORIN_BASELINE.md), [HP_BASELINE.md](HP_BASELINE.md), [HAOS_BASELINE.md](HAOS_BASELINE.md)

## Unknown or risky items needing human review

- Mini Prometheus is live on `*:9090`, which conflicts with the expected localhost-only posture. Evidence: [MINI_BASELINE.md](MINI_BASELINE.md)
- Mini Tailscale Serve still maps `:8123` to `192.168.1.40:8123`, which now aligns with host-observed HAOS evidence and conflicts with older repo references to `192.168.1.70:8123`. Evidence: [MINI_BASELINE.md](MINI_BASELINE.md), [HAOS_BASELINE.md](HAOS_BASELINE.md), [HP_BASELINE.md](HP_BASELINE.md)
- Mini has a live shadow LiteLLM process tied to a path not shown in `git worktree list`. Evidence: [MINI_BASELINE.md](MINI_BASELINE.md)
- Studio `8101` remains the highest-risk inventory mismatch because repo canon says active while host evidence says absent. Evidence: [STUDIO_BASELINE.md](STUDIO_BASELINE.md)
- Studio `docs-mcp-main` and `llmster` launchd state both conflict with observed listener/process reality. Evidence: [STUDIO_BASELINE.md](STUDIO_BASELINE.md)
- Studio pgvector and Kibana are present, but neither should be assumed phase-one V2 doctrine without review. Evidence: [STUDIO_BASELINE.md](STUDIO_BASELINE.md)
- Orin offload and broader runtime role still need care; this pass established the speech stack but not a wider inference posture. Evidence: [ORIN_BASELINE.md](ORIN_BASELINE.md)
- HAOS is only host-observed in this pass; direct guest-shell inventory remains a future gap. Evidence: [HAOS_BASELINE.md](HAOS_BASELINE.md)

## V2 phase-one implications

- Phase one should assume Mini remains the operator-facing control host and Studio remains the heavyweight runtime host. Evidence: [MINI_BASELINE.md](MINI_BASELINE.md), [STUDIO_BASELINE.md](STUDIO_BASELINE.md)
- Phase one should preserve the current public gateway contract while rebuilding planning doctrine around one boring gateway, not around a specific V1 backend name. Evidence: [../adr/0001-one-public-gateway.md](../adr/0001-one-public-gateway.md), [STUDIO_BASELINE.md](STUDIO_BASELINE.md)
- Phase one should preserve specialized-runtime evidence on Studio, but keep it private and non-required. Evidence: [../adr/0002-runtime-plane-separation.md](../adr/0002-runtime-plane-separation.md), [STUDIO_BASELINE.md](STUDIO_BASELINE.md)
- Phase one should assume Elastic-backed retrieval is the incumbent runtime reality, while still requiring V2 retrieval-quality revalidation. Evidence: [../adr/0006-retrieval-discipline-before-backend-default.md](../adr/0006-retrieval-discipline-before-backend-default.md), [STUDIO_BASELINE.md](STUDIO_BASELINE.md)
- Phase one should treat Orin as a live preserve-now speech host, while keeping it out of unrelated rebuild slices unless explicitly needed. Evidence: [ORIN_BASELINE.md](ORIN_BASELINE.md)
- Phase one should treat HAOS as the current Home Assistant endpoint and HP as a separate physical host. Evidence: [HAOS_BASELINE.md](HAOS_BASELINE.md), [HP_BASELINE.md](HP_BASELINE.md)

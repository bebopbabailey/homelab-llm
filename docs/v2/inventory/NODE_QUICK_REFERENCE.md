# V2 Planning Material: Node Quick Reference

Not current runtime truth. This is a compact reference for future coding agents working on V2 planning.

## Mini

- Type: physical host
- Access: local repo on `themini`
- Primary IP: `192.168.1.71`
- OS / hardware: Ubuntu `24.04.4 LTS`, `Macmini8,1`
- Current role: public gateway, chat/code/search/operator surfaces
- Key live ports: `3000`, `4000`, `4096`, `8888`, `9090`, `9100`
- Preserve-now signals: public gateway contract, Open WebUI, SearXNG, OpenCode Web, monitoring stack
- Top drift: shadow LiteLLM on `127.0.0.1:4001`, Prometheus on `*:9090`, Home Assistant tailnet mapping points to `192.168.1.40`
- Source: [MINI_BASELINE.md](MINI_BASELINE.md)

## Studio

- Type: physical host
- Access: `ssh studio`
- Primary IP: `192.168.1.72`
- OS / hardware: macOS `26.2`, `Mac15,14`, `Apple M3 Ultra`
- Current role: heavyweight runtime host, retrieval host, private specialized-runtime evidence
- Key live ports: `8126`, `4020`, `8120`, `9200`, `55432`, `55440`, `5601`
- Preserve-now signals: incumbent GPT/GGUF compatibility path, Elastic + memory API, model stores
- Top drift: repo canon still points at `8101`, Docs MCP launchd/listener mismatch, `llmster` launchd/live-state mismatch
- Source: [STUDIO_BASELINE.md](STUDIO_BASELINE.md)

## Orin

- Type: physical host
- Access: `ssh orin`
- Primary IP: `192.168.1.93`
- OS / hardware: Ubuntu `22.04.5`, Jetson AGX Orin Developer Kit
- Current role: live speech appliance host
- Key live ports: `18080`, `18081`, `8000`
- Preserve-now signals: `voice-gateway`, native STT wrapper, `speaches`, audio hardware, `/srv/ssd`
- Top drift: offload path observed through `autofs`; no broader inference-runtime claim should be inferred
- Source: [ORIN_BASELINE.md](ORIN_BASELINE.md)

## HP

- Type: physical host
- Access: `ssh hp`
- Primary IP: `192.168.1.70`
- OS / hardware: Ubuntu `24.04.4`, `Hewlett-Packard 23-p114`
- Current role: unclear / lightweight by observed evidence
- Key live ports: `22`, `3389`, `3390`
- Preserve-now signals: operator access and host identity only
- Top drift: historical docs have conflated this host with Home Assistant, but current evidence does not support that
- Source: [HP_BASELINE.md](HP_BASELINE.md)

## HAOS

- Type: VM on Mini
- Access: host-observed via `virsh` on `themini`
- Primary IP: `192.168.1.40`
- OS / hardware: guest OS not directly probed; VM has `2` vCPU and `4 GiB` RAM
- Current role: live Home Assistant endpoint
- Key live ports: `8123`
- Preserve-now signals: qcow2 backing file, bridge placement on `br0`, live Home Assistant web surface
- Top drift: direct guest-shell evidence is absent; IP comes from host bridge/ARP evidence
- Source: [HAOS_BASELINE.md](HAOS_BASELINE.md)

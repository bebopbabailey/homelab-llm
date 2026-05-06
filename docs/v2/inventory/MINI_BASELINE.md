# V2 Mini Baseline Inventory

## Summary
- Host `themini` is an Ubuntu `24.04.4 LTS` Mac Mini (`Macmini8,1`) on kernel `6.8.0-94-generic`.
- CPU is `Intel(R) Core(TM) i7-8700B CPU @ 3.20GHz` with `12` logical CPUs, `62 GiB` RAM, and no swap.
- Root storage is `227G ext4` with `167G` used and `50G` available; external storage is `/mnt/seagate` at `1.9T exfat` with `1.7T` available.
- Primary LAN identity is `192.168.1.71` on `br0`; Tailscale is healthy on `100.69.99.60` with MagicDNS suffix `tailfd1400.ts.net`.
- Core live Mini surfaces are LiteLLM, Open WebUI, OpenCode Web, OpenHands, SearXNG, Prometheus, Grafana, CCProxy API, Open Terminal MCP, Media Fetch MCP, Samba, Docker, and Tailscale.
- Drift and failures matter for V2 planning: `ov-server.service` is crash-looping, `ollama.service` is inactive, `qwen-agent-proxy.service` is failed, a shadow LiteLLM listens on `127.0.0.1:4001`, and Prometheus is listening on `*:9090` instead of the documented localhost-only posture.
- `docs/v2/README.md` does not exist; V2 planning context is currently anchored by `docs/v2/V2_MIGRATION_NOTES.md` plus the ADR set in `docs/v2/adr/`.

## Host identity
- Hostname: `themini`
- OS: `Ubuntu 24.04.4 LTS`
- Kernel: `Linux 6.8.0-94-generic`
- Architecture: `x86_64`
- Hardware: `Apple Inc. Macmini8,1`
- Repo root: `/home/christopherbailey/homelab-llm`
- Primary worktree branch: `master`
- Git state at inventory time: `master...origin/master [ahead 1]`

## Network
- Active LAN interface is `br0` with `192.168.1.71/24` and global IPv6 `2600:1700:bb52:9010:4cbd:46ff:fe69:63bc/64`.
- `tailscale0` is present with `100.69.99.60/32` and `fd7a:115c:a1e0::e801:6363/128`.
- `docker0` is active on `172.17.0.1/16`; inactive bridges exist on `172.18.0.1/16`, `172.19.0.1/16`, and `172.20.0.1/16`.
- `virbr0` exists but is down on `192.168.122.1/24`.
- Tailscale backend state is `Running` with no reported health errors.
- MagicDNS suffix is `tailfd1400.ts.net`; observed served service names are `svc:chat`, `svc:code`, `svc:codeagent`, `svc:gateway`, `svc:grafana`, `svc:hands`, and `svc:search`.
- Live Tailscale serve mappings:
  - `svc:chat` -> `http://127.0.0.1:3000`
  - `svc:code` -> `http://127.0.0.1:8080`
  - `svc:codeagent` -> `http://127.0.0.1:4096`
  - `svc:gateway` -> `http://127.0.0.1:4000`
  - `svc:grafana` -> `http://127.0.0.1:3001`
  - `svc:hands` -> `http://127.0.0.1:4031`
  - `svc:search` -> `http://127.0.0.1:8888`
- Additional serve mapping observed: `themini.tailfd1400.ts.net:8123` proxies to `http://192.168.1.40:8123`. Repo docs currently describe Home Assistant on `192.168.1.70:8123`, so this needs human review.

## Storage
- Internal NVMe device: `APPLE SSD AP0256M`, `233.8G`
  - `/boot/efi`: `1.1G vfat`
  - `/`: `227G ext4` on `ubuntu--vg-ubuntu--lv`
- External device: `Portable`, mounted at `/mnt/seagate`
  - Size: `1.9T`
  - Filesystem: `exfat`
- Filesystem utilization snapshot:
  - `/`: `77%` used (`167G` used, `50G` available)
  - `/mnt/seagate`: `9%` used (`166G` used, `1.7T` available)
- Docker volumes relevant to homelab surfaces:
  - `open-terminal-home` -> `/var/lib/docker/volumes/open-terminal-home/_data`
  - `open-terminal-mcp-home` -> `/var/lib/docker/volumes/open-terminal-mcp-home/_data`
  - `open-terminal-mcp-home-test` -> `/var/lib/docker/volumes/open-terminal-mcp-home-test/_data`

## Services
- `litellm-orch.service`
  - State: `active/running`, `enabled`
  - Entry: `/etc/systemd/system/litellm-orch.service`
  - Exec: repo `services/litellm-orch/scripts/run-service.sh`
  - Health: `GET /health/readiness` returned `200` with `status: healthy` and `db: connected`
- `open-webui.service`
  - State: `active/running`, `enabled`
  - Entry: `/etc/systemd/system/open-webui.service`
  - Exec: repo venv `open-webui serve --host 0.0.0.0 --port 3000`
  - Health: `GET /health` returned `200`
- `opencode-web.service`
  - State: `active/running`, `enabled`
  - Entry: `/etc/systemd/system/opencode-web.service`
  - Exec: `opencode web --hostname 0.0.0.0 --port 4096`
  - Health: root returned `401 Unauthorized`, matching its app-layer auth posture
- `openhands.service`
  - State: `active/running`, `enabled`
  - Entry: `/etc/systemd/system/openhands.service`
  - Exec: Docker-managed `openhands-app`
  - Health: UI root returned `200`
- `searxng.service`
  - State: `active/running`, `enabled`
  - Entry: `/etc/systemd/system/searxng.service`
  - Exec: `granian ... --host 127.0.0.1 --port 8888`
  - Health: root returned `200`
- `prometheus.service`
  - State: `active/running`, `enabled`
  - Entry: `/usr/lib/systemd/system/prometheus.service`
  - Health: `GET /-/ready` returned `200`
  - Drift: live listener is `*:9090`, not localhost-only
- `prometheus-node-exporter.service`
  - State: `active/running`, `enabled`
  - Entry: `/usr/lib/systemd/system/prometheus-node-exporter.service`
  - Live listener: `*:9100`
- `grafana-server.service`
  - State: `active/running`, `enabled`
  - Entry: `/usr/lib/systemd/system/grafana-server.service`
  - Health: `GET /api/health` returned `200`
- `ccproxy-api.service`
  - State: `active/running`, `enabled`
  - Entry: `/etc/systemd/system/ccproxy-api.service`
  - Live listener: `127.0.0.1:4010`
- `open-terminal-mcp.service`
  - State: `active/running`, `enabled`
  - Entry: `/etc/systemd/system/open-terminal-mcp.service`
  - Live listener: `127.0.0.1:8011`
- `media-fetch-mcp.service`
  - State: `active/running`, `enabled`
  - Entry: `/etc/systemd/system/media-fetch-mcp.service`
  - Live listener: `127.0.0.1:8012`
- `smbd.service`
  - State: `active/running`, `enabled`
- `nmbd.service`
  - State: `active/running`, `enabled`
- `docker.service`
  - State: `active/running`, `enabled`
- `tailscaled.service`
  - State: `active/running`, `enabled`
- `open-webui-elasticsearch-bridge.service`
  - State: `active/running`, `enabled`
  - Role: SSH tunnel `127.0.0.1:19200 -> studio:9200`
- `orchestration-cockpit-graph.service`
  - State: `active/running`, `disabled`
  - Role: local LangGraph dev server on `127.0.0.1:2024`
- `orchestration-cockpit-ui.service`
  - State: `active/running`, `disabled`
  - Role: local Agent Chat UI on `127.0.0.1:3030`
- `ollama.service`
  - State: `inactive/dead`, `disabled`
  - Health: no listener on `127.0.0.1:11434`
- `ov-server.service`
  - State: `activating/auto-restart`, `enabled`
  - Result: `exit-code`
  - Health: no listener on `127.0.0.1:9000`
- `qwen-agent-proxy.service`
  - State: `failed`, `disabled`
  - Entry: `/etc/systemd/system/qwen-agent-proxy.service`
  - Role: localhost-only shadow sidecar from `experiments/qwen-agent-proxy`

## Containers
- Running containers:
  - `openhands-app`
    - Image: `docker.openhands.dev/openhands/openhands:1.6`
    - Ports: `127.0.0.1:4031->3000/tcp`, `172.17.0.1:4031->3000/tcp`
    - Mounts: `/var/run/docker.sock`, `/home/christopherbailey/.local/share/openhands-phasea -> /.openhands`
  - `open-terminal-mcp`
    - Image: `local/open-terminal-mcp:0.11.29`
    - Ports: `127.0.0.1:8011->8000/tcp`
    - Mounts: repo read-only at `/lab/homelab-llm`, named volume at `/home/user`
  - `open-terminal`
    - Image: `ghcr.io/open-webui/open-terminal`
    - Ports: `127.0.0.1:8010->8000/tcp`
    - Mounts: named volume at `/home/user`, repo read-only at `/home/user/homelab-llm`
- Exited containers still present:
  - `compose-orchestrator-1`
  - `compose-litellm-1`
  - `jerry_litellm`
- Relevant cached images present:
  - `local/open-terminal-mcp:0.11.29`
  - `local/open-terminal-mcp:0.11.29-precloseout`
  - `docker.openhands.dev/openhands/openhands:1.6`
  - `docker.openhands.dev/openhands/openhands:1.5`
  - `ghcr.io/openhands/agent-server:1.15.0-python`
  - `ghcr.io/openhands/agent-server:1.12.0-python`
  - `ghcr.io/open-webui/open-terminal:latest`
  - `ghcr.io/berriai/litellm:main`

## Ports
- Core Mini listeners observed:
  - `0.0.0.0:3000` Open WebUI
  - `0.0.0.0:4000` LiteLLM
  - `127.0.0.1:4010` CCProxy API
  - `127.0.0.1:4031` OpenHands
  - `0.0.0.0:4096` OpenCode Web
  - `127.0.0.1:8010` Open Terminal UI
  - `127.0.0.1:8011` Open Terminal MCP
  - `127.0.0.1:8012` Media Fetch MCP
  - `127.0.0.1:8888` SearXNG
  - `127.0.0.1:3001` Grafana
  - `*:9090` Prometheus
  - `*:9100` node exporter
  - `192.168.1.71:139`, `192.168.1.71:445`, `127.0.0.1:139`, `127.0.0.1:445` Samba
- Tailnet-facing listeners observed:
  - `100.69.99.60:4031`
  - `100.69.99.60:4443`
  - `100.69.99.60:8123`
- Additional non-core or review-needed listeners:
  - `127.0.0.1:2024` orchestration-cockpit graph
  - `127.0.0.1:3030` orchestration-cockpit UI
  - `127.0.0.1:4001` shadow LiteLLM from `homelab-llm-qwen-agent-shadow-20260415`
  - `127.0.0.1:4011` LiteLLM ChatGPT adapter sidecar
  - `127.0.0.1:8080` `code-server`
  - `127.0.0.1:8129` SSH tunnel to Studio `8120`
  - `127.0.0.1:19200` SSH tunnel to Studio `9200`
  - `127.0.0.1:5432` local Postgres
  - `*:22` SSH
  - `*:2049` NFS
- Expected but not present:
  - `127.0.0.1:11434` Ollama
  - `0.0.0.0:9000` OpenVINO

## Repo/worktrees
- Primary repo/worktree: `/home/christopherbailey/homelab-llm`
- Linked worktrees reported by Git:
  - `/home/christopherbailey/homelab-llm-omlx-cache-tier-eval-20260421`
  - `/home/christopherbailey/homelab-llm-omlx-narrow-eval-20260420`
  - `/home/christopherbailey/homelab-llm-omlx-shadow-lane-followup-20260421`
  - `/home/christopherbailey/homelab-llm-searxng-health-audit`
- Process evidence references an additional path not listed by `git worktree list`:
  - `/home/christopherbailey/homelab-llm-qwen-agent-shadow-20260415`
  - This path is associated with the live shadow LiteLLM on `127.0.0.1:4001` and should be reviewed.

## Secrets/env locations, names only
- `services/litellm-orch/config/env.local`
- `/etc/homelab-llm/litellm-voice.env`
- `/etc/open-webui/env`
- `/etc/opencode/env`
- `/etc/openhands/env`
- `/etc/openhands/secret.env`
- `/etc/searxng/env`
- `/etc/default/prometheus`
- `/etc/default/grafana-server`
- `/etc/homelab-llm/ov-server.env`
- `/etc/homelab-llm/ccproxy.env`
- `/etc/homelab-llm/media-fetch-mcp.env`
- `/etc/open-terminal-mcp/env`
- `/etc/orchestration-cockpit/graph.env`
- `/etc/orchestration-cockpit/graph.secret.env`
- `/etc/orchestration-cockpit/ui.env`
- `/etc/homelab-llm/qwen-agent-proxy.env`
- `/etc/homelab-llm/qwen-agent-proxy.secret.env`

## Safe-to-stop candidates
- `orchestration-cockpit-graph.service`
  - Local prototype plane, disabled unit, not part of the boring public gateway baseline.
- `orchestration-cockpit-ui.service`
  - Local prototype plane, disabled unit, not part of the boring public gateway baseline.
- `qwen-agent-proxy.service`
  - Failed and disabled shadow sidecar; fits the V2 retirement posture for stale shadow infrastructure.

## Preserve candidates
- `litellm-orch.service`
- `open-webui.service`
- `searxng.service`
- `prometheus.service`
- `prometheus-node-exporter.service`
- `grafana-server.service`
- `opencode-web.service`
- `openhands.service`
- `open-terminal-mcp.service`
- `media-fetch-mcp.service`
- `smbd.service`
- `nmbd.service`
- `tailscaled.service`
- `docker.service`
- `ccproxy-api.service`
- `open-webui-elasticsearch-bridge.service`

## Unknowns
- Prometheus is documented as localhost-only but is listening on `*:9090`.
- Tailscale Serve maps `themini.tailfd1400.ts.net:8123` to `192.168.1.40:8123`, while repo docs currently describe Home Assistant on `192.168.1.70:8123`.
- The live shadow LiteLLM process on `127.0.0.1:4001` references a path not shown in `git worktree list`.
- `code-server` is running on `127.0.0.1:8080` and served as `svc:code`, but it is outside the requested baseline set and needs owner intent during the rebuild.
- OpenVINO is present in systemd but not healthy enough to count as a working baseline.
- Ollama is installed enough to have a unit file but is inactive and not listening.
- `docs/v2/README.md` is absent; `docs/v2/V2_MIGRATION_NOTES.md` currently acts as the nearest V2 planning entrypoint.

## V2 implications
- One public gateway remains the clean Mini baseline: LiteLLM on `:4000` is the only obvious candidate for the commodity public gateway contract.
- Shadow infrastructure should not be inherited accidentally into V2. The failed `qwen-agent-proxy` and live shadow LiteLLM on `:4001` need explicit preserve-or-retire decisions.
- Tailnet is clearly active for operator access, but the durable runtime baseline remains LAN-first on `192.168.1.71` plus Mini-local listeners.
- Native Open WebUI plus SearXNG is already the live search posture and aligns with the V2 web-search boundary ADR.
- Retrieval-related plumbing is present but should remain candidate status in V2 planning: the Elasticsearch bridge is live, but retrieval doctrine should outrank backend attachment.
- The orchestration cockpit is running but clearly separate from the commodity public baseline; it should remain a distinct plane in any V2 rebuild plan.
- OpenHands is proven as a managed local-bind execution surface and should be evaluated as an execution-plane preserve candidate, not folded into the gateway contract.
- Worktree discipline is materially in use on the Mini, but the off-list shadow path and process are evidence of cleanup debt that V2 should avoid carrying forward.

## Commands run
```bash
sed -n '1,220p' AGENTS.md
sed -n '1,220p' .codex/skills/homelab-durability/SKILL.md
sed -n '1,220p' docs/_core/README.md
sed -n '1,220p' docs/_core/SOURCES_OF_TRUTH.md
sed -n '1,220p' docs/foundation/operating-rhythm.md
find docs/v2 -maxdepth 2 -type f | sort
sed -n '1,240p' docs/v2/V2_MIGRATION_NOTES.md
for f in docs/v2/adr/*.md; do sed -n '1,140p' "$f"; done
sed -n '1,260p' docs/foundation/topology.md
sed -n '1,260p' docs/PLATFORM_DOSSIER.md
sed -n '1,260p' docs/INTEGRATIONS.md
sed -n '1,220p' NOW.md
sed -n '1,260p' docs/_core/CHANGE_RULES.md
find docs -path '*/AGENTS.md' | sort
hostnamectl
uname -srmo
lscpu
free -h
lsblk -e7 -o NAME,SIZE,FSTYPE,TYPE,MOUNTPOINTS,MODEL
findmnt -R -o TARGET,SOURCE,FSTYPE,SIZE,USED,AVAIL,OPTIONS
df -hT -x tmpfs -x devtmpfs
ip -brief addr
tailscale status --json
tailscale serve status --json
ss -ltnup
systemctl --no-pager --full --type=service --state=running
systemctl show <relevant services> -p Id -p ActiveState -p SubState -p Result -p EnvironmentFiles -p ExecStart ...
curl -sS --max-time 5 http://127.0.0.1:4000/health/readiness
curl -sS --max-time 5 http://127.0.0.1:3000/health
curl -sS --max-time 5 http://127.0.0.1:4096/
curl -sS --max-time 5 http://127.0.0.1:4031/
curl -sS --max-time 5 http://127.0.0.1:8888/
curl -sS --max-time 5 http://127.0.0.1:9090/-/ready
curl -sS --max-time 5 http://127.0.0.1:3001/api/health
curl -sS --max-time 5 http://127.0.0.1:11434/
curl -sS --max-time 5 http://127.0.0.1:9000/health
docker ps -a --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'
docker images --format 'table {{.Repository}}\t{{.Tag}}\t{{.ID}}\t{{.Size}}'
docker volume ls
docker inspect openhands-app open-terminal open-terminal-mcp --format ...
docker volume inspect open-terminal-home open-terminal-mcp-home open-terminal-mcp-home-test --format ...
git worktree list --porcelain
git rev-parse --show-toplevel
git status --short --branch
ps -fp <relevant pids>
rg -n 'docs/v2/inventory|MINI_BASELINE|baseline inventory' docs/v2 docs -g '!docs/journal/**'
```

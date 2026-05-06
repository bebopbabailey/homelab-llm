# V2 Planning Material: Studio Baseline Inventory

Not current runtime truth. This is a read-only planning snapshot for V2 rebuild work.

Snapshot gathered from repo docs plus read-only `ssh studio` inspection on `2026-05-06 UTC`.

## Summary

- Studio baseline host is a `Mac15,14` Mac Studio with `Apple M3 Ultra`, `256 GB` RAM, and macOS `26.2` (`25C56`). Observed via: `ssh studio '... sw_vers ... system_profiler SPHardwareDataType ...'`
- Main APFS volume has about `3.3 TiB` free. Observed via: `ssh studio '... df -h / /System/Volumes/Data /Volumes/* ...'`
- Active runtime listeners observed on Studio were `8126` (`llmster`), `4020` (OptiLLM proxy), `8120` (oMLX localhost eval), `9200` (Elasticsearch), `55432` (Postgres), `55440` (memory API), and `5601` (Kibana). Observed via: `ssh studio '... lsof -nP -iTCP -sTCP:LISTEN ...'`
- Vector and memory services are live in practice: Elasticsearch `9.3.3` was healthy on `127.0.0.1:9200`, and the memory API reported backend `elastic` with `native_rrf_enabled=true`. Observed via: `ssh studio '... curl -fsS http://127.0.0.1:9200 ... curl -fsS http://127.0.0.1:55440/health ...'`
- Host-local model storage is split across LM Studio / GGUF (`~/.lmstudio` about `72G`) and MLX/Hugging Face (`~/models` about `85G`, `~/.cache/huggingface` about `12G`). Observed via: `ssh studio '... du -sh ~/.cache/huggingface ~/.lmstudio ~/models ...'`
- Repo canon and live host state currently diverge on MLX lanes: repo docs still describe `8101` as active, but this inventory pass observed no `8101` listener, a disabled `com.bebop.mlx-lane.8101`, and a host-local MLX registry showing null/down lane state. Repo canon: `docs/foundation/topology.md`, `docs/PLATFORM_DOSSIER.md`, `docs/foundation/mlx-registry.md`. Observed via: `ssh studio '... launchctl print-disabled system ...'`, `ssh studio '... lsof -nP -iTCP:8100-8109 ...'`, `ssh studio '... sed -n "1,120p" /Users/thestudio/models/hf/hub/registry.json ...'`
- `mlxctl` is installed on Studio but unusable from the default shell because it expects a repo root containing `/platform/registry/services.jsonl`. Observed via: `ssh studio '... mlxctl --help ... mlxctl status --json ...'`
- The baseline preserves strong evidence for three V2-relevant runtime families on Studio: GPT/GGUF via `llmster`, specialized runtime via local `oMLX` on `8120`, and Elastic-backed retrieval via `9200` + `55440`.

## Host identity

- Computer name: `Ryan’s Mac Studio (3)`. Observed via: `ssh studio 'scutil --get ComputerName ...'`
- Local host name: `thestudio-5`. Observed via: `ssh studio 'scutil --get LocalHostName ...'`
- Hostname: `thestudio-5.local`. Observed via: `ssh studio 'hostname ...'`
- Model: `Mac Studio`, identifier `Mac15,14`, model number `Z1CE000Y2LL/A`. Observed via: `ssh studio 'system_profiler SPHardwareDataType ...'`
- Chip: `Apple M3 Ultra`. Observed via: `ssh studio 'system_profiler SPHardwareDataType ... sysctl machdep.cpu.brand_string ...'`
- CPU cores: `32` total (`24` performance, `8` efficiency). Observed via: `ssh studio 'system_profiler SPHardwareDataType ... sysctl hw.logicalcpu hw.physicalcpu ...'`
- RAM: `256 GB` (`274877906944` bytes). Observed via: `ssh studio 'system_profiler SPHardwareDataType ... sysctl hw.memsize ...'`
- System firmware version: `13822.61.10`. Observed via: `ssh studio 'system_profiler SPHardwareDataType ...'`
- Sensitive identifiers were present in `system_profiler` output, but serial number, UUID, and provisioning UDID are intentionally omitted from this planning doc.

## Network

- Primary active interface observed: `en0`. Observed via: `ssh studio '... ifconfig en0 ...'`
- LAN IPv4: `192.168.1.72`. Observed via: `ssh studio 'ipconfig getifaddr en0 ... ifconfig en0 ...'`
- Default gateway: `192.168.1.254`. Observed via: `ssh studio 'route -n get default ...'`
- Link posture: `10Gbase-T` full duplex with `status: active`. Observed via: `ssh studio 'ifconfig en0 ...'`
- IPv6 addresses are present on `en0`, but this inventory does not treat the temporary IPv6 set as planning truth. Observed via: `ssh studio 'ifconfig en0 ...'`
- Repo canon still treats the Studio LAN IP as the Mini -> Studio runtime path. Repo canon: `docs/foundation/topology.md`, `docs/PLATFORM_DOSSIER.md`

## Storage

- Root volume `/`: `3.6Ti` total, about `11Gi` used, about `3.3Ti` free. Observed via: `ssh studio 'df -h / ...'`
- Data volume `/System/Volumes/Data`: `3.6Ti` total, about `328Gi` used, about `3.3Ti` free. Observed via: `ssh studio 'df -h /System/Volumes/Data ...'`
- `/Volumes/Macintosh HD` was present in the probed volume list, but this snapshot did not identify it as a distinct runtime data surface. Observed via: `ssh studio '... for d in ... /Volumes/* ...'`
- `~/.lmstudio` is about `72G`. Observed via: `ssh studio 'du -sh ~/.lmstudio ...'`
- `~/models` is about `85G`. Observed via: `ssh studio 'du -sh ~/models ...'`
- `~/.cache/huggingface` is about `12G`. Observed via: `ssh studio 'du -sh ~/.cache/huggingface ...'`

## Memory/runtime tuning

- `memory_pressure` reported `System-wide memory free percentage: 70%`. Observed via: `ssh studio 'memory_pressure ...'`
- Pages wired down were about `4,933,472` pages. Observed via: `ssh studio 'memory_pressure ... vm_stat ...'`
- Swap was effectively idle: `total = 1024.00M`, `used = 1.00M`, `free = 1023.00M`. Observed via: `ssh studio 'sysctl vm.swapusage ...'`
- Compressor is active but lightly used: `vm.compressor.is_active = 1`, `vm.compressor.pages_compressed = 1605`. Observed via: `ssh studio 'sysctl -a | egrep "iogpu|swap|compressor|memorystatus|wire" ...'`
- Memory pressure signal `kern.memorystatus_level = 70` was readable. Observed via: `ssh studio 'sysctl -a | egrep "iogpu|swap|compressor|memorystatus|wire" ...'`
- Readable GPU/wired signals:
  - `iogpu.dynamic_lwm = 1`
  - `iogpu.wired_limit_mb = 241644`
  - `debug.iogpu.wired_lwm_mb = 0`
  - `vm.global_user_wire_limit = 261134011596`
  Observed via: `ssh studio 'sysctl -a | egrep "iogpu|swap|compressor|memorystatus|wire" ...'`
- These are observed tuning signals only. This inventory does not interpret them as validated V2 tuning doctrine.

## Launchd services

### Observed running / enabled core services

- `com.bebop.optillm-proxy` was running with program `/Users/thestudio/optillm-proxy/.venv/bin/optillm` and PID `94350`. Observed via: `ssh studio 'launchctl print system/com.bebop.optillm-proxy ...'`
- `com.bebop.elasticsearch-memory-main` was running with Elasticsearch under `/Users/thestudio/optillm-proxy/layer-data/vector-db/runtime/elasticsearch-current/bin/elasticsearch`. Observed via: `ssh studio 'launchctl print system/com.bebop.elasticsearch-memory-main ...'`
- `com.bebop.memory-api-main` was running from `/Users/thestudio/optillm-proxy/layer-data/vector-db/.venv/bin/python` with PID `33632`. Observed via: `ssh studio 'launchctl print system/com.bebop.memory-api-main ...'`
- `com.bebop.docs-mcp-main` was running from `/Users/thestudio/optillm-proxy/layer-tools/docs-mcp/.venv/bin/python` with PID `65299`. Observed via: `ssh studio 'launchctl print system/com.bebop.docs-mcp-main ...'`
- `com.bebop.pgvector-main` was running from `/opt/homebrew/opt/postgresql@16/bin/postgres` with PID `1415`. Observed via: `ssh studio 'launchctl print system/com.bebop.pgvector-main ...'`

### Observed disabled / retired / parked labels

- Retired shadow labels remained disabled: `com.bebop.mlx-shadow.8123`, `com.bebop.mlx-shadow.8124`, `com.bebop.mlx-shadow.8125`. Observed via: `ssh studio 'launchctl print-disabled system ...'`
- Disabled MLX lane labels observed included `8103-8119` except for the explicitly enabled `8100` and `8102`. Observed via: `ssh studio 'launchctl print-disabled system ...'`
- Disabled non-core / legacy labels observed:
  - `com.bebop.optillm-local-balanced`
  - `com.bebop.optillm-local-high`
  - `com.bebop.optillm-proxy-deep`
  - `com.bebop.mlx-omni.8100`
  - `com.bebop.mlx-omni.8120`
  - `com.bebop.llama-router.8100`
  - `com.bebop.mlx-launch`
  - `com.deploy.mlx.server`
  Observed via: `ssh studio 'launchctl print-disabled system ...'`

### Observed mismatches needing review

- `com.bebop.mlx-lane.8101` was disabled and no `8101` listener was observed, even though repo canon still describes `8101` as the active MLX lane. Repo canon: `docs/foundation/topology.md`, `docs/PLATFORM_DOSSIER.md`. Observed via: `ssh studio 'launchctl print-disabled system ...'`, `ssh studio 'lsof -nP -iTCP:8100-8109 ...'`
- `com.bebop.mlx-lane.8100` and `com.bebop.mlx-lane.8102` were `spawn scheduled` with `last exit code = 1`. Observed via: `ssh studio 'launchctl print system/com.bebop.mlx-lane.8100 ... com.bebop.mlx-lane.8102 ...'`
- `com.bebop.llmster-gpt.8126` showed `state = not running` in `launchctl print`, but a live `llmster` process and a `192.168.1.72:8126` listener were observed. Observed via: `ssh studio 'launchctl print system/com.bebop.llmster-gpt.8126 ...'`, `ssh studio 'lsof -nP -iTCP -sTCP:LISTEN ...'`
- `com.bebop.docs-mcp-main` had a running launchd job, but no `8013` listener was observed during this pass. Repo canon expects `8013`. Repo canon: `docs/foundation/topology.md`, `docs/PLATFORM_DOSSIER.md`. Observed via: `ssh studio 'launchctl print system/com.bebop.docs-mcp-main ...'`, `ssh studio 'lsof -nP -iTCP:8013 -sTCP:LISTEN ...'`

## Model/runtime directories

### Observed runtime roots

- `~/models`
- `~/.lmstudio`
- `~/.cache/huggingface`
- `~/optillm-proxy`
- `~/models/omlx-eval`
Observed via: `ssh studio '... for d in ~/.cache/mlx ~/.cache/huggingface ~/Library/Application Support/LM Studio ~/.lmstudio ~/models /Volumes/* ...'`, `ssh studio 'find /Users/thestudio/models ...'`

### Approximate sizes

- `~/models`: about `85G`
- `~/.lmstudio`: about `72G`
- `~/.cache/huggingface`: about `12G`
- `~/models/hf`: about `83G`
- `~/models/omlx-eval`: about `2.1G`
Observed via: `ssh studio 'du -sh ~/.cache/huggingface ~/.lmstudio ~/models ...'`, `ssh studio 'find /Users/thestudio/models ... | xargs du -sh ...'`

### High-level contents

- MLX / HF tree under `~/models/hf` included:
  - `LibraxisAI/Qwen3-Next-80B-A3B-Instruct-MLX-MXFP4` about `39G`
  - `mlx-community/Qwen3-Coder-Next-4bit` about `42G`
  - `mlx-community/Qwen3-0.6B-4bit` about `335M`
  - `mlx-community/Qwen3-0.6B-bf16` about `1.1G`
  Observed via: `ssh studio 'find /Users/thestudio/models ...'`
- LM Studio / `llmster` model tree under `~/.lmstudio/models` included:
  - `ggml-org/gpt-oss-20b-GGUF` about `11G`
  - `lmstudio-community/gpt-oss-120b-GGUF` about `59G`
  Observed via: `ssh studio 'find /Users/thestudio/.lmstudio/models ... | xargs du -sh ...'`
- HF cache also held embedding and reranker artifacts, including:
  - `nomic-ai/nomic-embed-text-v1.5` about `523M`
  - `mixedbread-ai/mxbai-embed-large-v1` about `640M`
  - `Qwen/Qwen3-Embedding-0.6B` about `1.1G`
  - `cross-encoder/ms-marco-MiniLM-L-6-v2` about `88M`
  Observed via: `ssh studio 'find /Users/thestudio/.cache/huggingface ... | xargs du -sh ...'`
- `.lmstudio` contained runtime and state roots for `llmster`, extensions/backends, server logs, conversations, projects, and retrieval-session caches. Observed via: `ssh studio 'find /Users/thestudio/.lmstudio -maxdepth 2 ...'`

## Ports

### Observed listeners

- `192.168.1.72:8126` by `llmster`
- `127.0.0.1:41343` by `llmster` helper
- `192.168.1.72:4020` by OptiLLM proxy
- `127.0.0.1:8120` by `omlx serve`
- `127.0.0.1:9200` by Elasticsearch
- `127.0.0.1:9300` by Elasticsearch transport
- `127.0.0.1:55432` by Postgres / pgvector
- `*:55440` by memory API
- `127.0.0.1:5601` by Kibana
Observed via: `ssh studio 'lsof -nP -iTCP -sTCP:LISTEN ...'`

### Expected by repo canon but not observed during this pass

- `192.168.1.72:8101`
- `192.168.1.72:8013`
Repo canon: `docs/foundation/topology.md`, `docs/PLATFORM_DOSSIER.md`. Observed via: `ssh studio 'lsof -nP -iTCP:8100-8109 ...'`, `ssh studio 'lsof -nP -iTCP:8013 -sTCP:LISTEN ...'`

## Registries

- Repo canonical registry surfaces remain:
  - `platform/registry/services.jsonl`
  - Studio governance docs in `docs/foundation/mlx-registry.md` and `docs/foundation/studio-scheduling-policy.md`
- Host-local observed registry file: `/Users/thestudio/models/hf/hub/registry.json` (`18K`, modified `2026-04-19`). Observed via: `ssh studio 'ls -lh /Users/thestudio/models/hf/hub/registry.json ...'`
- Host-local registry format:
  - `version: 2`
  - model entries included `mlx-qwen3-coder-next-6bit` and `mlx-qwen3-coder-next-4bit`
  - lane map showed `8100`, `8101`, and `8102` with `desired_target = null`, `actual_serving_target = null`, and `health_state = down`
  Observed via: `ssh studio 'sed -n "1,120p" /Users/thestudio/models/hf/hub/registry.json ...'`
- `mlxctl` is installed at `/usr/local/bin/mlxctl`, but default-shell execution failed because it expected `/platform/registry/services.jsonl` and no matching repo clone was found at the probed home-directory depth. Observed via: `ssh studio 'command -v mlxctl ... mlxctl --help ...'`, `ssh studio 'find ~ -maxdepth 4 -path "*/platform/registry/services.jsonl" ...'`
- The only repo-like root directly observed during the shallow search was `/Users/thestudio/optillm-proxy/AGENTS.md`. Observed via: `ssh studio 'find ~ -maxdepth 3 -name AGENTS.md ...'`

## Vector/memory services

- Elasticsearch was listening on `127.0.0.1:9200` and identified itself as cluster `memory-main`, node `studio-memory-main`, version `9.3.3`. Observed via: `ssh studio 'curl -fsS http://127.0.0.1:9200 ...'`
- Memory API on `55440` returned `{"service":"studio-memory-api","ok":true,"backend":"elastic",...}`. Observed via: `ssh studio 'curl -fsS http://127.0.0.1:55440/health ...'`
- Memory API health also reported:
  - `native_rrf_capable = true`
  - `native_rrf_enabled = true`
  - `embedding_model = "studio-nomic-embed-text-v1.5"`
  - `embedding_dims = 768`
  - `embedding_prefix_mode = "search_query/search_document"`
  Observed via: `ssh studio 'curl -fsS http://127.0.0.1:55440/health ...'`
- Postgres / pgvector remained present on `127.0.0.1:55432`. Observed via: `ssh studio 'lsof -nP -iTCP:55432 ...'`
- Kibana also had a host-local listener on `127.0.0.1:5601`. Observed via: `ssh studio 'lsof -nP -iTCP -sTCP:LISTEN ...'`
- Repo canon emphasizes Elastic + memory API as the live retrieval path, but pgvector is still running and should be treated as present baseline inventory, not assumed dead. Repo canon: `docs/PLATFORM_DOSSIER.md`, `docs/INTEGRATIONS.md`

## Safe-to-stop candidates

- The strongest safe-to-leave-stopped set is the already disabled shadow infrastructure:
  - `com.bebop.mlx-shadow.8123`
  - `com.bebop.mlx-shadow.8124`
  - `com.bebop.mlx-shadow.8125`
  Observed via: `ssh studio 'launchctl print-disabled system ...'`
- Additional likely safe-to-leave-stopped labels for V2 phase-one planning:
  - disabled MLX lanes `8103-8119`
  - `com.bebop.optillm-local-balanced`
  - `com.bebop.optillm-local-high`
  - `com.bebop.optillm-proxy-deep`
  - `com.bebop.mlx-omni.8100`
  - `com.bebop.mlx-omni.8120`
  - `com.bebop.llama-router.8100`
  - `com.bebop.mlx-launch`
  Observed via: `ssh studio 'launchctl print-disabled system ...'`
- This section is inventory only. It is not an instruction to mutate or stop anything.

## Preserve candidates

- `llmster` GPT runtime on `8126` should be preserved as concrete evidence of the incumbent GPT/GGUF compatibility path. Observed via: `ssh studio 'lsof -nP -iTCP -sTCP:LISTEN ... ps aux | egrep "llmster" ...'`
- OptiLLM proxy on `4020` should be preserved as extant Studio-side runtime evidence even though it is not current public V2 doctrine. Observed via: `ssh studio 'launchctl print system/com.bebop.optillm-proxy ... lsof -nP -iTCP -sTCP:LISTEN ...'`
- Local oMLX runtime on `127.0.0.1:8120` should be preserved as specialized-runtime evidence. Observed via: `ssh studio 'ps aux | egrep "omlx" ... lsof -nP -iTCP -sTCP:LISTEN ...'`
- Elastic + memory API should be preserved as the currently live retrieval baseline. Observed via: `ssh studio 'curl -fsS http://127.0.0.1:9200 ... curl -fsS http://127.0.0.1:55440/health ...'`
- Postgres / pgvector presence should be preserved as baseline evidence until a human decides whether it is still needed. Observed via: `ssh studio 'launchctl print system/com.bebop.pgvector-main ... lsof -nP -iTCP:55432 ...'`
- `docs-mcp-main` launchd presence should be preserved as a candidate V2 planning signal even though its listener was not observed during this pass. Observed via: `ssh studio 'launchctl print system/com.bebop.docs-mcp-main ...'`
- Large GGUF and MLX model stores should be preserved before any future cleanup:
  - `~/.lmstudio/models/ggml-org/gpt-oss-20b-GGUF`
  - `~/.lmstudio/models/lmstudio-community/gpt-oss-120b-GGUF`
  - `~/models/hf/models--LibraxisAI--Qwen3-Next-80B-A3B-Instruct-MLX-MXFP4`
  - `~/models/hf/models--mlx-community--Qwen3-Coder-Next-4bit`
  Observed via: `ssh studio 'find /Users/thestudio/.lmstudio/models ...'`, `ssh studio 'find /Users/thestudio/models ...'`

## Unknowns

- Requested input file `docs/v2/README.md` does not exist in the repo. Observed via: `sed -n '1,220p' docs/v2/README.md`
- Repo canon still describes `8101` as the active MLX lane, but this pass observed no `8101` listener, a disabled `com.bebop.mlx-lane.8101`, and a host-local registry showing MLX lanes down/null. This needs human review before any V2 rebuild assumes MLX lane continuity. Repo canon: `docs/foundation/topology.md`, `docs/PLATFORM_DOSSIER.md`, `docs/foundation/mlx-registry.md`
- `mlxctl` is installed but unusable from the default Studio shell because it expects a repo root containing `/platform/registry/services.jsonl`. That could mean the canonical Studio repo checkout is absent, elsewhere, or no longer the operator path. Observed via: `ssh studio 'mlxctl --help ... mlxctl status --json ...'`, `ssh studio 'find ~ -maxdepth 4 -path "*/platform/registry/services.jsonl" ...'`
- `com.bebop.llmster-gpt.8126` launchd state conflicts with the observed live process/listener. Human review is needed to determine whether launchd state reporting, process ancestry, or plist posture is the trustworthy operational signal.
- `com.bebop.docs-mcp-main` had a running launchd job but no `8013` listener was observed. Human review is needed before treating Docs MCP as live or retired.
- Exact keep-or-retire posture for `pgvector` and `Kibana` is unresolved. Both were present, but late-V1 repo canon leans more heavily on Elastic + memory API than on pgvector or Kibana as active V2-shaping surfaces.
- Exact ownership and intended future of the host-local `~/optillm-proxy` tree needs human review. It currently contains the OptiLLM proxy, vector DB runtime, Docs MCP runtime, and related venvs.

## V2 implications

- V2 Studio planning should assume the incumbent GPT/GGUF compatibility path still matters on this host because `llmster` on `8126` is concretely present.
- V2 should not assume the MLX team-lane domain is currently alive just because repo canon still documents it that way.
- Specialized-runtime evidence exists locally via `oMLX` on `127.0.0.1:8120`, but it remains a private/local path rather than a public gateway contract.
- Retrieval on Studio is Elastic-backed in practice today, with Postgres / pgvector still present as a likely legacy or contingency surface.
- V2 rebuild planning should include an explicit host-canon reconciliation step before treating current Studio docs as fully live truth.
- Studio model inventory suggests two runtime families still need first-class accounting in V2 planning:
  - GGUF / LM Studio / `llmster`
  - MLX / HF cache / local `oMLX`
- Preserve labels, logs, and data paths before any future cleanup pass; the host still carries evidence from multiple V1 runtime directions.
- Disabled shadow and legacy labels already provide a conservative starting set for “leave stopped / keep retired” decisions.
- The `docs-mcp-main` and `8101` mismatches should be resolved by human review before V2 phase-one scope assumes either is live.
- The absence of `docs/v2/README.md` suggests V2 top-level navigation is still incomplete and should not be assumed to exist in future planning tasks.

## Commands run

- `sed -n '1,220p' /home/christopherbailey/homelab-llm/.codex/skills/homelab-durability/SKILL.md`
- `sed -n '1,220p' AGENTS.md`
- `for f in docs/v2/README.md docs/foundation/topology.md docs/PLATFORM_DOSSIER.md docs/foundation/mlx-registry.md docs/foundation/studio-scheduling-policy.md docs/INTEGRATIONS.md; do echo "FILE: $f"; sed -n '1,220p' "$f"; echo; done`
- `find docs/v2/adr -maxdepth 1 -type f | sort | xargs -I{} sh -c 'echo FILE: {}; sed -n "1,200p" "{}"; echo'`
- `find docs/v2 -maxdepth 2 -type f | sort`
- `test -e docs/v2/inventory/STUDIO_BASELINE.md && echo present || echo missing`
- `git status --short`
- `ssh studio 'printf "## sw_vers\n"; sw_vers; printf "\n## hardware\n"; system_profiler SPHardwareDataType | sed -n "1,80p"; printf "\n## storage\n"; df -h / /System/Volumes/Data /Volumes/* 2>/dev/null; printf "\n## memory_pressure\n"; memory_pressure 2>/dev/null | sed -n "1,80p"; printf "\n## vm_stat\n"; vm_stat | sed -n "1,40p"; printf "\n## swap\n"; sysctl vm.swapusage; printf "\n## sysctl mem\n"; sysctl hw.memsize hw.logicalcpu hw.physicalcpu machdep.cpu.brand_string 2>/dev/null'`
- `ssh studio 'printf "## ports\n"; lsof -nP -iTCP -sTCP:LISTEN 2>/dev/null | sed -n "1,200p"; printf "\n## launchd owned labels\n"; launchctl list | egrep "com\.bebop|com\.deploy|llmster|optillm|memory|elastic|docs-mcp|omlx" | sed -n "1,200p"; printf "\n## disabled owned labels\n"; launchctl print-disabled system 2>/dev/null | egrep "com\.bebop|com\.deploy" | sed -n "1,120p"'`
- `ssh studio 'printf "## tools\n"; for x in mlxctl llmster lms llamactl llama-server llama-cli python3 uv conda; do printf "%s: " "$x"; command -v "$x" || true; done; printf "\n## runtime processes\n"; ps aux | egrep "mlx-openai|vllm|llmster|optillm|omlx|LM Studio|llama.cpp|llama-server|memory-api|elasticsearch|docs-mcp" | egrep -v "egrep" | sed -n "1,200p"; printf "\n## mlxctl status\n"; mlxctl status --table 2>/dev/null | sed -n "1,120p"; printf "\n## lms ps\n"; lms ps --json 2>/dev/null | sed -n "1,160p"'`
- `ssh studio 'printf "## candidate model dirs\n"; for d in ~/.cache/mlx ~/.cache/huggingface ~/Library/Application\ Support/LM\ Studio ~/.lmstudio ~/models /Volumes/*; do [ -e "$d" ] && printf "%s\n" "$d"; done; printf "\n## sized model dirs\n"; for d in ~/.cache/mlx ~/.cache/huggingface ~/.lmstudio ~/Library/Application\ Support/LM\ Studio ~/models; do [ -e "$d" ] && du -sh "$d" 2>/dev/null; done; printf "\n## registry candidates\n"; find ~ -maxdepth 4 \( -name "registry.json" -o -name "registry*.json" -o -name "*.jsonl" \) 2>/dev/null | egrep "mlx|registry|model" | sed -n "1,200p"'`
- `ssh studio 'printf "## python env markers\n"; find ~ -maxdepth 3 \( -name pyvenv.cfg -o -name conda-meta -o -name environment.yml -o -name uv.lock \) 2>/dev/null | sed -n "1,200p"; printf "\n## vector memory probes\n"; lsof -nP -iTCP:9200 -iTCP:55432 -iTCP:55440 -sTCP:LISTEN 2>/dev/null; printf "\n## health probes\n"; curl -fsS http://127.0.0.1:9200 2>/dev/null | sed -n "1,40p"; printf "\n---\n"; curl -fsS http://127.0.0.1:55440/health 2>/dev/null | sed -n "1,40p"; printf "\n## launchd vector labels\n"; launchctl list | egrep "elasticsearch|memory-api|memory-ingest|memory-backup|docs-mcp" | sed -n "1,120p"'`
- `ssh studio 'printf "## network\n"; scutil --get ComputerName 2>/dev/null; scutil --get LocalHostName 2>/dev/null; hostname; ipconfig getifaddr en0 2>/dev/null; ifconfig en0 | sed -n "1,20p"; printf "\n## route\n"; route -n get default 2>/dev/null | sed -n "1,20p"'`
- `ssh studio 'printf "## label details\n"; for label in com.bebop.llmster-gpt.8126 com.bebop.optillm-proxy com.bebop.elasticsearch-memory-main com.bebop.memory-api-main com.bebop.docs-mcp-main com.bebop.pgvector-main com.bebop.mlx-lane.8100 com.bebop.mlx-lane.8101 com.bebop.mlx-lane.8102; do echo "LABEL: $label"; launchctl print system/$label 2>/dev/null | egrep "state =|path =|program =|last exit code|pid =" | sed -n "1,20p"; echo; done'`
- `ssh studio 'printf "## model tree\n"; find /Users/thestudio/models -maxdepth 2 -mindepth 1 -type d | sort | sed -n "1,120p"; printf "\n## model sizes\n"; find /Users/thestudio/models -maxdepth 2 -mindepth 1 -type d -print0 | xargs -0 du -sh 2>/dev/null | sort -h | sed -n "1,120p"; printf "\n## lmstudio top dirs\n"; find /Users/thestudio/.lmstudio -maxdepth 2 -mindepth 1 -type d | sort | sed -n "1,120p"'`
- `ssh studio 'printf "## registry file\n"; ls -lh /Users/thestudio/models/hf/hub/registry.json 2>/dev/null; printf "\n## registry head\n"; sed -n "1,120p" /Users/thestudio/models/hf/hub/registry.json 2>/dev/null; printf "\n## memory tuning search\n"; sysctl -a 2>/dev/null | egrep "iogpu|swap|compressor|memorystatus|wire" | sed -n "1,120p"'`
- `ssh studio 'printf "## mlxctl help\n"; mlxctl --help 2>&1 | sed -n "1,120p"; printf "\n## mlxctl status json\n"; mlxctl status --json 2>&1 | sed -n "1,120p"'`
- `ssh studio 'printf "## repo clones with services registry\n"; find ~ -maxdepth 4 -path "*/platform/registry/services.jsonl" 2>/dev/null | sed -n "1,40p"; printf "\n## repo clones with AGENTS\n"; find ~ -maxdepth 3 -name AGENTS.md 2>/dev/null | egrep "homelab-llm|optillm-proxy" | sed -n "1,40p"'`
- `ssh studio 'printf "## lmstudio model sizes\n"; find /Users/thestudio/.lmstudio/models -maxdepth 2 -mindepth 1 -type d -print0 2>/dev/null | xargs -0 du -sh 2>/dev/null | sort -h | sed -n "1,120p"; printf "\n## huggingface cache top\n"; find /Users/thestudio/.cache/huggingface -maxdepth 2 -mindepth 1 -type d -print0 2>/dev/null | xargs -0 du -sh 2>/dev/null | sort -h | sed -n "1,120p"'`
- `ssh studio 'printf "## safe stop candidates evidence\n"; launchctl print-disabled system 2>/dev/null | egrep "com\.bebop\.(mlx-shadow\.812[345]|mlx-lane\.810[3-9]|mlx-lane\.811[0-9]|optillm-local|optillm-proxy-deep|mlx-launch|llama-router\.8100|mlx-omni)" | sed -n "1,120p"'`
- `find docs/v2 -maxdepth 2 -type d | sort`
- `ssh studio 'printf "## docs mcp port\n"; lsof -nP -iTCP:8013 -sTCP:LISTEN 2>/dev/null; printf "\n## 810x ports\n"; lsof -nP -iTCP:8100-8109 -sTCP:LISTEN 2>/dev/null'`

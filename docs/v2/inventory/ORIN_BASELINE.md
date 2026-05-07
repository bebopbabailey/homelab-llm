# V2 Planning Material: Orin Baseline Inventory

Not current runtime truth. This is a read-only planning snapshot for V2 rebuild work.

Snapshot gathered from repo docs plus read-only `ssh orin` inspection on `2026-05-07 UTC`.

## Summary

- Orin baseline host is `theorin`, an `NVIDIA Jetson AGX Orin Developer Kit` on Ubuntu `22.04.5 LTS` with L4T `R36.4.7`. Observed via: `ssh orin 'hostnamectl ... cat /etc/os-release ... cat /etc/nv_tegra_release ...'`
- Orin has `12` ARM CPU cores, about `61 GiB` RAM, about `30 GiB` swap, local root on `57.8G` eMMC, and a separate `1.8T` NVMe mounted at `/srv/ssd`. Observed via: `ssh orin 'lscpu ... free -h ... df -h ... lsblk ...'`
- Primary LAN IP is `192.168.1.93`; Tailscale is also active on `100.122.226.93`. Observed via: `ssh orin 'hostname -I ... ip -brief addr ...'`
- Live speech surfaces are present in practice: `voice-gateway.service` on `192.168.1.93:18080`, `voice-gateway-native-stt.service`, and `speaches.service` with localhost `127.0.0.1:8000`. Observed via: `ssh orin 'ss -ltnp ... systemctl list-units ...'`
- Docker is active and currently runs one `speaches` container with `127.0.0.1:8000->8000/tcp`. Observed via: `ssh orin 'docker ps -a --format ...'`
- `/mnt/seagate` remains an Orin offload path sourced from Mini, but this pass observed it through `autofs` rather than a fully mounted remote filesystem. Observed via: `ssh orin 'findmnt /mnt/seagate -R ...'`
- Audio hardware is substantial and includes a `Shure MV51` USB microphone, which matters for speech-host planning. Observed via: `ssh orin 'arecord -l; aplay -l'`

## Host identity

- Hostname: `theorin`
- SSH alias / operator path: `ssh orin`
- OS: `Ubuntu 22.04.5 LTS`
- Kernel: `Linux 5.15.148-tegra`
- Architecture: `arm64`
- Hardware vendor: `NVIDIA`
- Hardware model: `NVIDIA Jetson AGX Orin Developer Kit`
- L4T release: `R36 (release), REVISION: 4.7`
Observed via: `ssh orin 'hostnamectl ... cat /etc/os-release ... cat /etc/nv_tegra_release ... uname -a'`

## Network

- Primary LAN interface: `eno1`
- Primary LAN IPv4: `192.168.1.93/24`
- Tailscale interface: `tailscale0`
- Tailscale IPv4: `100.122.226.93/32`
- Docker bridge present: `docker0` on `172.17.0.1/16`
- Default gateway: `192.168.1.254`
Observed via: `ssh orin 'hostname -I ... ip -brief addr ... ip route ...'`

## Storage

- Root filesystem: `/dev/mmcblk0p1`, about `54G` total, `23G` used, `29G` available
- EFI partition: `/dev/mmcblk0p10`, `64M`, mounted at `/boot/efi`
- NVMe data disk: `nvme0n1p1`, about `1.8T`, mounted at `/srv/ssd`
- Offload mount path: `/mnt/seagate`
- Observed `/mnt/seagate` source during this pass: `systemd-1 autofs`
Observed via: `ssh orin 'df -h / /home /mnt/seagate ... lsblk ... findmnt /mnt/seagate -R ...'`

## Memory/runtime tuning

- RAM: about `61 GiB`
- Memory in use at snapshot: about `3.6 GiB`
- Free memory at snapshot: about `54 GiB`
- Swap: about `30 GiB`, with `0B` used
- zram devices present: `zram0` through `zram11`
Observed via: `ssh orin 'free -h ... lsblk ...'`

## Services

- `voice-gateway.service`
  - State: `active/running`
  - Role: speech facade on the Orin host
- `voice-gateway-native-stt.service`
  - State: `active/running`
  - Role: native STT wrapper behind the facade
- `speaches.service`
  - State: `active/running`
  - Role: speech backend container
- `docker.service`
  - State: `active/running`
- `containerd.service`
  - State: `active/running`
- `tailscaled.service`
  - State: `active/running`
- `ssh.service`
  - State: `active/running`
Observed via: `ssh orin 'systemctl list-units --type=service --all --no-pager | egrep -i "voice|docker|containerd|tailscale|ssh|speaches|tts|asr"'`

## Containers

- Running container:
  - `speaches`
    - Image: `speaches:orin-local-a811659-cuda`
    - Status: `Up 2 weeks`
    - Ports: `127.0.0.1:8000->8000/tcp`
Observed via: `ssh orin 'docker ps -a --format "table {{.Names}}\\t{{.Image}}\\t{{.Status}}\\t{{.Ports}}"'`

## Audio devices

- Capture devices include `NVIDIA Jetson AGX Orin APE` and `Shure MV51`
- Playback devices include HDMI outputs and the Jetson APE audio endpoints
Observed via: `ssh orin 'arecord -l; aplay -l'`

## Ports

- `192.168.1.93:18080` by `voice-gateway`
- `127.0.0.1:18081` by a Python process backing native STT
- `127.0.0.1:8000` by the speech backend container
- `0.0.0.0:22` and `[::]:22` for SSH
- `0.0.0.0:111` and `[::]:111` for RPC bind
Observed via: `ssh orin 'ss -ltnp | sed -n "1,120p"'`

## Model/runtime directories

- Candidate runtime directories observed:
  - `/home/christopherbailey`
  - `/mnt/seagate`
- No additional model-store paths were asserted from this pass because the probe did not establish them cleanly.
Observed via: `ssh orin 'for d in /opt/voice-gateway /srv/voice-gateway /home/christopherbailey /mnt/seagate; do [ -e "$d" ] && echo "$d"; done'`

## Preserve candidates

- `voice-gateway.service` as the live speech facade boundary
- `voice-gateway-native-stt.service` as concrete backend evidence behind that facade
- `speaches.service` plus the `speaches` Docker container as current backend reality
- Tailscale and SSH as operator access surfaces
- `/srv/ssd` and `/mnt/seagate` as storage surfaces to preserve before any cleanup
Observed via: `ssh orin 'systemctl ...'`, `ssh orin 'docker ps -a ...'`, `ssh orin 'findmnt /mnt/seagate -R ...'`

## Safe-to-stop candidates

- None asserted from this pass with high confidence. This inventory did not observe clearly retired or disabled speech/runtime surfaces on Orin.

## Unknowns

- Repo canon and older V2 planning docs still need reconciliation with the now-live speech facade on Orin. Repo canon: `docs/foundation/orin-agx.md`, `docs/foundation/topology.md`
- This pass observed no additional inference backend beyond the speech stack; that should remain an observed absence, not a permanent architectural claim.
- `/mnt/seagate` appeared through `autofs` during this pass, so actual live mount behavior should be rechecked before storage-sensitive work.
- The probe did not establish any authoritative model-cache or repo-local runtime directory beyond broad candidate paths.

## V2 implications

- Orin is no longer a mere pending host for V2 planning; it is a live speech appliance host with concrete services.
- The speech facade boundary should remain the planning truth, not the specific backend implementation names.
- Orin should be treated as a preserve-now speech host, not as a general inference host by default.
- Storage and audio-device evidence should be preserved before any future speech-runtime redesign.

## Commands run

- `ssh orin 'hostname; uname -a; printf "\n## os-release\n"; cat /etc/os-release 2>/dev/null | sed -n "1,20p"; printf "\n## whoami\n"; whoami'`
- `ssh orin 'printf "## host\n"; hostnamectl 2>/dev/null | sed -n "1,20p"; printf "\n## release\n"; cat /etc/os-release | sed -n "1,12p"; cat /etc/nv_tegra_release 2>/dev/null || true; printf "\n## hw\n"; lscpu | sed -n "1,40p"; free -h; printf "\n## storage\n"; df -h / /home /mnt/seagate 2>/dev/null; lsblk -o NAME,SIZE,FSTYPE,MOUNTPOINT | sed -n "1,40p"; printf "\n## net\n"; hostname -I; ip -brief addr | sed -n "1,40p"; ip route | sed -n "1,20p"; printf "\n## listen\n"; ss -ltnp | sed -n "1,120p"; printf "\n## services\n"; systemctl list-units --type=service --all --no-pager | egrep -i "voice|docker|containerd|tailscale|ssh|pipewire|pulse|speaches|wyoming|whisper|tts|asr" | sed -n "1,120p"; printf "\n## audio\n"; arecord -l 2>/dev/null || true; echo --; aplay -l 2>/dev/null || true; printf "\n## tools\n"; command -v python3; python3 --version 2>/dev/null; command -v uv || true; command -v docker || true; command -v ffmpeg || true'`
- `ssh orin 'printf "## offload\n"; findmnt /mnt/seagate -R -o TARGET,SOURCE,FSTYPE,OPTIONS 2>/dev/null || true; printf "\n## docker\n"; docker ps -a --format "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || true; printf "\n## candidate dirs\n"; for d in /opt/voice-gateway /srv/voice-gateway /home/christopherbailey /mnt/seagate; do [ -e "$d" ] && echo "$d"; done; printf "\n## sizes\n"; du -sh /opt/voice-gateway /srv/voice-gateway /mnt/seagate 2>/dev/null || true'`

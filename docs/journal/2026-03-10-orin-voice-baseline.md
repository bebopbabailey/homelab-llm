# Orin Voice Baseline Snapshot

Date: 2026-03-10

Purpose: dated evidence record for the current Orin host baseline before
`layer-interface/voice-gateway` deployment work. Treat all items here as
observations from this date, not timeless canonical truth.

## Identity and Access
- SSH alias used: `ssh orin`
- Observed hostname: `theorin`
- Observed service target IP: `192.168.1.93`

Commands:
```bash
ssh orin 'hostnamectl --static; hostname -I | awk "{print $1}"'
```

## Observed OS / Jetson Release
- Observed OS: Ubuntu 22.04.4 LTS
- Observed Jetson release: R36.4.0
- Observed kernel: `5.15.148-tegra`

Commands:
```bash
ssh orin 'cat /etc/os-release | sed -n "1,6p"; cat /etc/nv_tegra_release 2>/dev/null || true; uname -a'
```

## Observed Listener State
- Observed TCP listeners were limited to SSH and RPC-style base services.
- No Voice Gateway listener was observed.
- No Orin inference listener matching the stale `:9210` note was observed.

Commands:
```bash
ssh orin 'ss -ltnp'
ssh orin 'systemctl list-units --type=service --all | grep -Ei "voice|docker|containerd" || true'
```

## Observed Mount Check
- `/mnt/seagate` resolved to an sshfs-backed mount during this snapshot.

Commands:
```bash
ssh orin 'findmnt /mnt/seagate -R -o TARGET,SOURCE,FSTYPE,OPTIONS || true'
```

## Observed Audio Devices
- Onboard audio devices were present.
- A Shure MV51 USB audio device was present.

Commands:
```bash
ssh orin 'arecord -l; aplay -l'
ssh orin 'pactl list short sources 2>/dev/null || true; echo "--"; pactl list short sinks 2>/dev/null || true'
```

## Observed Tool Checks
- `python3` was present on PATH.
- `uv` was not found on PATH.
- `ffmpeg` was not found on PATH.

Commands:
```bash
ssh orin 'command -v python3; command -v uv || true; command -v ffmpeg || true'
```

## Observed Docker Check
- `docker.service` was active during the snapshot.
- `docker ps -a` showed no containers.

Commands:
```bash
ssh orin 'systemctl status docker --no-pager -n 20 || true'
ssh orin 'sudo docker ps -a --format "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}" || true'
```

## Observed Power / Performance Check
- `nvpmodel -q` reported `MAXN`.
- `jetson_clocks --show` reported clocks pinned at the time of the snapshot.

Commands:
```bash
ssh orin 'sudo nvpmodel -q 2>/dev/null || true; sudo jetson_clocks --show 2>/dev/null || true'
```

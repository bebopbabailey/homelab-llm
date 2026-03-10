# Orin Post-Upgrade Baseline Snapshot

Date: 2026-03-10

Purpose: dated evidence record for the Orin host after the owner-reported OS /
JetPack upgrade. This entry supersedes the earlier same-day snapshot in
`docs/journal/2026-03-10-orin-voice-baseline.md` as the latest March 10, 2026
evidence. Treat all items here as observations from this date, not timeless
canonical truth.

## Identity and Access
- SSH alias used: `ssh orin`
- Observed hostname: `theorin`
- Observed primary service target IP: `192.168.1.93`

Commands:
```bash
ssh orin 'hostnamectl --static; hostname -I | awk "{print $1}"'
```

## Observed OS / Jetson Release
- Operator-reported upgrade line: JetPack 6.2.1
- Observed OS: Ubuntu 22.04.5 LTS
- Observed Jetson release: R36.4.7
- Observed kernel: `5.15.148-tegra`
- The host-reported release string above is the canonical verified version data
  for this snapshot.

Commands:
```bash
ssh orin 'cat /etc/os-release | sed -n "1,12p"; cat /etc/nv_tegra_release 2>/dev/null || true; uname -a'
ssh orin 'dpkg -l | grep -Ei "nvidia-jetpack|jetpack|nvidia-l4t-core|cuda-toolkit|tensorrt|cudnn" || true'
```

## Observed Listener State
- Observed TCP listeners were limited to SSH, local resolver, and base RPC-style
  services.
- No Voice Gateway listener was observed.
- No Orin inference listener matching the stale `:9210` note was observed.

Commands:
```bash
ssh orin 'ss -ltnp'
ssh orin 'systemctl list-units --type=service --all | grep -Ei "voice|docker|containerd|pipewire|pulseaudio" || true'
```

## Observed Mount Check
- `findmnt /mnt/seagate -R` reported the `autofs` root during this snapshot.
- The command output did not prove a live `sshfs` child mount at the time of the
  check, so this entry does not describe `/mnt/seagate` as actively mounted over
  `sshfs`.

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
- `python3` was present on `PATH`.
- `python3 --version` reported `3.10.12`.
- `uv` was not found on `PATH`.
- `ffmpeg` was not found on `PATH`.

Commands:
```bash
ssh orin 'command -v python3; python3 --version; command -v uv || true; command -v ffmpeg || true'
```

## Observed Docker Check
- `docker.service` and `containerd.service` were active during the snapshot.
- `docker ps -a` showed no containers.

Commands:
```bash
ssh orin 'systemctl list-units --type=service --all | grep -Ei "docker|containerd" || true'
ssh orin 'sudo docker ps -a --format "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}" || true'
```

## Observed Power / Performance Check
- `nvpmodel -q` reported `MAXN`.
- `jetson_clocks --show` reported pinned clocks at the time of the snapshot.

Commands:
```bash
ssh orin 'sudo nvpmodel -q 2>/dev/null || true; sudo jetson_clocks --show 2>/dev/null || true'
```

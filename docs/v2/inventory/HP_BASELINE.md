# V2 Planning Material: HP Baseline Inventory

Not current runtime truth. This is a read-only planning snapshot for V2 rebuild work.

Snapshot gathered from repo docs plus read-only `ssh hp` inspection on `2026-05-07 UTC`.

## Summary

- HP baseline host is `Kiosk`, an Ubuntu `24.04.4 LTS` desktop on `Hewlett-Packard 23-p114` hardware. Observed via: `ssh hp 'hostnamectl ... cat /etc/os-release ...'`
- Hardware is lightweight by homelab standards: `4` CPU cores, about `6.7 GiB` RAM, and a single `931.5G` SATA disk with about `856G` free. Observed via: `ssh hp 'lscpu ... free -h ... df -h ... lsblk ...'`
- Primary LAN IP is `192.168.1.70` on `enp1s0`. Observed via: `ssh hp 'hostname -I ... ip -brief addr ... ip route ...'`
- This host does not appear to be the live Home Assistant endpoint. No listener on `8123` was observed, and the only clearly relevant running service in the inspected slice was `ssh.service`. Observed via: `ssh hp 'ss -ltnp ... systemctl list-units ...'`
- No Docker or Podman workloads were observed from the current user context. Observed via: `ssh hp 'docker ps ...; podman ps ...'`
- Observed listeners were mostly desktop or operator-facing (`22`, `3389`, `3390`, local CUPS, local resolver, Rygel). Observed via: `ssh hp 'ss -ltnp ...'`

## Host identity

- Hostname: `Kiosk`
- User observed via SSH alias: `kiosk-hp`
- OS: `Ubuntu 24.04.4 LTS`
- Kernel: `Linux 6.17.0-22-generic`
- Architecture: `x86_64`
- Hardware vendor: `Hewlett-Packard`
- Hardware model: `23-p114`
Observed via: `ssh hp 'hostnamectl ... cat /etc/os-release ... uname -a ... whoami'`

## Network

- Primary interface: `enp1s0`
- Primary LAN IPv4: `192.168.1.70/24`
- Default gateway: `192.168.1.254`
- Wireless interface `wlp3s0` was present but down
- Multiple IPv6 addresses were present on `enp1s0`, but this inventory does not treat them as planning canon
Observed via: `ssh hp 'hostname -I ... ip -brief addr ... ip route ...'`

## Storage

- Root filesystem: `/dev/sda2`, about `915G` total, `13G` used, `856G` available
- EFI partition: `/dev/sda1`, `1G`
- No additional homelab data mount was established during this pass
Observed via: `ssh hp 'df -h / /boot /home ... lsblk -o NAME,SIZE,FSTYPE,MOUNTPOINT ...'`

## Memory/runtime tuning

- RAM: about `6.7 GiB`
- Memory in use at snapshot: about `1.9 GiB`
- Free memory at snapshot: about `2.2 GiB`
- Buff/cache: about `2.8 GiB`
- Swap: about `4 GiB`, with `0B` used
Observed via: `ssh hp 'free -h'`

## Services

- `ssh.service`
  - State: `active/running`
  - Role: operator access
- No clearly homelab-specific running services were established from the filtered service probe
Observed via: `ssh hp 'systemctl list-units --type=service --state=running --no-pager | egrep -i "home|ha|docker|podman|nginx|caddy|tailscale|ssh|samba|mqtt|postgres|prometheus|grafana"'`

## Ports

- `0.0.0.0:22` and `[::]:22` for SSH
- `*:3389` and `*:3390` for remote desktop surfaces
- `127.0.0.1:631` and `[::1]:631` for local CUPS
- `127.0.0.54:53` and `127.0.0.53:53` for local resolver
- Several `rygel` listeners were present on ephemeral ports
- No `8123` Home Assistant listener was observed
Observed via: `ssh hp 'ss -ltnp | sed -n "1,80p"'`

## Candidate homelab directories/tools

- Candidate directories observed:
  - `/srv`
  - `/opt`
  - `/var/lib`
  - `/home`
  - `/mnt`
- Python was available:
  - `/usr/bin/python3`
  - `Python 3.12.3`
- No `uv`, Docker, or Podman binary was established in the probe output
Observed via: `ssh hp 'for d in ...'; ssh hp 'command -v python3; python3 --version; command -v uv || true; command -v docker || true; command -v podman || true'`

## Preserve candidates

- SSH access on the HP host should be preserved as the operator entrypoint
- The host identity and LAN presence of `192.168.1.70` should be preserved because repo canon has historically conflated this with Home Assistant
- Any future role for this host should be derived from fresh evidence, not inherited assumptions

## Safe-to-stop-later candidates

- None asserted from this pass. The inventory did not establish any clearly retired homelab-specific service surface on the HP host.

## Unknowns

- Repo canon has historically associated `192.168.1.70` with Home Assistant, but this pass did not support that claim. That contradiction must remain explicit.
- The current homelab role of the physical HP host is unknown/lightweight from observed evidence.
- The probe did not establish whether additional services exist outside the filtered service slice or behind another user/session context.

## V2 implications

- HP should be treated as a distinct physical node from HAOS.
- HP should not be used as shorthand for the live Home Assistant endpoint in future V2 planning docs.
- Any reuse of HP capacity in V2 should start from fresh role definition, not legacy assumptions.

## Commands run

- `ssh hp 'hostname; uname -a; printf "\n## os-release\n"; cat /etc/os-release 2>/dev/null | sed -n "1,20p"; printf "\n## whoami\n"; whoami'`
- `ssh hp 'printf "## host\n"; hostnamectl 2>/dev/null | sed -n "1,20p"; printf "\n## hw\n"; lscpu | sed -n "1,30p"; printf "\n## mem\n"; free -h; printf "\n## storage\n"; df -h / /boot /home 2>/dev/null; lsblk -o NAME,SIZE,FSTYPE,MOUNTPOINT | sed -n "1,40p"; printf "\n## net\n"; hostname -I; ip -brief addr | sed -n "1,40p"; ip route | sed -n "1,20p"; printf "\n## listen\n"; ss -ltnp | sed -n "1,80p"; printf "\n## services\n"; systemctl list-units --type=service --state=running --no-pager | egrep -i "home|ha|docker|podman|nginx|caddy|tailscale|ssh|samba|mqtt|postgres|prometheus|grafana" | sed -n "1,80p"; printf "\n## envs\n"; command -v python3; python3 --version 2>/dev/null; command -v uv || true; command -v docker || true; command -v podman || true'`
- `ssh hp 'printf "## candidate dirs\n"; for d in /srv /opt /var/lib /home /mnt /etc/homeassistant /config; do [ -e "$d" ] && echo "$d"; done; printf "\n## top sizes\n"; du -sh /etc/homeassistant /config /var/lib/docker /var/lib/containers 2>/dev/null; printf "\n## container ps\n"; docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || true; podman ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || true'`

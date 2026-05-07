# V2 Planning Material: HAOS VM Baseline Inventory

Not current runtime truth. This is a host-observed, read-only planning snapshot for the HAOS virtual machine used in V2 rebuild work.

Snapshot gathered from local `virsh` inspection on `themini` plus a read-only HTTP probe on `2026-05-07 UTC`.

## Summary

- `haos` is a live `virsh` VM on `themini`, not a physical host. Observed via: `virsh list --all`, `virsh dominfo haos`
- The guest is `running`, has `2` vCPU, `4 GiB` RAM, and persistent qcow2 storage at `/var/lib/libvirt/images/homeassistant/haos.qcow2`. Observed via: `virsh dominfo haos`, `virsh domblklist haos`
- The VM is bridged to `br0`, with guest MAC `52:54:00:ed:c5:b2`. Observed via: `virsh dumpxml haos`
- Host ARP evidence places that MAC at `192.168.1.40`, matching the existing Mini Tailscale Serve mapping and the live Home Assistant web surface on `http://192.168.1.40:8123`. Observed via: `ip neigh ...`, `curl http://192.168.1.40:8123`
- `virsh domifaddr haos` returned no guest-agent IP, so network identity in this doc is inferred from host bridge evidence rather than direct guest introspection. Observed via: `virsh domifaddr haos`

## VM identity

- VM name: `haos`
- Current state: `running`
- Persistence: `yes`
- Autostart: `disable`
- Security model: `apparmor`
- `virsh` warning signal present: `tainted: custom monitor control commands issued`
Observed via: `virsh dominfo haos`

## Host placement and network

- Hypervisor host: `themini`
- Guest network mode: bridged to `br0`
- Guest MAC: `52:54:00:ed:c5:b2`
- Observed guest IPv4 by host ARP: `192.168.1.40`
- Existing Mini Tailscale Serve mapping also targets `192.168.1.40:8123`
Observed via: `virsh dumpxml haos`, `ip neigh`, `tailscale serve status` evidence already recorded in [MINI_BASELINE.md](MINI_BASELINE.md)

## Virtual hardware

- vCPU: `2`
- Max memory: `4194304 KiB`
- Used memory at snapshot: `4194304 KiB`
- OS type: `hvm`
Observed via: `virsh dominfo haos`

## Storage backing

- Primary disk target: `sda`
- Backing file: `/var/lib/libvirt/images/homeassistant/haos.qcow2`
Observed via: `virsh domblklist haos`

## Observed guest surface

- HTTP on `http://192.168.1.40:8123` returned Home Assistant content
- `HEAD` request returned `405 Method Not Allowed` with `Allow: GET`, which is consistent with a live Home Assistant frontend rather than a dead socket
- HTML title observed: `Home Assistant`
Observed via: `curl -kI --max-time 5 http://192.168.1.40:8123`, `curl -ksS --max-time 5 http://192.168.1.40:8123`

## Ports

- Guest web surface observed: `192.168.1.40:8123`
- Host tailnet listener observed on Mini for forwarded Home Assistant access:
  - `100.69.99.60:8123`
  - `[fd7a:115c:a1e0::e801:6363]:8123`
Observed via: `curl http://192.168.1.40:8123`, `ss -ltnp '( sport = :8123 )'`

## Preserve candidates

- The HAOS qcow2 backing file
- The `br0` bridge placement and guest MAC/IP relationship
- The live Home Assistant web surface at `192.168.1.40:8123`
- The explicit distinction between HAOS and the physical HP host

## Unknowns

- No direct guest shell access was used in this pass, so guest OS version, internal storage layout, add-ons, and service composition remain unknown.
- `virsh domifaddr` returned no guest-agent IP, so guest IP identity relies on bridge/ARP evidence rather than guest-reported data.
- VM autostart is currently `disable`; this is inventory evidence only and should not be normalized into any operational conclusion without review.

## V2 implications

- HAOS should be documented as its own node in V2 planning, separate from the physical HP host.
- The live Home Assistant endpoint evidence currently points to the VM at `192.168.1.40`, not to `192.168.1.70`.
- Future Home Assistant planning should start from VM reality and only add guest-internal claims after direct guest evidence exists.

## Commands run

- `which virsh && virsh list --all && printf '\n## net\n' && virsh net-list --all`
- `printf '## virsh dominfo\n'; virsh dominfo haos; printf '\n## virsh domifaddr\n'; virsh domifaddr haos 2>/dev/null || true; printf '\n## virsh domblklist\n'; virsh domblklist haos; printf '\n## virsh dumpxml excerpt\n'; virsh dumpxml haos | egrep -n '<name>|<uuid>|<memory|<vcpu|source file=|mac address=|network=|bridge=' | sed -n '1,80p'; printf '\n## arp lookup\n'; ip neigh | egrep '192\\.168\\.1\\.40|192\\.168\\.122\\.' | sed -n '1,40p'; printf '\n## host listens 8123\n'; ss -ltnp '( sport = :8123 )' 2>/dev/null || true`
- `printf '## haos http\n'; curl -kI --max-time 5 http://192.168.1.40:8123 2>/dev/null | sed -n '1,20p'; printf '\n## haos title\n'; curl -ksS --max-time 5 http://192.168.1.40:8123 2>/dev/null | sed -n '1,40p' | head -n 5`

# 2026-03-30 — Mini Tailscale Serve recovery and SSH triage

## Summary
- Confirmed the Mini's tailnet operator surface regressed because a local ad-hoc
  `tailscale serve reset` replaced the documented `svc:*` Services config with a
  node-root `themini` HTTPS mapping plus `/codex/`.
- Restored the documented Mini Tailscale Services contract:
  `svc:code`, `svc:chat`, `svc:codeagent`, `svc:gateway`, `svc:hands`,
  `svc:search`, plus TCP `4443 -> 127.0.0.1:4000`.
- Verified the restored operator URLs remotely from `orin`:
  `gateway.tailfd1400.ts.net` returned `200` on `/health/readiness`,
  `codeagent.tailfd1400.ts.net` returned `401` unauthenticated, and `orin`
  resolved both service hostnames over `tailscale0`.
- Did not find evidence of a fresh Mini-side `netplan` or `sshd` regression:
  `/etc/netplan/*.yaml` and `/etc/ssh/sshd_config*` are dated `2025-12-16`,
  there was no carrier loss after boot, and the MacBook SSH sessions closed
  cleanly in Mini logs rather than alongside a server-side restart.

## High-signal evidence
- Host shell history:
  - `~/.bash_history` lines `1977-1987` show:
    - `tailscale serve status`
    - `tailscale cert $(hostname).$(tailscale status --json | jq -r '.CurrentTailnet.Name').ts.net`
    - `tailscale serve ... /codex`
    - `tailscale serve status --json > ~/tailscale-serve-backup.json`
    - `sudo tailscale serve reset`
    - `sudo tailscale serve --bg --https=443 http://127.0.0.1:4000`
    - `sudo tailscale serve --bg --https=443 --set-path=/codex /home/christopherbailey/codex-out`
- Tailscale daemon log:
  - `journalctl -b -u tailscaled` shows `localapi: [POST] /localapi/v0/serve-config`
    at `2026-03-30 17:16:03`, `17:16:09`, and `17:16:20 UTC`, with the earlier
    listeners for `3000`, `4000`, `4031`, `4096`, `8080`, and `8888` closed.
- Saved good config:
  - `~/tailscale-serve-backup.json` preserved the prior working shape:
    `TCP.4443` plus the six `Services`.
- Mini SSH/server evidence:
  - `journalctl -b | rg 'sshd|LinkChange: major|Lost carrier|Gained carrier'`
    shows no Mini carrier loss after boot and no `sshd` restart during the
    reported MacBook drop windows.
  - `journalctl -b -u ssh.service` shows clean session closes for the MacBook
    LAN sessions at `19:01:18` and `20:09:14 UTC`.

## Commands run
```bash
sudo tailscale serve status --json > ~/tailscale-serve-pre-restore-20260330T222219Z.json

sudo tailscale serve reset
sudo tailscale serve --yes --bg --tcp=4443 tcp://127.0.0.1:4000
sudo tailscale serve --yes --bg --service=svc:chat http://127.0.0.1:3000
sudo tailscale serve --yes --bg --service=svc:code http://127.0.0.1:8080
sudo tailscale serve --yes --bg --service=svc:codeagent http://127.0.0.1:4096
sudo tailscale serve --yes --bg --service=svc:gateway http://127.0.0.1:4000
sudo tailscale serve --yes --bg --service=svc:hands http://127.0.0.1:4031
sudo tailscale serve --yes --bg --service=svc:search http://127.0.0.1:8888
tailscale serve status --json

ssh -o BatchMode=yes -o ConnectTimeout=8 orin 'resolvectl query gateway.tailfd1400.ts.net codeagent.tailfd1400.ts.net'
ssh -o BatchMode=yes -o ConnectTimeout=8 orin 'printf "gateway "; curl -ksS -o /dev/null -w "%{http_code}\n" --max-time 8 https://gateway.tailfd1400.ts.net/health/readiness; printf "codeagent "; curl -ksS -o /dev/null -w "%{http_code}\n" --max-time 8 https://codeagent.tailfd1400.ts.net/'
ssh -o BatchMode=yes -o ConnectTimeout=8 orin 'tailscale ping -c 3 themini'

tailscale status --json | jq '{Health: .Health, PeerCount: (.Peer|length), Self: {DNSName: .Self.DNSName, Active: .Self.Active, InMagicSock: .Self.InMagicSock, InEngine: .Self.InEngine}}'
sudo iptables -t filter -S
sudo ip6tables -t filter -S
sudo nft list ruleset
```

## Results
- `tailscale serve status --json` now matches the documented Mini contract again.
- Remote tailnet validation from `orin` succeeded:
  - `gateway.tailfd1400.ts.net` resolved and returned `200`.
  - `codeagent.tailfd1400.ts.net` resolved and returned `401` unauthenticated.
  - `tailscale ping themini` from `orin` used direct path `via 192.168.1.71`.
- Mini-local self-resolution is still odd:
  - `resolvectl query code.tailfd1400.ts.net ...` on the Mini still returns
    NXDOMAIN for its own `svc:*` hostnames even after cache flush, despite remote
    tailnet clients resolving and using them successfully.
- Tailscale still reports the pre-existing health warning:
  - missing IPv6 `ts-input` chain via `ip6tables`.
  - `tailscale debug prefs` shows `RunSSH=true`, `AdvertiseServices` present,
    and `NoStatefulFiltering=true`.

## Deferred follow-up
- Do not keep `/codex` live on the node-root hostname.
- If `/codex` should come back later, give it its own Tailscale Service/grant/doc contract.
- Revisit the Mini-local MagicDNS self-resolution quirk and the `ts-input`
  warning separately if they continue to matter after remote operator paths stay stable.

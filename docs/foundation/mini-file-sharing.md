# Mini File Sharing (Finder over SMB)

## Scope
Mini-hosted SMB access for Finder on the home LAN.

## Runtime contract
- Host: Mini (`themini`, Ubuntu 24.04)
- Transport: SMB/CIFS
- Ports: `139/tcp`, `445/tcp`
- Network scope: LAN only on `127.0.0.1` + `192.168.1.71`
- Auth: password login for Samba user `christopherbailey`
- Guest access: disabled
- Finder connection URLs:
  - `smb://192.168.1.71/mini-root`
  - `smb://192.168.1.71/seagate`

## Share contract
- `mini-root`
  - Path: `/`
  - Writable as Unix user `christopherbailey`
  - Hidden pseudo-filesystems: `/proc`, `/sys`, `/dev`, `/run`
  - `hide unreadable = yes`
- `seagate`
  - Path: `/mnt/seagate`
  - Writable as Unix user `christopherbailey`

## Canonical config
- Live file: `/etc/samba/smb.conf`
- Repo template: `platform/ops/templates/samba-mini-shares.conf`
- Keep the repo-managed block delimited with:
  - `# BEGIN repo-managed Mini Finder SMB block`
  - `# END repo-managed Mini Finder SMB block`

## Deploy steps
```bash
sudo cp /etc/samba/smb.conf /etc/samba/smb.conf.bak.$(date +%F-%H%M%S)
sudo testparm -s
sudo smbpasswd -a christopherbailey
sudo systemctl reload smbd.service nmbd.service
```

## Validation
```bash
sudo testparm -s | rg 'interfaces =|bind interfaces only =|map to guest =|server min protocol ='
sudo pdbedit -L | rg '^christopherbailey:'
sudo systemctl --no-pager --full status smbd.service nmbd.service
sudo journalctl -u smbd -u nmbd -n 50 --no-pager
```

Finder checks on the MacBook:
- Connect with `Cmd-K` to `smb://192.168.1.71/mini-root`
- Connect with `Cmd-K` to `smb://192.168.1.71/seagate`
- Verify browse access to `/home`, `/mnt`, `/etc`, `/usr`
- Verify create/delete in `/home/christopherbailey/Downloads`
- Verify create/delete in `/mnt/seagate/backups`
- Verify writes to root-owned locations such as `/etc` fail

## Rollback
```bash
sudo cp /etc/samba/smb.conf.bak.<timestamp> /etc/samba/smb.conf
sudo systemctl reload smbd.service nmbd.service
sudo smbpasswd -x christopherbailey
```

## Non-goals
- No Tailnet SMB in this phase
- No Bonjour/auto-discovery work
- No NFS or WebDAV rollout

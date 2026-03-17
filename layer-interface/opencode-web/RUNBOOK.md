# Runbook: OpenCode Web

## Install or Refresh the Unit
```bash
sudo install -d -m 0755 /etc/opencode
sudo install -m 0644 /home/christopherbailey/homelab-llm/platform/ops/systemd/opencode-web.service /etc/systemd/system/opencode-web.service
```

If `/etc/opencode/env` does not exist yet:
```bash
sudo install -m 0600 /home/christopherbailey/homelab-llm/platform/ops/templates/opencode.env.example /etc/opencode/env
sudoedit /etc/opencode/env
```

## Reload and Restart
```bash
sudo systemctl daemon-reload
sudo systemctl restart opencode-web.service
sudo systemctl enable opencode-web.service
```

## Service Inspection
```bash
systemctl status opencode-web.service --no-pager
systemctl show opencode-web.service \
  -p User -p WorkingDirectory -p ExecStart \
  -p ProtectSystem -p ProtectHome -p ReadWritePaths \
  -p NoNewPrivileges -p PrivateTmp
```

## Auth Checks
```bash
curl -i http://127.0.0.1:4096/ | sed -n '1,20p'
sudo bash -lc 'set -a; . /etc/opencode/env; user="${OPENCODE_SERVER_USERNAME:-opencode}"; curl -s -o /dev/null -w "%{http_code}\n" -u "$user:$OPENCODE_SERVER_PASSWORD" http://127.0.0.1:4096/'
```

Expected:
- unauthenticated `GET /` returns `401`
- authenticated `GET /` returns `200`

## Namespace Writeability Checks
```bash
pid="$(systemctl show -p MainPID --value opencode-web.service)"
sudo nsenter -t "$pid" -m -- bash -lc '
  set -e
  touch /home/christopherbailey/homelab-llm/.opencode-write-test
  rm /home/christopherbailey/homelab-llm/.opencode-write-test
  touch /home/christopherbailey/homelab-llm/.git/.opencode-git-write-test
  rm /home/christopherbailey/homelab-llm/.git/.opencode-git-write-test
'
```

Negative least-privilege check:
```bash
pid="$(systemctl show -p MainPID --value opencode-web.service)"
sudo nsenter -t "$pid" -m -- bash -lc 'touch /home/christopherbailey/.opencode-should-fail'
```

Expected:
- repo-root and `.git` writes succeed
- unrelated home-path write fails

## Tailnet Exposure
Desired state:
```bash
tailscale serve --yes --bg --service=svc:codeagent http://127.0.0.1:4096
tailscale serve --yes --https=443 off
```

Verification:
```bash
tailscale serve status --json
curl -s -o /dev/null -w "%{http_code}\n" https://codeagent.tailfd1400.ts.net/
sudo bash -lc 'set -a; . /etc/opencode/env; user="${OPENCODE_SERVER_USERNAME:-opencode}"; curl -s -o /dev/null -w "%{http_code}\n" -u "$user:$OPENCODE_SERVER_PASSWORD" https://codeagent.tailfd1400.ts.net/'
```

Expected:
- no top-level node `Web` entry remains for `themini.tailfd1400.ts.net:443`
- `Services["svc:codeagent"]` proxies `https://codeagent.tailfd1400.ts.net/` to `http://127.0.0.1:4096`
- Mini tailnet TCP `4443 -> 127.0.0.1:4000` remains present
- unauthenticated remote `GET /` returns `401`
- authenticated remote `GET /` returns `200`

## Rollback
```bash
sudo cp /etc/systemd/system/opencode-web.service.bak.<timestamp> /etc/systemd/system/opencode-web.service
sudo systemctl daemon-reload
sudo systemctl restart opencode-web.service
```

Serve rollback:
```bash
tailscale serve --yes --bg --https=443 http://127.0.0.1:4096
tailscale serve --yes --bg --service=svc:codeagent http://127.0.0.1:4096
tailscale serve status --json
```

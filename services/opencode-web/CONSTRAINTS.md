# Constraints: OpenCode Web

This service inherits global + layer constraints:
- Global: `../../CONSTRAINTS.md`
- Interface layer: `../CONSTRAINTS.md`

## Hard Constraints
- Keep `opencode-web.service` on `0.0.0.0:4096` unless an approved migration plan says otherwise.
- Tailnet exposure for OpenCode Web must use `svc:codeagent` only.
- Do not expose OpenCode Web through the node-root `themini.tailfd1400.ts.net` hostname.
- Keep existing Basic Auth via `/etc/opencode/env`; never commit secrets.
- Keep `ProtectSystem=strict` and `ProtectHome=read-only`.
- Do not broaden write access beyond the documented allowlist without explicit approval.

## Writable Allowlist
- `/home/christopherbailey/.local/share/opencode`
- `/home/christopherbailey/.local/state/opencode`
- `/home/christopherbailey/.cache/opencode`
- `/home/christopherbailey/homelab-llm`

## Forbidden Operations
- No full-home write access.
- No disabling hardening as a shortcut for edit failures.
- No direct model/provider secrets in repo-managed files.

## Validation Pointers
- `systemctl show opencode-web.service -p ProtectSystem -p ProtectHome -p ReadWritePaths -p ExecStart -p WorkingDirectory`
- `curl -i http://127.0.0.1:4096/ | sed -n '1,20p'`
- `sudo nsenter -t "$(systemctl show -p MainPID --value opencode-web.service)" -m -- bash -lc 'touch /home/christopherbailey/homelab-llm/.opencode-write-test && rm /home/christopherbailey/homelab-llm/.opencode-write-test'`

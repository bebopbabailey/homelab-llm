# Node Toolchain Contract (Mini / Agent Hosts)

This document is the canonical policy for Node.js and global CLI management on
agent deployment hosts (especially the Mini). It exists to prevent version
drift and "updated but still old version" failures.

## Why this exists

When Volta manages a CLI, the command you run is a Volta shim. Running
`npm install -g <package>` can update a different global tree than the one the
shim is pinned to. The result is a common failure mode:

- npm reports an updated package
- the CLI command still runs an older version

## Required policy

1. Use Volta as the source of truth for global agent CLIs.
2. Install and update managed CLIs with `volta install <package>@latest`.
3. Use `npm install` for project-local dependencies only.
4. Do not use `sudo npm -g`.

## Standard commands

Install or update a managed CLI:

```bash
volta install @openai/codex@latest
volta install @google/gemini-cli@latest
```

Remove and reinstall a stale pinned CLI:

```bash
volta uninstall @openai/codex
volta install @openai/codex@latest
```

Verify what is active:

```bash
which -a codex
codex --version
volta list @openai/codex
volta which codex
```

## Troubleshooting: npm updated but CLI version did not

Symptom:
- `npm install -g <cli>` succeeds
- `<cli> --version` is unchanged

Root cause:
- Volta still has a pinned package version for that CLI shim.

Fix:
1. `volta uninstall <package>`
2. `volta install <package>@latest`
3. Re-run `which -a <cli>`, `<cli> --version`, and `volta list <package>`.

## Optional shell guardrail

Add an interactive guard to reduce accidental global installs:

```bash
npm() {
  if [[ "$1" == "install" || "$1" == "i" ]]; then
    for arg in "$@"; do
      if [[ "$arg" == "-g" || "$arg" == "--global" ]]; then
        echo "Use 'volta install <package>@latest' for global agent CLIs."
        return 1
      fi
    done
  fi
  command npm "$@"
}
```

Note: keep this as an operator opt-in; this repo does not enforce shell config.

## New host checklist

1. Confirm Volta is first in path: `which -a node npm`.
2. Confirm no system shadowing for managed CLIs: `which -a codex gemini`.
3. Confirm versions match Volta metadata:
   - `<cli> --version`
   - `volta list <package>`
4. Validate in a fresh login shell.

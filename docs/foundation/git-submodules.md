# Git Submodules (Homelab LLM)

This repo uses **git submodules** for service repos that evolve independently.
This keeps each service’s history intact while the monorepo pins exact versions.

## Why submodules here
- Services like `services/litellm-orch` and `services/ov-llm-server` have their own
  lifecycles, releases, and dependency management.
- The monorepo records the exact commit for each service so the platform is reproducible.

## Key concept
A submodule is a *pointer* to a specific commit in another repo. The monorepo must
be updated whenever the submodule pointer changes.

## One-time setup (after clone)
```bash
# Clone the monorepo and initialize submodules

git clone <your-monorepo-url>
cd homelab-llm

git submodule update --init --recursive
```

## Daily workflow
### 1) Pull updates (monorepo + submodules)
```bash
git pull

git submodule update --init --recursive
```

### 2) Work inside a submodule
```bash
cd services/litellm-orch
# make changes, commit in the submodule repo

git status

git add -A

git commit -m "your message"
```

### 3) Update the monorepo pointer
```bash
cd /home/christopherbailey/homelab-llm

git status
# You will see the submodule marked as modified

git add services/litellm-orch

git commit -m "Update litellm-orch submodule"
```

### 4) Push
```bash
# Push submodule repo first
cd services/litellm-orch

git push

# Then push the monorepo pointer
cd /home/christopherbailey/homelab-llm

git push
```

## Common pitfalls
- **Forgetting to update the monorepo pointer** after committing inside a submodule.
- **Pulling the monorepo** without running `git submodule update` (submodules stay stale).
- **Trying to edit submodule files without committing** inside the submodule repo.

## Quick health check
```bash
cd /home/christopherbailey/homelab-llm

git submodule status
```

If you see a leading `-` or `+`, the submodule pointer is out of sync.

## Where we use submodules
- `services/litellm-orch`
- `services/ov-llm-server`


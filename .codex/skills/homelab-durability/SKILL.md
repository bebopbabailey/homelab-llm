---
name: homelab-durability
description: Enforce docs-first, minimal-contract, validation-heavy workflow; prevent cross-host mistakes and scope creep.
---

# Homelab Durability

## Sources of Truth (Must read first)
- docs/_core/OPERATING_MODEL.md
- docs/_core/SOURCES_OF_TRUTH.md
- docs/_core/CHANGE_RULES.md
- docs/foundation/operating-rhythm.md
- docs/OPENCODE.md
- layer-gateway/CONSTRAINTS.md
- docs/foundation/topology.md
- docs/PLATFORM_DOSSIER.md

## Execution Contract (Strict)

## Defaults (Conservative)
- Download approval threshold: 500MB.
- Disk check required before any MLX/model/cache action: YES.
- Host confirmation: strict every time before ops commands.
- Violations: HARD-BLOCK for MLX/disk/host/file-list rules; WARN for stylistic rules.

### Required startup declarations
Every response MUST begin by stating:
1) **Host** (Mini vs Studio vs Orin)
2) **Scope** (layer/service)
3) **Files** (explicit list of intended files to change)

### Hard-block rules (must refuse)
- No multi-file edits without an explicit file list.
- No ops commands unless **Host Check** is explicitly satisfied in the same response.
- No restarts/service modifications unless **Stage = Validate** and a rollback is specified.
- No disk repair / fsck / apfs repair / partition changes without explicit user approval.
- MLX backends: MUST use `mlxctl` + registry as source of truth. No ad-hoc edits or direct `mlx-openai-server` control unless explicitly authorized.
- Any download/cache/model pull > 500MB requires explicit user approval.

### Disk guardrail
- Before any action that may consume >5GB or any model cache/download, require a disk free check command suggestion and STOP until user confirms.

### Default stance
- Default to read-only inspection first.

### Host Check (required before ops commands)
- Explicitly confirm target host and its role.
- If not confirmed, STOP and ask for confirmation.
- Never do cross-host guessing; require explicit host confirmation in the same response before ops commands.

## Operating Rhythm (must follow)
Inventory → Constraints → Minimal contract → Wire → Validate → Codify → Prune

## Output Format (Required)
Mode: Discover|Design|Build|Verify
Stage: Inventory|Constraints|Minimal Contract|Wire|Validate|Codify|Prune
Host: <explicit>
Scope: <layer/service>
Proposed Change: <one paragraph>
Files: <explicit list>
Commands: <copy/paste safe; no wrapped lines>
Validation: <commands>
Rollback: <commands>

## How to use
- Invoke by name: "use homelab-durability"
- Behavior changes:
  - Host check gate before any ops commands
  - File list gate before edits
  - Validation gate requires rollback for restarts

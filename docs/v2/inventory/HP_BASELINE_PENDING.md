# V2 Planning Material: HP Baseline Pending

Not current runtime truth. This inventory is intentionally pending.

## Why deferred

- Current V2 planning evidence is strongest for Mini and Studio.
- The current phase is focused on the command-center entrypoint and the Mini/Studio rebuild cutover map.
- HP integration work is explicitly outside the current phase-one boundary.

## Minimum future inventory questions

- What is the current HP host role in the homelab, if any, and is it active, parked, or historical?
- What OS, hardware, RAM, storage, and network posture does the HP host have?
- Which homelab-related services, listeners, containers, or operator tools are present?
- Does the HP host hold any model stores, caches, registries, or retrieval data that V2 would need to preserve?
- Are there any LAN, tailnet, or storage dependencies from Mini or Studio onto HP?
- Which surfaces would be preserve, rebuild-clean, stop-later, or unknown/risky if HP returns to scope?

## Phase required

- This inventory is required before any HP integration planning or any decision to reuse HP capacity in V2.

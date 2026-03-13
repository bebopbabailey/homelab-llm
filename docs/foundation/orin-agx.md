# Jetson Orin AGX

## Purpose
Edge compute host designated for Voice Gateway deployment and future on-device
experiments.

## Canonical Host Doc
This file is the canonical Orin host doc for active documentation.

## Evidence Record
- Latest dated evidence: `docs/journal/2026-03-10-orin-phase1-preflight-corrections.md`
- Verification commands: `docs/foundation/testing.md`

## Host Identity Conventions
- SSH alias: `orin`
- hostname: `theorin`
- service target IP: `192.168.1.93`

## Access
- Operator entrypoint: `ssh orin`

## Runtime role (current)
- No inference backends are currently deployed on Orin.
- Voice Gateway is designated for this host, but a live deployment is not
  documented yet.

## Notes
- Keep volatile host-state observations in the dated journal entry rather than
  treating them as timeless canonical truth.
- The earlier `docs/journal/2026-03-10-orin-voice-baseline.md` entry remains as
  the pre-upgrade same-day snapshot.
- The `docs/journal/2026-03-10-orin-post-upgrade-baseline.md` entry remains as
  the broader post-upgrade baseline snapshot; the later same-day preflight note
  clarifies Phase 1 tooling and packaging details.

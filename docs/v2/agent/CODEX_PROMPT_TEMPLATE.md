# V2 Planning Material: Codex Prompt Template

Not current runtime truth. This is a reusable prompt template for Codex planning-only sessions.

```md
You are working in homelab-llm.

Mode: V2 planning-prep docs only.

Goal:
- <state the planning goal>

Allowed paths:
- <docs-only paths>

Forbidden paths:
- service configs
- systemd/launchd files
- Docker/Compose files
- platform registry files
- active runtime docs outside the allowed planning scope
- host-modifying scripts

Read first:
- <planning doctrine docs>
- <evidence docs>
- <inventory docs>

Deliverables:
- <planning-only docs or summaries>

Constraints:
- mark outputs as V2 planning material, not runtime truth
- do not choose backends
- do not choose repo layout
- do not promote candidates to defaults
- do not design V2 infrastructure
- keep these evidence categories explicit:
  - doctrine
  - conditional candidate
  - historical reference
  - retest-only
  - unknown
- prefer readiness, doctrine, evidence, or inventory-review outputs before broader V2 planning

Verification:
- uv run python scripts/repo_hygiene_audit.py --json
- uv run python scripts/control_plane_sync_audit.py --strict --json
- uv run python scripts/service_registry_audit.py --strict --json
- uv run python scripts/docs_link_audit.py

Debrief format:
1. Summary
2. Files created
3. Files modified
4. Checks run
5. Planning boundaries preserved
6. Open questions
7. Recommended next docs-only step
```

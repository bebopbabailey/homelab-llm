# 2026-04-30 — Open WebUI query-generation prompt policy

## Objective
- Add a durable global Open WebUI instruction that makes web-search query
  generation topic-first and date-last.
- Put the policy in a host-level location that survives restarts and is easy to
  inspect later.

## Runtime shape
- Host: Mini
- Service: `open-webui.service`
- Authority path:
  `/etc/systemd/system/open-webui.service.d/25-querygen-prompt-policy.conf`

## Change
- Added a new systemd drop-in:
  - `/etc/systemd/system/open-webui.service.d/25-querygen-prompt-policy.conf`
- The drop-in sets `QUERY_GENERATION_PROMPT_TEMPLATE` globally for Open WebUI.
- The policy tells query generation to:
  - keep queries topic-first and date-last
  - never start with a standalone month name or vague time phrase
  - preserve explicit dates but append them after the concrete topic
  - avoid generic community/forum/discussion/sentiment-only rewrites unless the
    actual subject is present

Backup handling:
- Existing drop-in backup would have been created as
  `/etc/systemd/system/open-webui.service.d/25-querygen-prompt-policy.conf.bak.<timestamp>`
  if a prior file existed.
- This was a new file on this host, so no prior-content backup was needed.

## Validation
- `sudo systemctl daemon-reload`
- `sudo systemctl restart open-webui.service`
- `sudo systemctl status open-webui.service --no-pager`
  - active/running
- Authenticated task-config check:
  - `GET /api/v1/tasks/config`
  - confirmed `ENABLE_SEARCH_QUERY_GENERATION=true`
  - confirmed non-empty `QUERY_GENERATION_PROMPT_TEMPLATE` matching the new
    drop-in

## Notes
- The direct `/api/v1/tasks/queries/completions` probe with `model=fast` and
  `model=deep` returned `404 {"detail":"Model not found"}` on this host.
  That probe was not required to validate the config change itself because the
  authoritative live task config already reflected the new prompt value.

## Outcome
- The global query-generation instruction is now live and durable.
- The setting lives in a host-visible systemd override rather than only inside
  Open WebUI DB state.

## Cleanup state
- No rollback performed.
- Rollback path:
  - remove `/etc/systemd/system/open-webui.service.d/25-querygen-prompt-policy.conf`
    or restore its backup
  - `sudo systemctl daemon-reload`
  - `sudo systemctl restart open-webui.service`

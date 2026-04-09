# 2026-04-08 — LiteLLM upstream MCP toolset evaluation (`NO-GO`, rolled back)

## Summary

This evaluation tested whether an official upstream LiteLLM GitHub snapshot fixed the Mini-side MCP route/auth defect that blocks Open WebUI from consuming a LiteLLM-owned OpenTerminal shared tool lane.

The answer is no.

The upstream snapshot proved that LiteLLM's MCP control-plane pieces are largely present and functional:
- DB-backed MCP servers work
- MCP toolsets work
- standalone keys scoped by `object_permission.mcp_toolsets` work
- `/v1/mcp/tools` reflects the expected filtered tool surface

The failure remains at the actual MCP route used by clients:
- `Authorization: Bearer <key>` timed out
- `x-litellm-api-key: <raw-key>` returned `500`
- `x-litellm-api-key: Bearer <key>` timed out

That same failure reproduced against current upstream source, not just packaged stable `1.83.4`. The issue is therefore upstream LiteLLM MCP route/auth behavior, not repo config, router config, or OpenTerminal backend reachability.

## Scope

- Host: `Mini`
- Live baseline intentionally preserved: LiteLLM stable runtime on `127.0.0.1:4000`
- Candidate evaluation only:
  - official upstream LiteLLM source clone
  - throwaway venv
  - throwaway Postgres database
  - throwaway MCP server/toolset/key objects
- No repo-tracked runtime contract changes
- No live cutover

## Candidate Provenance

- Upstream repo: `https://github.com/BerriAI/litellm.git`
- Evaluated commit: `2dac54b732e93baf5964ff739f9c4efa3d2d7eb1`
- Candidate identified itself as: `litellm 1.83.5`
- Candidate bind: `127.0.0.1:4011`
- Throwaway DB: `litellm_eval_mcp`

Scratch artifacts were captured under:
- `/var/tmp/litellm-upstream-mcp-eval/artifacts/`
- `/var/tmp/litellm-upstream-mcp-eval/logs/`

Notable files:
- `/var/tmp/litellm-upstream-mcp-eval/artifacts/candidate-version.txt`
- `/var/tmp/litellm-upstream-mcp-eval/artifacts/db-setup.json`
- `/var/tmp/litellm-upstream-mcp-eval/artifacts/open-terminal-server.json`
- `/var/tmp/litellm-upstream-mcp-eval/artifacts/open-terminal-toolset.json`
- `/var/tmp/litellm-upstream-mcp-eval/artifacts/open-terminal-key.json`
- `/var/tmp/litellm-upstream-mcp-eval/artifacts/route-matrix.json`
- `/var/tmp/litellm-upstream-mcp-eval/logs/litellm-candidate.log`

## Stable Baseline Before Evaluation

The live `:4000` service stayed untouched throughout the pass.

Verified baseline on stable LiteLLM `1.83.4`:
- readiness healthy
- `/v1/models` exposed only:
  - `main`
  - `deep`
  - `fast`
  - `code-reasoning`
  - `task-json`
  - `task-transcribe`
  - `task-transcribe-vivid`
- `/v1/mcp/server` showed only `home_assistant`
- `/v1/mcp/toolset` was empty
- `/v1/mcp/tools` showed only the existing Home Assistant tool surface
- `/key/info` and `/key/generate` were healthy again after the earlier Prisma/schema repair work

## Scratch Bootstrap Findings

The upstream source did not start cleanly in the scratch venv without extra bootstrap steps.

Issues encountered:
- missing `prometheus_client`
- missing `prisma`
- missing generated Prisma client

Scratch-only fixes applied:
- install `prometheus_client`
- install `prisma==0.15.0`
- generate Prisma client from LiteLLM's shipped schema

These were evaluation-environment fixes only. They were not applied to the repo or live service.

After those fixes, the candidate reached healthy readiness on `127.0.0.1:4011`.

## What Worked

### 1. OpenTerminal backend reachability through LiteLLM preview

Against the candidate:
- `POST /mcp-rest/test/connection` succeeded
- `POST /mcp-rest/test/tools/list` succeeded

That preview path returned the raw upstream OpenTerminal inventory, confirming the backend itself was reachable and healthy from the candidate LiteLLM process.

### 2. DB-backed MCP server registration

The candidate accepted a DB-backed LiteLLM MCP server for OpenTerminal:
- `server_name`: `open_terminal`
- `alias`: `open_terminal`
- `server_id`: `6ef296c8-40b9-4ca1-8ce1-5bea9b8d7779`
- `allowed_tools`:
  - `health_check`
  - `list_files`
  - `read_file`
  - `grep_search`
  - `glob_search`

### 3. MCP toolset creation

The candidate accepted a toolset referencing exactly the intended read-only subset:
- `toolset_name`: `open_terminal_readonly`
- `toolset_id`: `0494f67a-1bb5-4d01-a095-637f80f37654`

### 4. Standalone key generation using `mcp_toolsets`

The candidate accepted a standalone virtual key with:
- `key_alias`: `open-webui-terminal-readonly`
- `object_permission.mcp_toolsets = [0494f67a-1bb5-4d01-a095-637f80f37654]`
- `allowed_routes` including:
  - `/toolset/open_terminal_readonly/mcp`
  - `/open_terminal_readonly/mcp`

This confirmed the earlier finding that `mcp_toolsets` is the supported primitive for standalone-key MCP scoping, not `mcp_servers`.

### 5. Filtered tool exposure on the management surface

With the candidate master key, `/v1/mcp/tools` showed the expected five OpenTerminal tools:
- `open_terminal-health_check`
- `open_terminal-list_files`
- `open_terminal-read_file`
- `open_terminal-grep_search`
- `open_terminal-glob_search`

This means the LiteLLM MCP control-plane data model was coherent enough to register and list the desired restricted tool surface.

## Failing Matrix

The actual client-facing MCP route still failed.

Tested routes:
- `http://127.0.0.1:4011/toolset/open_terminal_readonly/mcp`
- `http://127.0.0.1:4011/open_terminal_readonly/mcp`

Tested header variants:
- `Authorization: Bearer <key>`
- `x-litellm-api-key: <raw-key>`
- `x-litellm-api-key: Bearer <key>`

Observed results on both route shapes:

| Route | Header shape | Result |
| --- | --- | --- |
| `/toolset/open_terminal_readonly/mcp` | `Authorization: Bearer <key>` | timeout |
| `/toolset/open_terminal_readonly/mcp` | `x-litellm-api-key: <raw-key>` | HTTP `500` |
| `/toolset/open_terminal_readonly/mcp` | `x-litellm-api-key: Bearer <key>` | timeout |
| `/open_terminal_readonly/mcp` | `Authorization: Bearer <key>` | timeout |
| `/open_terminal_readonly/mcp` | `x-litellm-api-key: <raw-key>` | HTTP `500` |
| `/open_terminal_readonly/mcp` | `x-litellm-api-key: Bearer <key>` | timeout |

The raw-key failure returned:

```json
{"error":"MCP request failed","details":""}
```

Candidate logs also showed the expected validation complaint for that case:
- `Malformed API Key passed in. Ensure Key has Bearer prefix.`

That means the raw-key path is not the intended supported path. The problem is that the documented/expected bearer-style path still hangs and never returns a valid MCP initialize response.

## Open WebUI MCP Client Result

The installed Open WebUI MCP client was tested directly against:
- `http://127.0.0.1:4011/toolset/open_terminal_readonly/mcp`

Headers:
- `x-litellm-api-key: Bearer <candidate_key>`

Result:
- timed out during `initialize()`
- never reached a usable session

The client then hit its known cleanup-path issue:
- `AttributeError: 'NoneType' object has no attribute 'aclose'`

That secondary cleanup bug is in Open WebUI client cleanup, but it is not the primary blocker here. The primary blocker is that LiteLLM never returned a valid MCP initialize response.

## Assessment

### What this rules out

This evaluation rules out the following as the primary cause:
- repo router/config drift
- OpenTerminal backend reachability
- missing LiteLLM MCP server support
- missing LiteLLM MCP toolset support
- missing standalone-key toolset scoping support
- packaged-stable-only lag

### What remains

The remaining defect is in LiteLLM MCP route/auth/session handling for toolset-scoped client traffic.

The strongest evidence:
- control-plane objects create successfully
- the candidate can list the filtered toolset on `/v1/mcp/tools`
- both candidate route shapes still fail at the actual MCP session boundary
- the same defect reproduces on official upstream source

High-level conclusion:
- this is an upstream LiteLLM MCP route defect
- it is not fixable through more repo-side wiring while keeping LiteLLM as the gateway and ACL owner

## Rollback Performed

Everything created for the evaluation was removed.

Rollback completed:
- stopped the candidate LiteLLM process on `:4011`
- deleted the candidate key by alias
- deleted the candidate MCP toolset
- deleted the candidate MCP server
- dropped the throwaway database `litellm_eval_mcp`
- removed candidate runtime state from the active host

Post-rollback verification on live `:4000`:
- readiness healthy
- models unchanged
- `/v1/mcp/server` back to baseline
- `/v1/mcp/toolset` back to baseline
- `/v1/mcp/tools` back to baseline

No repo-tracked files changed during the evaluation pass.

## Current Recommendation

Do not add a shared OpenTerminal LiteLLM lane to the public Open WebUI contract on the current baseline.

The next valid paths are:
1. prepare an upstream defect report using the captured scratch artifacts and route matrix
2. wait for an upstream LiteLLM release that demonstrably fixes the MCP toolset route/auth/session path
3. if waiting is unacceptable, explicitly re-plan a local LiteLLM patch pass against the MCP route/auth handler

## Non-Recommendations

These are not recommended based on the evidence from this pass:
- more repo-local router/config rewiring
- direct Open WebUI connection to `127.0.0.1:8011/mcp`
- loosening the server to `allow_all_keys=true`
- adding team scaffolding just to force key assignment
- reintroducing ChatGPT work in the same slice

## Review Decision

Status: `NO-GO`

Reason:
- the supported, LiteLLM-owned OpenTerminal path still does not produce a working MCP client route, even on the evaluated upstream source snapshot

Recommended next review question:
- upstream issue packet first, or local patch evaluation first

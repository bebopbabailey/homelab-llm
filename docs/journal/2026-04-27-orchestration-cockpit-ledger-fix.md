# 2026-04-27 orchestration-cockpit ledger fix

## Objective
Fix `orchestration-cockpit` per-turn run bookkeeping so repeated Agent Chat UI
messages in a single thread do not reuse `run_id`, accumulate `node_sequence`,
or leak a prior specialized `adapter_request_id` into later turns.

## Cause
`intake_node()` reused prior thread state when `run_id`, `started_at`, and
`node_sequence` were already present in the persisted thread. That was correct
for thread identity but wrong for per-turn observability.

## Change
- always mint a fresh `run_id` at intake
- always mint a fresh `started_at` at intake
- reset per-turn bookkeeping fields at intake:
  - `route_decision`
  - `route_reason`
  - `fixture_id`
  - `node_sequence`
  - `adapter_request_id`
  - `specialized_payload`
  - `specialized_result`
  - `final_text`
  - `error`

## Validation
- unit regression added for two consecutive runs on the same persisted thread:
  - specialized turn followed by out-of-scope turn
- expected result:
  - second run gets a new `run_id`
  - second run starts with `node_sequence == ["intake", "route", "finalize"]`
  - second run ledger entry has empty `adapter_request_id`
- live graph service restarted after merge to pick up the fix

## Notes
This does not change graph routing or runtime behavior. It only corrects the
observability semantics for multi-message UI threads.

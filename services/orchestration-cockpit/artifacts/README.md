# Local Artifacts

`orchestration-cockpit` keeps runtime artifacts local by default.

Default artifact root:
- `/tmp/orchestration-cockpit-phase5`

Current artifacts:
- `run-ledger.jsonl`
  - one record per graph run
  - includes route decision, node sequence, status, latency, and
    `adapter_request_id`
- `omlx-runtime-telemetry.jsonl`
  - correlated specialized-runtime telemetry records
  - uses the same `adapter_request_id` as `request_id`

These files are service-owned local artifacts. They are not repo-tracked
runtime output.

# Testing and Verification

This doc captures the recommended test steps for new changes. Run these on the
appropriate host and confirm outputs before declaring a change complete.

## Documentation integrity
Run these for doc-heavy changes before sign-off:
```bash
uv run python scripts/docs_contract_audit.py --strict --json
uv run python scripts/repo_hygiene_audit.py --json
uv run python scripts/control_plane_sync_audit.py --strict --json
uv run python scripts/service_registry_audit.py --strict --json
uv run python scripts/docs_link_audit.py
```

Expected:
- docs bundle contracts stay complete
- root_ok and journal_index_ok remain true
- service registry coverage remains complete
- control-plane sync remains aligned
- internal markdown links on the supported doc surface resolve cleanly

## Runtime Lock
FAST validator:
```bash
python3 platform/ops/scripts/validate_runtime_lock.py --mode fast --json
```

FULL validator:
```bash
python3 platform/ops/scripts/validate_runtime_lock.py --mode full --host studio --json
```

Expected:
- FAST passes in local CI/repo state with no patch artifacts or git-sourced OptiLLM.
- FULL confirms Studio OptiLLM exact-SHA deploy plus MLX lane `auto`/`--no-async-scheduling` with no backend bearer auth.
- FULL also confirms the locked `8101` parser override: `--tool-call-parser hermes`
  and no `--reasoning-parser`.
- Repo-local validation resolves `litellm-orch` and `optillm-proxy` through the
  service registry rather than hardcoded `layer-*` script constants.

Additional Studio backend checks (not part of the current live FULL gate):
```bash
curl -fsS http://192.168.1.72:4020/v1/models | jq .
curl -fsS http://192.168.1.72:8126/v1/models | jq .
```

Additional backend interpretation:
- `4020` is the non-core OptiLLM operator path
- `8126` is the canonical GPT-family service
- `8123-8125` are retired shadow ports and should not respond

### GPT `llmster` rollout checks
Studio retention dry-run:
```bash
uv run python services/llama-cpp-server/scripts/studio_model_retention.py \
  --host studio \
  --staged-slug gpt-oss-20b-mxfp4 \
  --output /tmp/studio-model-retention-fast.json
```

Raw fast mirror launch:
```bash
uv run python services/llama-cpp-server/scripts/start_raw_llama_mirror.py \
  --host studio \
  --port 8130 \
  --server-bin /Users/thestudio/llama.cpp-releases/current/bin/llama-server \
  --model-path /Users/thestudio/Library/Caches/llama.cpp/ggml-org_gpt-oss-20b-GGUF_gpt-oss-20b-mxfp4.gguf \
  --alias llmster-gpt-oss-20b-mxfp4-gguf
```

Raw launcher invariants:
- use a versioned raw `llama-server` path when available
- use `--jinja`
- do not add repetition penalties for GPT-OSS

Raw/direct acceptance:
```bash
uv run python services/llama-cpp-server/scripts/run_gpt_oss_acceptance.py \
  --base-url http://127.0.0.1:8130/v1 \
  --model llmster-gpt-oss-20b-mxfp4-gguf

uv run python services/llama-cpp-server/scripts/run_gpt_oss_acceptance.py \
  --base-url http://192.168.1.72:8126/v1 \
  --model llmster-gpt-oss-20b-mxfp4-gguf \
  --api-key "$LLMSTER_API_KEY"
```

Deep preflight estimate-only:
```bash
ssh studio '/Users/thestudio/.lmstudio/bin/lms load gpt-oss-20b \
  --identifier llmster-gpt-oss-20b-mxfp4-gguf \
  --context-length 32768 --parallel 4 --estimate-only -y'

ssh studio '/Users/thestudio/.lmstudio/bin/lms load gpt-oss-120b \
  --identifier llmster-gpt-oss-120b-mxfp4-gguf \
  --context-length 32768 --parallel 2 --estimate-only -y'
```

Actual shared-posture proof before any public `deep` cutover:
```bash
ssh studio '/Users/thestudio/.lmstudio/bin/lms ps --json'
ssh studio 'curl -fsS http://192.168.1.72:8126/v1/models | jq .'
ssh studio 'curl -fsS http://192.168.1.72:8126/api/v1/models | jq .'
ssh studio 'memory_pressure -Q'
ssh studio 'vm_stat'
ssh studio 'top -l 1 -stats pid,command,mem,cpu'
sleep 300
ssh studio 'memory_pressure -Q'
ssh studio 'vm_stat'
ssh studio 'top -l 1 -stats pid,command,mem,cpu'
```

Shared-posture interpretation:
- `estimate-only` is necessary but not sufficient
- public `deep` may not be cut over until:
  - both intended models appear in `lms ps --json`
  - both intended models appear in `/v1/models`
  - post-load idle memory captures do not show obvious thrash/instability
  - `fast` still passes its regression gate under the actual dual-load posture

The GPT acceptance harness now reports:
- `plain_chat`
- `structured_simple`
- `structured_nested`
- `auto_tool_noop`
- `auto_tool_arg`
- `required_tool_arg`
- `named_tool_arg`
- `large_schema_tool_stress`
- `responses_smoke`
- `responses_structured_simple`
- `responses_followup_state`
- `concurrency_smoke`

Deep usable-success gate:
- plain chat clean
- structured simple clean
- structured nested clean
- auto noop strong
- auto arg-bearing usable at `>= 8/10` on direct `llmster` and public LiteLLM
- at least one constrained mode strong:
  - `tool_choice="required" >= 9/10`, or
  - named-tool forcing `>= 9/10`
- crashes, listener loss, sustained readiness regressions, repeated `5xx`, and
  repeated timeouts remain blockers
- Current public `deep` cutover result on shared `8126`:
  - `plain_chat`: `5/5`
  - `structured_simple`: `5/5`
  - `structured_nested`: `5/5`
  - `auto_tool_noop`: `10/10`
  - `auto_tool_arg`: `10/10`
  - `required_tool_arg`: `9/10`
  - `named_tool_arg`: unsupported on the current backend path, returns
    backend-visible `400` for object-form `tool_choice`

Raw mirror policy:
- raw standalone llama.cpp remains diagnostic-first
- raw divergence alone does not block promotion unless it exposes a crash,
  gross corruption, or a reproducible defect that also appears on direct
  `llmster` or public LiteLLM

OpenAI gpt-oss verification:
- Run the official upstream verification flow described in:
  `https://developers.openai.com/cookbook/articles/gpt-oss/verifying-implementations`
- Minimum in this repo:
  - one pass on refreshed raw deep mirror
  - one pass on direct `llmster` deep
  - optional public LiteLLM deep smoke if it adds signal

Accepted cutover order:
- raw `deep` validation
- direct `llmster` `deep` validation
- temporary canary validation through LiteLLM (now retired)
- only then canonical public `deep`

Raw mirror teardown:
```bash
uv run python services/llama-cpp-server/scripts/stop_raw_llama_mirror.py \
  --host studio \
  --port 8130
```

## OpenCode Web (Mini)
Service install/source-of-truth check:
```bash
systemctl cat opencode-web.service
systemctl show opencode-web.service \
  -p User -p WorkingDirectory -p ExecStart \
  -p ProtectSystem -p ProtectHome -p ReadWritePaths \
  -p NoNewPrivileges -p PrivateTmp
```

Auth check:
```bash
curl -i http://127.0.0.1:4096/ | sed -n '1,20p'
sudo bash -lc 'set -a; . /etc/opencode/env; user="${OPENCODE_SERVER_USERNAME:-opencode}"; curl -s -o /dev/null -w "%{http_code}\n" -u "$user:$OPENCODE_SERVER_PASSWORD" http://127.0.0.1:4096/'
```

Namespace writeability check:
```bash
pid="$(systemctl show -p MainPID --value opencode-web.service)"
sudo nsenter -t "$pid" -m -- bash -lc '
  set -e
  touch /home/christopherbailey/homelab-llm/.opencode-write-test
  rm /home/christopherbailey/homelab-llm/.opencode-write-test
  touch /home/christopherbailey/homelab-llm/.git/.opencode-git-write-test
  rm /home/christopherbailey/homelab-llm/.git/.opencode-git-write-test
'
```

Negative least-privilege check:
```bash
pid="$(systemctl show -p MainPID --value opencode-web.service)"
sudo nsenter -t "$pid" -m -- bash -lc 'touch /home/christopherbailey/.opencode-should-fail'
```

Expected:
- unauthenticated `GET /` returns `401`
- authenticated `GET /` returns `200`
- repo-root and `.git` writes succeed from inside the service mount namespace
- unrelated home-path write still fails

Tailnet exposure check:
```bash
tailscale serve status --json
curl -s -o /dev/null -w "%{http_code}\n" https://codeagent.tailfd1400.ts.net/
sudo bash -lc 'set -a; . /etc/opencode/env; user="${OPENCODE_SERVER_USERNAME:-opencode}"; curl -s -o /dev/null -w "%{http_code}\n" -u "$user:$OPENCODE_SERVER_PASSWORD" https://codeagent.tailfd1400.ts.net/'
```

Expected:
- top-level node `Web` has no `themini.tailfd1400.ts.net:443` entry for OpenCode
- `Services["svc:codeagent"].Web["codeagent.tailfd1400.ts.net:443"]` proxies to `http://127.0.0.1:4096`
- tailnet serve remains optional for remote operator access, not the canonical Mini ↔ Studio service path
- unauthenticated `GET /` on `https://codeagent.tailfd1400.ts.net/` returns `401`
- authenticated `GET /` on `https://codeagent.tailfd1400.ts.net/` returns `200`

## MLX Registry and Controller (Studio)

Current runtime baseline (per-port MLX lanes):
```bash
mlxctl init
mlxctl ensure <hf_repo_id> --convert auto
mlxctl list
mlxctl status
mlxctl verify
mlxctl studio-cli-sha
```

Notes:
- `mlxctl ensure` takes a Hugging Face repo id (example: `mlx-community/Qwen3-4B-Instruct-2507-gabliterated-mxfp4`).
  Use `mlxctl list` to discover canonical `mlx-*` model ids.
- `mlxctl verify` is read-only by default and also validates (on gateway hosts) that
  served MLX handles in `platform/registry/handles.jsonl` exist in the Studio registry.
- Use `mlxctl verify --fix-defaults` only when explicitly persisting inferred defaults.
- `mlxctl` now requires `platform/ops/mlx-runtime-profiles.json`; missing,
  invalid, or ambiguous profile resolution is a validation failure.

Expanded runtime inspection:
```bash
mlxctl status --checks
mlxctl status --checks --json
mlxctl status --json
mlxctl vllm-render --validate --json
```

`status --checks` includes `http_models_ok` so lanes can be considered healthy
even when `listener_visible=false` under root-owned launchd runtime.
For load transitions, the primary readiness proof is a successful minimal
non-streaming `/v1/chat/completions` probe. `/v1/models` is retained as the
served-model identity check.

Lane drift recovery (disabled/unloaded launchd labels):
```bash
mlxctl repair-lanes --json
mlxctl repair-lanes --apply --json
mlxctl status --checks --json
mlxctl verify
```

`repair-lanes` is safe to run from Mini; it fetches Studio registry/status and
applies launchctl actions on Studio only when `--apply` is used.

`mlx-launch-start --ports` now refuses partial assigned-team-lane scope by
default. Use `--allow-partial` only for intentional scoped restarts.

Lane load/unload:
```bash
mlxctl load <hf_repo_id_or_mlx_model_id> 8100
mlxctl status --checks
mlxctl unload 8100
mlxctl status --checks
```

Expected `load` behavior:
- `desired_target` updates immediately in lane state
- unsupported targets fail before a healthy lane is torn down
- success is declared only after two consecutive readiness passes with no restart between them
- failed loads never claim the new target is serving

Unload all ports:
```bash
mlxctl unload-all
```

Reconcile after reboot:
```bash
mlxctl reconcile --json
mlxctl reconcile --apply --json
```

## MLX lanes (Studio)
After reboot or launchd restart, confirm all active `mlxctl` assignments are serving
`/v1/models`.
Note: `GET /v1/models` on the Studio may return a local filesystem snapshot path
as the model `id`. Use `mlxctl status` for canonical model/port mapping.

As of `2026-03-19`, the expected public MLX lane is `8101`.
The old GPT rollback slots `8100` and `8102` remain `mlxctl`-governed but are
expected to be unloaded. Any deviation should be treated as drift and triaged
with `mlxctl status --checks` and `mlxctl verify`.

Canonical Mini -> Studio transport for active MLX team lanes is the Studio LAN
IP `192.168.1.72`.

Mini-side reachability check:

```bash
for p in 8101; do
  curl -fsS "http://192.168.1.72:${p}/v1/models" | jq .
done
```

```bash
ACTIVE_PORTS=$(ssh studio "mlxctl status --json | jq -r '.ports[] | select(.status==\"listening\" or .status==\"running\") | .port'")
for p in $ACTIVE_PORTS; do
  ssh studio "curl -fsS http://127.0.0.1:${p}/v1/models | jq ."
done
```

`main` tool-calling validation:
```bash
./platform/ops/scripts/mlxctl vllm-capabilities --json
./platform/ops/scripts/mlxctl vllm-render --ports 8101 --validate --json

ssh studio "python3 - <<'PY'
import json, urllib.request
payload={
  'model':'mlx-qwen3-next-80b-mxfp4-a3b-instruct',
  'messages':[{'role':'user','content':'Use the noop tool once, then stop.'}],
  'tools':[{'type':'function','function':{'name':'noop','description':'noop','parameters':{'type':'object','properties':{}}}}],
  'tool_choice':'auto',
  'stream':False,
  'max_tokens':128
}
req=urllib.request.Request(
  'http://127.0.0.1:8101/v1/chat/completions',
  data=json.dumps(payload).encode(),
  headers={'Content-Type':'application/json'},
  method='POST'
)
with urllib.request.urlopen(req, timeout=60) as r:
  body=json.loads(r.read().decode())
print(json.dumps(body['choices'][0]['message'], indent=2))
PY"
```

Expected:
- `tool_calls` is present and names `noop`
- response `content` does not contain raw `<tool_call>`

Direct backend argument-bearing auto probe:
```bash
ssh studio "python3 - <<'PY'
import json, urllib.request
payload={
  'model':'mlx-qwen3-next-80b-mxfp4-a3b-instruct',
  'messages':[{'role':'user','content':'Use the noop tool exactly once with a short JSON object argument.'}],
  'tools':[{'type':'function','function':{'name':'noop','description':'noop','parameters':{'type':'object','properties':{'value':{'type':'string'}},'required':['value'],'additionalProperties':False}}}],
  'tool_choice':'auto',
  'stream':False,
  'max_tokens':128
}
req=urllib.request.Request(
  'http://127.0.0.1:8101/v1/chat/completions',
  data=json.dumps(payload).encode(),
  headers={'Content-Type':'application/json'},
  method='POST'
)
with urllib.request.urlopen(req, timeout=60) as r:
  body=json.loads(r.read().decode())
print(json.dumps(body['choices'][0], indent=2))
PY"
```

Interpretation:
- native pass:
  - `tool_calls` is present and arguments parse as JSON containing `value`
- semantic but raw/recoverable:
  - direct backend returns exactly one `<tool_call>...</tool_call>` block with a
    JSON object payload and no extra prose
  - this is acceptable only if LiteLLM `main` post-call success-hook validation
    also passes
- semantic fail:
  - malformed JSON, extra prose, ambiguity, `5xx`, or timeout

`tool_choice="required"` and named forced-tool choice are advisory-only on the
current Qwen main lane and are not part of the public `main` acceptance gate.

`main` structured-output protocol validation (diagnostic only, not a closeout blocker):
```bash
ssh studio "python3 - <<'PY'
import json, urllib.request
schema={
  'type':'object',
  'properties':{'status':{'type':'string'}},
  'required':['status'],
  'additionalProperties':False
}
payload={
  'model':'mlx-qwen3-next-80b-mxfp4-a3b-instruct',
  'messages':[{'role':'user','content':'Return a JSON object that matches the schema exactly.'}],
  'response_format':{
    'type':'json_schema',
    'json_schema':{
      'name':'status_payload',
      'schema':schema
    }
  },
  'stream':False,
  'temperature':0,
  'max_tokens':128
}
req=urllib.request.Request(
  'http://127.0.0.1:8101/v1/chat/completions',
  data=json.dumps(payload).encode(),
  headers={'Content-Type':'application/json'},
  method='POST'
)
with urllib.request.urlopen(req, timeout=60) as r:
  body=json.loads(r.read().decode())
print(json.dumps(body['choices'][0]['message'], indent=2))
PY"

ssh studio "python3 - <<'PY'
import json, urllib.request
schema={
  'type':'object',
  'properties':{'status':{'type':'string'}},
  'required':['status'],
  'additionalProperties':False
}
payload={
  'model':'mlx-qwen3-next-80b-mxfp4-a3b-instruct',
  'messages':[{'role':'user','content':'Return a JSON object that matches the schema exactly.'}],
  'structured_outputs':{'json':schema},
  'stream':False,
  'temperature':0,
  'max_tokens':128
}
req=urllib.request.Request(
  'http://127.0.0.1:8101/v1/chat/completions',
  data=json.dumps(payload).encode(),
  headers={'Content-Type':'application/json'},
  method='POST'
)
with urllib.request.urlopen(req, timeout=60) as r:
  body=json.loads(r.read().decode())
print(json.dumps(body['choices'][0]['message'], indent=2))
PY"

bash -lc 'set -a && source /home/christopherbailey/homelab-llm/services/litellm-orch/config/env.local && set +a && python3 - <<'"'"'PY'"'"'
import json, os, urllib.request
schema={
  "type":"object",
  "properties":{"status":{"type":"string"}},
  "required":["status"],
  "additionalProperties":False
}
payload={
  "model":"main",
  "messages":[{"role":"user","content":"Return a JSON object that matches the schema exactly."}],
  "response_format":{
    "type":"json_schema",
    "json_schema":{
      "name":"status_payload",
      "schema":schema
    }
  },
  "stream":False,
  "temperature":0,
  "max_tokens":128
}
req=urllib.request.Request(
  "http://127.0.0.1:4000/v1/chat/completions",
  data=json.dumps(payload).encode(),
  headers={"Authorization": f"Bearer {os.environ['LITELLM_MASTER_KEY']}", "Content-Type":"application/json"},
  method="POST"
)
with urllib.request.urlopen(req, timeout=60) as r:
  body=json.loads(r.read().decode())
print(json.dumps(body["choices"][0]["message"], indent=2))
PY'
```

Expected current truth:
- direct `8101` exact documented `response_format.json_schema`: semantic FAIL
- direct `8101` exact `structured_outputs.json`: semantic FAIL
- LiteLLM `main` exact documented `response_format.json_schema`: semantic FAIL
- all three currently return HTTP `200` with assistant `content` equal to:
  `{"error":"No schema provided to match against."}`
- this is a backend-path structured-output gap on the current `8101` runtime,
  not a LiteLLM-only transport failure
- this probe remains useful as backend evidence, but it is not part of the
  accepted public `main` closeout gate

## Studio scheduling policy (Mini -> Studio)
This section is authoritative for Studio scheduling verification workflow.

Policy source of truth:
- `platform/ops/templates/studio_scheduling_policy.json`
- `docs/foundation/studio-scheduling-policy.md`

Quick path (recommended order):
1) `uv run python platform/ops/scripts/validate_studio_policy.py --json`
2) `uv run python platform/ops/scripts/audit_studio_scheduling.py --policy-only --json`
3) `uv run python platform/ops/scripts/audit_studio_scheduling.py --host studio --json`
4) optional read-only check: `uv run python platform/ops/scripts/enforce_studio_launchd_policy.py --host studio --json`
5) apply only when needed, in staged order (`optillm-proxy` then `mlx-lane.*`), then rerun strict audit

Deterministic local checks:
```bash
uv run python platform/ops/scripts/validate_studio_policy.py --json
uv run python platform/ops/scripts/audit_studio_scheduling.py --policy-only --json
```

Remote check-only:
```bash
uv run python platform/ops/scripts/enforce_studio_launchd_policy.py --host studio --json
uv run python platform/ops/scripts/audit_studio_scheduling.py --host studio --json
```

Robust plist key spot-check (no brittle exit-code presence test):
```bash
ssh studio "sudo -n plutil -convert json -o - /Library/LaunchDaemons/com.bebop.mlx-lane.8100.plist | jq '{ProcessType, Nice, LowPriorityIO, LowPriorityBackgroundIO}'"
ssh studio "sudo -n plutil -convert json -o - /Library/LaunchDaemons/com.bebop.mlx-lane.8101.plist | jq '{ProcessType, Nice, LowPriorityIO, LowPriorityBackgroundIO}'"
ssh studio "sudo -n plutil -convert json -o - /Library/LaunchDaemons/com.bebop.mlx-lane.8102.plist | jq '{ProcessType, Nice, LowPriorityIO, LowPriorityBackgroundIO}'"
ssh studio "sudo -n plutil -convert json -o - /Library/LaunchDaemons/com.bebop.optillm-proxy.plist | jq '{ProcessType, Nice, LowPriorityIO, LowPriorityBackgroundIO}'"
# Fallback if JSON conversion is unavailable:
ssh studio "sudo -n /usr/libexec/PlistBuddy -c 'Print :ProcessType' /Library/LaunchDaemons/com.bebop.mlx-lane.8100.plist"
ssh studio "sudo -n /usr/libexec/PlistBuddy -c 'Print :ProcessType' /Library/LaunchDaemons/com.bebop.mlx-lane.8101.plist"
ssh studio "sudo -n /usr/libexec/PlistBuddy -c 'Print :ProcessType' /Library/LaunchDaemons/com.bebop.mlx-lane.8102.plist"
ssh studio "sudo -n /usr/libexec/PlistBuddy -c 'Print :ProcessType' /Library/LaunchDaemons/com.bebop.optillm-proxy.plist"
```

Staged apply order:
1) `com.bebop.optillm-proxy` via:
   `uv run python platform/ops/scripts/enforce_studio_launchd_policy.py --host studio --apply --managed-label com.bebop.optillm-proxy --json`
2) validate
3) MLX lane labels via:
   `uv run python platform/ops/scripts/enforce_studio_launchd_policy.py --host studio --apply --managed-label com.bebop.mlx-lane.8100 --json`
   `uv run python platform/ops/scripts/enforce_studio_launchd_policy.py --host studio --apply --managed-label com.bebop.mlx-lane.8101 --json`
   `uv run python platform/ops/scripts/enforce_studio_launchd_policy.py --host studio --apply --managed-label com.bebop.mlx-lane.8102 --json`
4) full strict audit

### Studio main vector-store labels (background lane)
Studio memory store labels included in policy checks:
- `com.bebop.pgvector-main`
- `com.bebop.memory-api-main`
- `com.bebop.memory-ingest-nightly`
- `com.bebop.memory-backup-nightly`

Read-only audit checks:
```bash
uv run python platform/ops/scripts/validate_studio_policy.py --json
uv run python platform/ops/scripts/audit_studio_scheduling.py --host studio --json
ssh studio "sudo -n plutil -convert json -o - /Library/LaunchDaemons/com.bebop.pgvector-main.plist | jq '{ProcessType, Nice, LowPriorityIO, LowPriorityBackgroundIO}'"
ssh studio "sudo -n plutil -convert json -o - /Library/LaunchDaemons/com.bebop.memory-api-main.plist | jq '{ProcessType, Nice, LowPriorityIO, LowPriorityBackgroundIO}'"
```

Runtime smoke checks:
```bash
ssh studio "lsof -nP -iTCP -sTCP:LISTEN | egrep ':55432|:55440'"
ssh studio "curl -fsS http://127.0.0.1:55440/health | jq ."
```

### Studio vector-store retrieval quality gate (QG1)
Goal: tune retrieval defaults using a fixed judged query set while minimizing manual grading.

Canonical evaluation engine:
- `ir-measures` with pinned provider support via `pytrec-eval-terrier`

Artifact semantics:
- `run-pack` emits ranked retrieval output in `run.json`
- judgments stay in CSV, but scoring keys them by `(query_id, chunk_id)`, not by rank
- this keeps judgments portable across reranking as long as `chunk_id` identity is stable

Canonical metric mappings:
- `hit_at_5` -> `Success(rel=2, judged_only=False)@5`
- `mrr_at_10` -> `RR(rel=2, judged_only=False)@10`
- `ndcg_at_10` -> `nDCG(gains={0:0,1:1,2:3}, dcg='log2', judged_only=False)@10`
- `bad_hit_rate_at_5` -> `1 - P(rel=1, judged_only=False)@5`
- `p95_latency_ms` remains custom

Docs-pack workflow:
```bash
cd /home/christopherbailey/homelab-llm

platform/ops/scripts/studio_run_utility.sh --host studio -- \
  "cd /Users/thestudio/optillm-proxy && \
   uv run python services/vector-db/scripts/eval_memory_quality.py run-pack \
     --pack services/vector-db/eval/query_pack.docs.v1.jsonl \
     --api-base http://127.0.0.1:55440 \
     --model-space qwen \
     --top-k 10 \
     --lexical-k 30 \
     --vector-k 30 \
     --run-id D1 \
     --out /Users/thestudio/data/memory-main/eval/D1.run.json"

platform/ops/scripts/studio_run_utility.sh --host studio -- \
  "cd /Users/thestudio/optillm-proxy && \
   uv run python services/vector-db/scripts/eval_memory_quality.py autolabel \
     --run-json /Users/thestudio/data/memory-main/eval/D1.run.json \
     --out-csv /Users/thestudio/data/memory-main/eval/D1.judgments.auto.csv \
     --mode conservative_graded \
     --labeler codex-auto \
     --run-id D1"

platform/ops/scripts/studio_run_utility.sh --host studio -- \
  "cd /Users/thestudio/optillm-proxy && \
   uv run python services/vector-db/scripts/eval_memory_quality.py triage \
     --run-json /Users/thestudio/data/memory-main/eval/D1.run.json \
     --judgments /Users/thestudio/data/memory-main/eval/D1.judgments.auto.csv \
     --out /Users/thestudio/data/memory-main/eval/D1.triage.json"
```

Only if triage returns flagged query ids, review those cases interactively:
```bash
ssh -t studio "cd /Users/thestudio/optillm-proxy && \
   uv run python services/vector-db/scripts/eval_memory_quality.py label \
     --run-json /Users/thestudio/data/memory-main/eval/D1.run.json \
     --seed-judgments /Users/thestudio/data/memory-main/eval/D1.judgments.auto.csv \
     --triage-json /Users/thestudio/data/memory-main/eval/D1.triage.json \
     --out-csv /Users/thestudio/data/memory-main/eval/D1.judgments.final.csv \
     --labeler chris \
     --run-id D1"
```

If triage is empty, promote the auto labels directly:
```bash
platform/ops/scripts/studio_run_utility.sh --host studio -- \
  "cp /Users/thestudio/data/memory-main/eval/D1.judgments.auto.csv \
      /Users/thestudio/data/memory-main/eval/D1.judgments.final.csv"
```

Score on Studio:
```bash
platform/ops/scripts/studio_run_utility.sh --host studio -- \
  "cd /Users/thestudio/optillm-proxy && \
   uv run python services/vector-db/scripts/eval_memory_quality.py score \
     --run-json /Users/thestudio/data/memory-main/eval/D1.run.json \
     --judgments /Users/thestudio/data/memory-main/eval/D1.judgments.final.csv \
     --out /Users/thestudio/data/memory-main/eval/D1.score.json && \
   jq '{metrics_support,metrics_disconfirm,gates,diagnostics,bucket_hit_at_5_support}' \
      /Users/thestudio/data/memory-main/eval/D1.score.json"
```

Gate thresholds:
- support `hit_at_5 >= 0.85`
- support `mrr_at_10 >= 0.65`
- support `ndcg_at_10 >= 0.70`
- support buckets each `hit_at_5 >= 0.75`
- disconfirm `hit_at_5 >= 0.67`
- `p95_latency_ms <= 800`
- `bad_hit_rate_at_5` is diagnostic only

Runtime lineage check expectation:
- port `8101` listener is `vllm serve`
- process ancestry includes `com.bebop.mlx-lane.8101` lineage

Verify GPT‑OSS content channel is present on the canonical shared `8126` backend
(requires adequate max_tokens):
```bash
curl -fsS http://192.168.1.72:8126/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"llmster-gpt-oss-20b-mxfp4-gguf","messages":[{"role":"user","content":"ping"}],"reasoning_effort":"low","max_tokens":256}' \
  | jq -r '.choices[0].message | {content, reasoning}'
```

Verify `/v1/responses` on the canonical shared `8126` backend:
```bash
curl -fsS http://192.168.1.72:8126/v1/responses \
  -H "Content-Type: application/json" \
  -d '{"model":"llmster-gpt-oss-20b-mxfp4-gguf","input":"Reply with exactly: responses-ok","reasoning":{"effort":"low"}}' \
  | jq .
```

Smoke check for raw Harmony-tag leakage (should return no `<|channel|>`):
```bash
curl -fsS http://192.168.1.72:8126/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"llmster-gpt-oss-120b-mxfp4-gguf","messages":[{"role":"user","content":"Return one short sentence about oranges."}],"reasoning_effort":"low","max_tokens":128}' \
  | jq -r '.choices[0].message.content'
```

After any MLX served-set change (handles) or Studio registry/defaults change:
```bash
mlxctl sync-gateway
```

Quality gate (post-reboot / post-change):
```bash
mlxctl status --checks
mlxctl verify
uv run python /home/christopherbailey/homelab-llm/platform/ops/scripts/mlx_quality_gate.py --host thestudio.tailfd1400.ts.net --json
```

Expected:
- exit code `0`
- `failed: 0`
- no raw protocol markers in output (`<|channel|>`, `<think>`, tool tags)
- current golden fixture uses lane-specific budgets:
  - `deep`: `max_tokens=256`, `request_timeout_s=90`
  - `main`: `max_tokens=128`
  - `fast`: `max_tokens=256`, `request_timeout_s=90`


## LiteLLM Aliases (Mini)
```bash
curl -fsS http://127.0.0.1:4000/v1/models \
  -H "Authorization: Bearer $LITELLM_API_KEY" | jq .
```

Note: in the current deployment, unauthenticated `GET /health` may return `401`.
Prefer `/health/readiness` as the default probe when validating service liveness.

## OpenHands managed runtime (Mini)
```bash
systemctl is-enabled openhands.service
systemctl is-active openhands.service
ss -ltnp | rg ':4031'
curl -fsSI http://127.0.0.1:4031/
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}' | rg 'openhands-app'
docker inspect openhands-app --format '{{json .HostConfig.Binds}}'
docker inspect openhands-app --format '{{json .Config.Env}}' | jq -r '.[]' | rg '^SANDBOX_VOLUMES='
tailscale serve status --json | jq '.Services["svc:hands"]'
ssh orin 'curl -kI --max-time 10 https://hands.tailfd1400.ts.net/'
```

Expected:
- `openhands.service` is enabled and active
- `127.0.0.1:4031` is listening
- local root returns `200`
- `openhands-app` is running
- `docker inspect` shows only Docker socket and persistence binds
- `SANDBOX_VOLUMES` carries the disposable workspace contract
- `svc:hands` still proxies to `http://127.0.0.1:4031`
- remote tailnet root returns `HTTP/2 200`

## OpenHands Phase B note
OpenHands Phase B now has one governed worker contract only:
- alias: `code-reasoning`
- backend target: `deep`
- non-human service-account key only
- Chat Completions-first
- MCP denied
- `/v1/responses` denied

Worker-gate verification:
```bash
OPENHANDS_WORKER_KEY=$(cat /home/christopherbailey/.config/openhands/worker_api_key)

curl -fsS http://127.0.0.1:4000/v1/models \
  -H "Authorization: Bearer ${OPENHANDS_WORKER_KEY}" | jq .

curl -fsS http://127.0.0.1:4000/v1/model/info \
  -H "Authorization: Bearer ${OPENHANDS_WORKER_KEY}" | jq .

curl -fsS http://127.0.0.1:4000/model/info \
  -H "Authorization: Bearer ${OPENHANDS_WORKER_KEY}" | jq .

curl -fsS http://127.0.0.1:4000/v1/chat/completions \
  -H "Authorization: Bearer ${OPENHANDS_WORKER_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"model":"code-reasoning","messages":[{"role":"user","content":"Reply with exactly: code-reasoning-ok"}],"stream":false,"max_tokens":32}' | jq .

curl -sS -o /dev/null -w "%{http_code}\n" \
  http://127.0.0.1:4000/v1/mcp/tools \
  -H "Authorization: Bearer ${OPENHANDS_WORKER_KEY}"

curl -sS -o /dev/null -w "%{http_code}\n" \
  http://127.0.0.1:4000/v1/responses \
  -H "Authorization: Bearer ${OPENHANDS_WORKER_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"model":"code-reasoning","input":"hello"}'
```

Expected:
- models path returns only `code-reasoning`
- both model-info paths succeed
- chat completions succeeds on `code-reasoning`
- MCP returns `403`
- `/v1/responses` returns `403`

Inside-container authenticated OpenHands contract check:
```bash
OPENHANDS_WORKER_KEY=$(cat /home/christopherbailey/.config/openhands/worker_api_key)

docker exec -e OPENHANDS_WORKER_KEY="$OPENHANDS_WORKER_KEY" openhands-app sh -lc '
python3 - <<\"PY\"
import json, os, urllib.request, urllib.error
key=os.environ["OPENHANDS_WORKER_KEY"]
bases=["http://host.docker.internal:4000/v1","http://192.168.1.71:4000/v1"]
tests={
  "models":("GET","/models",None),
  "model_info":("GET","/model/info",None),
  "chat_ok":("POST","/chat/completions",{"model":"code-reasoning","messages":[{"role":"user","content":"Reply with exactly code-reasoning-ok"}],"stream":False,"max_tokens":32}),
  "mcp_denied":("GET","/mcp/tools",None),
  "responses_denied":("POST","/responses",{"model":"code-reasoning","input":"hello"})
}
out={}
for base in bases:
  out[base]={}
  for name,(method,path,payload) in tests.items():
    req=urllib.request.Request(base+path,data=(json.dumps(payload).encode() if payload is not None else None),headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"},method=method)
    try:
      with urllib.request.urlopen(req, timeout=30) as r:
        out[base][name]={"status":r.status,"body":r.read().decode()[:600]}
    except urllib.error.HTTPError as e:
      out[base][name]={"status":e.code,"body":e.read().decode()[:600]}
print(json.dumps(out, indent=2, sort_keys=True))
PY'
```

Expected:
- both paths return `200` for `/v1/models`
- both paths return `200` for `/v1/model/info`
- both paths return `200` for `/v1/chat/completions`
- `host.docker.internal` is promoted to canonical only after this authenticated
  inside-container check passes
- both paths return `403` for `/v1/mcp/tools`
- both paths return `403` for `/v1/responses`

Unsupported-feature probes:
```bash
OPENHANDS_WORKER_KEY=$(cat /home/christopherbailey/.config/openhands/worker_api_key)

curl -sS http://127.0.0.1:4000/v1/chat/completions \
  -H "Authorization: Bearer ${OPENHANDS_WORKER_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model":"code-reasoning",
    "messages":[{"role":"user","content":"Call noop once with {\"value\":\"x\"}."}],
    "tools":[{"type":"function","function":{"name":"noop","description":"noop","parameters":{"type":"object","properties":{"value":{"type":"string"}},"required":["value"],"additionalProperties":false}}}],
    "tool_choice":{"type":"function","function":{"name":"noop"}},
    "stream":false,
    "max_tokens":128
  }' | jq .

curl -sS http://127.0.0.1:4000/v1/chat/completions \
  -H "Authorization: Bearer ${OPENHANDS_WORKER_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model":"code-reasoning",
    "messages":[{"role":"user","content":"Return JSON matching the schema exactly."}],
    "response_format":{
      "type":"json_schema",
      "json_schema":{
        "name":"status_payload",
        "schema":{"type":"object","properties":{"status":{"type":"string"}},"required":["status"],"additionalProperties":false},
        "strict":true
      }
    },
    "stream":false,
    "max_tokens":128,
    "temperature":0
  }' | jq .
```

## CCProxy experimental lane
`chatgpt-5` is now backed by Mini-local `ccproxy-api` for Open WebUI testing.

Validation:
```bash
source /etc/homelab-llm/ccproxy.env
source /home/christopherbailey/homelab-llm/services/litellm-orch/config/env.local

curl -fsS -H "Authorization: Bearer ${CCPROXY_AUTH_TOKEN}" \
  http://127.0.0.1:4010/codex/v1/models | jq .

curl -fsS -H "Authorization: Bearer ${CCPROXY_AUTH_TOKEN}" \
  -H "Content-Type: application/json" \
  http://127.0.0.1:4010/codex/v1/chat/completions \
  -d '{"model":"gpt-5.3-codex","messages":[{"role":"user","content":"Reply with exactly: ccproxy-chat-ok"}],"stream":false,"max_tokens":32}' | jq .

curl -fsS -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" \
  -H "Content-Type: application/json" \
  http://127.0.0.1:4000/v1/chat/completions \
  -d '{"model":"chatgpt-5","messages":[{"role":"user","content":"Reply with exactly: litellm-chat-ok"}],"stream":false,"max_tokens":32}' | jq .
```

Expected:
- `ccproxy-api` returns Codex models on `/codex/v1/models`
- direct CCProxy Chat Completions returns non-empty assistant content
- LiteLLM `chatgpt-5` Chat Completions returns non-empty assistant content

Expected:
- named/object-form forced-tool choice is rejected or backend-visible unsupported
- strict structured-output/schema guarantee is rejected, ignored, or otherwise
  not part of the supported worker contract

## Open Terminal MCP read-only slice
Direct backend smoke:
```bash
/home/christopherbailey/homelab-llm/layer-interface/open-webui/.venv/bin/python - <<'PY'
import asyncio
from open_webui.utils.mcp.client import MCPClient

async def main():
    client = MCPClient()
    await client.connect("http://127.0.0.1:8011/mcp")
    tools = await client.list_tool_specs()
    print(sorted(tool["name"] for tool in tools))
    await client.disconnect()

asyncio.run(main())
PY
```

Expected:
- connection succeeds
- raw backend exposes the 13-tool Open Terminal MCP surface
- direct backend remains localhost-only and should not be treated as the
  primary durable auth boundary

Direct backend path-compatibility probe:
```bash
/home/christopherbailey/homelab-llm/layer-interface/open-webui/.venv/bin/python - <<'PY'
import asyncio
from open_webui.utils.mcp.client import MCPClient

PATHS = [
    ".",
    "/homelab-llm",
    "/home/christopherbailey/homelab-llm",
    "/services/litellm-orch",
]

async def main():
    client = MCPClient()
    await client.connect("http://127.0.0.1:8011/mcp")
    try:
        for directory in PATHS:
            result = await client.call_tool("list_files", {"directory": directory})
            print(directory, result[0]["text"][:200])
    finally:
        await client.disconnect()

asyncio.run(main())
PY
```

Expected:
- all listed paths succeed without `Directory not found`
- compatibility aliases are accepted for host-style absolute repo paths and
  root-level repo directories while repo-relative paths remain the preferred
  caller contract

Open WebUI direct registration smoke:
```bash
python3 - <<'PY'
import sqlite3, urllib.request
conn = sqlite3.connect('/home/christopherbailey/.open-webui/webui.db')
cur = conn.cursor()
api_key = cur.execute('select key from api_key order by created_at asc limit 1').fetchone()[0]
headers = {'Authorization': f'Bearer {api_key}'}
for path in ['api/v1/terminals/', 'api/v1/tools/']:
    req = urllib.request.Request(f'http://127.0.0.1:3000/{path}', headers=headers)
    with urllib.request.urlopen(req, timeout=20) as resp:
        print(path, resp.read().decode())
PY
```

Expected:
- `/api/v1/terminals/` lists `open-terminal`
- `/api/v1/tools/` lists `server:mcp:open-terminal-mcp-ro`

Open WebUI MCP verify smoke:
```bash
python3 - <<'PY'
import sqlite3, json, urllib.request
conn = sqlite3.connect('/home/christopherbailey/.open-webui/webui.db')
cur = conn.cursor()
api_key = cur.execute('select key from api_key order by created_at asc limit 1').fetchone()[0]
payload = {
    "url": "http://127.0.0.1:8011/mcp",
    "path": "",
    "type": "mcp",
    "auth_type": "none",
    "key": "",
    "config": {
        "enable": True,
        "function_name_filter_list": "health_check,list_files,read_file,grep_search,glob_search",
        "access_grants": []
    },
    "info": {"id": "open-terminal-mcp-ro", "name": "Open Terminal MCP (Read Only)"}
}
req = urllib.request.Request(
    'http://127.0.0.1:3000/api/v1/configs/tool_servers/verify',
    data=json.dumps(payload).encode(),
    headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
)
with urllib.request.urlopen(req, timeout=20) as resp:
    print(resp.read().decode())
PY
```

Expected:
- verify succeeds against `127.0.0.1:8011/mcp`
- Open WebUI is configured to filter tool use down to `health_check`,
  `list_files`, `read_file`, `grep_search`, and `glob_search`

Shared LiteLLM exposure for the Open Terminal read-only subset is follow-on
work and is not part of the current live runtime. Validate the direct localhost
MCP backend on `127.0.0.1:8011/mcp` and the direct Open WebUI registration on
the Mini in this slice.

OpenHands denial proof must still hold:
```bash
OPENHANDS_WORKER_KEY=$(cat /home/christopherbailey/.config/openhands/worker_api_key)

curl -sS -o /dev/null -w "%{http_code}\n" \
  http://127.0.0.1:4000/v1/mcp/tools \
  -H "Authorization: Bearer ${OPENHANDS_WORKER_KEY}"
```

Expected:
- returns `403`

## Documentation predictability sweep (repo)
Use this when running doc-consistency hardening work for coding-agent safety.

```bash
cd /home/christopherbailey/homelab-llm
uv run python scripts/docs_contract_audit.py --strict --json
uv run python scripts/repo_hygiene_audit.py --scope root --strict --json
uv run python scripts/repo_hygiene_audit.py --scope journal --json
uv run python scripts/repo_hygiene_audit.py --scope archive --json
uv run python scripts/control_plane_sync_audit.py --json
uv run python scripts/validate_handles.py
```

Expected:
- `docs_contract_audit.py` returns `ok: true` with `services_with_gaps: 0`.
- `docs_contract_audit.py` also returns `layers_ok: true` and `overall_ok: true`
  with README-only layer taxonomy surfaces.
- root strict mode returns `root_ok: true` and `overall_ok: true`.
- journal advisory mode returns `journal_index_ok: true`.
- archive advisory mode returns `archive_ok: true`.
- `control_plane_sync_audit.py` returns `repo_hygiene_sync_ok: true`,
  `skill_sync_ok: true`, and `overall_ok: true`.
- treat root failures as blocking because they change the repo entry surface
  agents see before descending into layers and services.
- treat journal/archive/control-plane findings as advisory until those contracts
  stay quiet through at least one cleanup cycle.
- `validate_handles.py` returns `ok`.

## Concurrent implementation preflight (local only)
Use this before `Build` or `Verify` work when multiple agent efforts may be
active.

```bash
cd /home/christopherbailey/homelab-llm
uv run python scripts/worktree_effort.py status --json
uv run python scripts/start_effort.py --id demo --scope docs --json
uv run python scripts/start_effort.py --id demo-service --service open-webui --json
uv run python scripts/worktree_effort.py park --notes "holding context" --json
uv run python scripts/worktree_effort.py register --effort-id bad --stage build --scope docs --json
uv run python scripts/worktree_effort.py preflight --stage build --json
uv run python scripts/worktree_effort.py preflight --stage verify --json
uv run python scripts/worktree_effort.py close --json
uv run python scripts/closeout_effort.py --worktree /home/christopherbailey/homelab-llm-demo --json
uv run python scripts/abandon_effort.py --worktree /home/christopherbailey/homelab-llm-demo --json
uv run python scripts/abandon_effort.py --worktree /home/christopherbailey/homelab-llm-demo --salvage-journal --json
uv run python scripts/service_registry_audit.py --strict --json
uv run python scripts/docs_link_audit.py
```

Expected:
- `status --json` identifies the current worktree, branch, gitdir, and local
  effort metadata when present, and reports whether the primary worktree
  baseline is healthy.
- `start_effort.py` succeeds only from a clean primary worktree on `master` and
  creates the linked worktree that will own the implementation effort. It also
  fails before leaving a blocked placeholder lane behind.
- `start_effort.py --service <service-id>` resolves the current canonical path
  through `platform/registry/services.jsonl` before overlap checks run.
- broad parallel docs/layer scopes are rejected while another implementation
  lane is active.
- `park --notes ... --json` marks a dirty context worktree as parked without
  making it an implementation effort; a parked primary worktree is still a
  degraded baseline state.
- `register --stage build` in the primary worktree fails because the primary
  worktree is baseline-only.
- `preflight --stage build --json` returns `overall_ok: true` before any
  repo-mutating implementation work in a linked worktree, and fails in the
  primary worktree.
- `preflight --stage verify --json` returns `overall_ok: true` before
  verification-stage mutations in a linked worktree, and fails in the primary
  worktree.
- `close --json` removes local metadata and returns the worktree to a null
  state, but is metadata-only.
- `closeout_effort.py` stages scoped lane changes, commits if needed,
  fast-forward merges to `master`, closes metadata, removes the linked
  worktree, and deletes the local branch.
- `closeout_effort.py` does not auto-rebase and does not update `NOW.md`.
- `abandon_effort.py` removes failed lanes only when no journal records would be
  lost; `--salvage-journal` lands journal-only records on `master` first.
- first-party services under `layer-*` are plain tracked directories, so
  lane bootstrap and closeout do not require submodule sync or gitlink checks.
- `service_registry_audit.py` hard-fails if a discovered `SERVICE_SPEC.md`
  service root is missing from the service registry.
- `docs_link_audit.py` validates internal markdown links on the supported
  documentation surface.
- these checks are local-only and are not CI-backed, because CI cannot see your
  live worktree topology.

## OpenCode repo-local control-plane smoke
Use your local `~/.config/opencode/opencode.json` together with the repo-local
`opencode.json` and `.opencode/*` files:
```bash
find .opencode -maxdepth 3 -type f | sort
sed -n '1,220p' opencode.json
opencode models litellm
opencode run --agent repo-deep "Inspect docs/OPENCODE.md and reply with exactly: repo-deep-ok"
```

Expected:
- `repo-deep` succeeds with grounded repo access.
- The repo-local OpenCode control surface is present on disk.

## Direct lane canary checks
Use these when validating machine-local lane readiness. `deep` is the required
baseline. `main` and `fast` are canary probes and may legitimately fail with
`litellm.NotFoundError` until backend provisioning and flags are ready.
```bash
opencode run -m litellm/deep "Reply with exactly: deep-ok"
opencode run -m litellm/main "Reply with exactly: main-ok"
opencode run -m litellm/fast "Reply with exactly: fast-ok"
```

Expected:
- `deep` passes when the machine-local `litellm` provider is configured.
- `main` and `fast` are recorded as canary results; a `NotFoundError` indicates
  lane-readiness work remains, not a repo-control-plane documentation failure.

Backend preflight for `main` tool-calling:
```bash
./platform/ops/scripts/mlxctl vllm-capabilities --json
./platform/ops/scripts/mlxctl vllm-render --ports 8101 --validate --json
```

If `main` still fails with a parser/auto-tool error, verify lane args directly:
```bash
ssh studio "ps -eo pid,command | rg -- '--port 8101|enable-auto-tool-choice|tool-call-parser'"
```

Direct lane smoke for `tool_choice:\"auto\"`:
```bash
ssh studio "python3 - <<'PY'
import json, urllib.request
payload={
  'model':'mlx-qwen3-next-80b-mxfp4-a3b-instruct',
  'messages':[{'role':'user','content':'Reply with exactly: main-tool-ok'}],
  'tools':[{'type':'function','function':{'name':'noop','description':'noop','parameters':{'type':'object','properties':{}}}}],
  'tool_choice':'auto',
  'max_tokens':32
}
req=urllib.request.Request(
  'http://127.0.0.1:8101/v1/chat/completions',
  data=json.dumps(payload).encode(),
  headers={'Content-Type':'application/json'},
  method='POST',
)
with urllib.request.urlopen(req, timeout=30) as r:
  print(r.status)
PY"
```

## LiteLLM Prometheus (Mini)
```bash
curl -fsS -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  http://127.0.0.1:4000/metrics/ | head -n 20
```
Note: `/metrics` redirects to `/metrics/` (307).

## Prometheus (Mini)
```bash
curl -fsS http://127.0.0.1:9090/-/ready
curl -fsS http://127.0.0.1:9090/-/healthy
```

## Grafana (Mini)
```bash
curl -fsS http://127.0.0.1:3001/api/health
```

Check for MLX aliases:
```bash
curl -fsS http://127.0.0.1:4000/v1/models \
  -H "Authorization: Bearer $LITELLM_API_KEY" \
  | jq -r '.data[].id' | rg '^mlx-'
```

Check for OpenVINO aliases (only when OpenVINO is intentionally wired into LiteLLM):
```bash
curl -fsS http://127.0.0.1:4000/v1/models \
  -H "Authorization: Bearer $LITELLM_API_KEY" \
  | jq -r '.data[].id' | rg '^ov-'
```

## OptiLLM via LiteLLM `boost` (Mini)
Confirm `boost` handle is present:
```bash
curl -fsS http://127.0.0.1:4000/v1/models \
  -H "Authorization: Bearer $LITELLM_API_KEY" \
  | jq -r '.data[].id' | rg '^boost$'
```

Then send a request through `boost` (Studio OptiLLM proxy path) and confirm a 200 response:
```bash
curl -fsS http://127.0.0.1:4000/v1/chat/completions \
  -H "Authorization: Bearer $LITELLM_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"boost","messages":[{"role":"user","content":"ping"}],"max_tokens":16}' \
  | jq .
```

Then send a request through `boost` (Studio OptiLLM proxy path):
```bash
curl -fsS http://127.0.0.1:4000/v1/chat/completions \
  -H "Authorization: Bearer $LITELLM_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"boost","messages":[{"role":"user","content":"ping"}],"max_tokens":16}' \
  | jq .
```

### PlanSearchTrio blind quality gate (`boost-plan` vs `boost-plan-trio`)
Use this flow when validating quality impact (not just latency/sentinel health):

1) Capture paired outputs:
```bash
cd /home/christopherbailey/homelab-llm/services/optillm-proxy
./scripts/ab_capture_plansearch.py \
  --url http://127.0.0.1:4000/v1/chat/completions \
  --bearer "$LITELLM_API_KEY" \
  --model-a boost-plan \
  --model-b boost-plan-trio \
  --model-b-extra-json '{"plansearchtrio_mode":"auto","plansearchtrio_latency_budget_ms":17000,"plansearchtrio_reasoning_effort_synthesis":"high","plansearchtrio_reasoning_effort_rewrite":"high"}' \
  --max-tokens 220 \
  --prompts ./scripts/canary_prompts_plansearch.txt \
  --out-jsonl /tmp/plansearchtrio_ab_capture.jsonl \
  --summary-json /tmp/plansearchtrio_ab_capture_summary.json
```

2) Build a blinded human-scoring packet:
```bash
cd /home/christopherbailey/homelab-llm/services/optillm-proxy
./scripts/ab_blind_packet.py \
  --capture-jsonl /tmp/plansearchtrio_ab_capture.jsonl \
  --out-csv /tmp/plansearchtrio_blind_score.csv \
  --out-key-json /tmp/plansearchtrio_blind_key.json \
  --seed 42
```

3) Score each row in `/tmp/plansearchtrio_blind_score.csv`:
- `winner` must be `A`, `B`, or `TIE`.

4) Compute model-level summary:
```bash
cd /home/christopherbailey/homelab-llm/services/optillm-proxy
./scripts/ab_score_blind.py \
  --scored-csv /tmp/plansearchtrio_blind_score.csv \
  --key-json /tmp/plansearchtrio_blind_key.json \
  --baseline-model boost-plan \
  --candidate-model boost-plan-trio \
  --out-json /tmp/plansearchtrio_blind_score_summary.json
```

Suggested quality gate:
- `candidate_win_rate_decisive >= 0.55`

## OptiLLM proxy (Studio)
```bash
curl -fsS http://192.168.1.72:4020/v1/models | jq .
```
Note: missing the `Authorization` header returns `Invalid Authorization header`.

## Orin (identity + current baseline checks)
```bash
ssh orin 'hostnamectl --static; hostname -I | awk "{print $1}"'
ssh orin 'cat /etc/os-release | sed -n "1,6p"; cat /etc/nv_tegra_release 2>/dev/null || true'
ssh orin 'ss -ltnp'
ssh orin 'findmnt /mnt/seagate -R -o TARGET,SOURCE,FSTYPE,OPTIONS || true'
ssh orin 'arecord -l; aplay -l'
ssh orin 'command -v python3; python3 --version; command -v uv || test -x /home/christopherbailey/.local/bin/uv && echo /home/christopherbailey/.local/bin/uv; command -v ffmpeg || true'
ssh orin 'sudo nvpmodel -q 2>/dev/null || true; sudo jetson_clocks --show 2>/dev/null || true'
ssh orin 'sudo docker ps -a --format "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}" || true'
```

## Voice Gateway Speech Appliance (Orin)
The canonical speech loop is now:

`Open WebUI -> LiteLLM -> voice-gateway -> Speaches`

Use direct Mini -> Orin LAN routing through `voice-gateway`. Do not add a Mini
port-forward layer. Speaches stays localhost-only behind `voice-gateway`.

Required Speaches appliance policy:
```dotenv
PRELOAD_MODELS=["Systran/faster-distil-whisper-large-v3","speaches-ai/Kokoro-82M-v1.0-ONNX"]
STT_MODEL_TTL=-1
TTS_MODEL_TTL=-1
```

Direct Orin speech facade checks:
```bash
curl -fsS http://192.168.1.93:18080/health
curl -fsS http://192.168.1.93:18080/health/readiness | jq .
curl -fsS http://192.168.1.93:18080/v1/models -H "Authorization: Bearer ${VOICE_GATEWAY_API_KEY}" | jq .
curl -fsS http://192.168.1.93:18080/v1/speakers -H "Authorization: Bearer ${VOICE_GATEWAY_API_KEY}" | jq .
curl -fsS http://192.168.1.93:18080/v1/audio/speech   -H "Authorization: Bearer ${VOICE_GATEWAY_API_KEY}"   -H "Content-Type: application/json"   -d '{"model":"tts-1","input":"Homelab speech canary.","voice":"alloy","response_format":"wav","speed":1.0}'   --output /tmp/voice-gateway-canary.wav
curl -fsS http://192.168.1.93:18080/v1/audio/transcriptions   -H "Authorization: Bearer ${VOICE_GATEWAY_API_KEY}"   -F 'file=@/tmp/voice-gateway-canary.wav'   -F 'model=whisper-1'
```

Voice alias acceptance checks:
```bash
curl -fsS http://192.168.1.93:18080/v1/speakers -H "Authorization: Bearer ${VOICE_GATEWAY_API_KEY}" | jq .
curl -sS -o /dev/null -w "%{http_code}\n" http://192.168.1.93:18080/v1/audio/speech   -H "Authorization: Bearer ${VOICE_GATEWAY_API_KEY}"   -H "Content-Type: application/json"   -d '{"model":"tts-1","input":"voice policy check","voice":"unknown","response_format":"wav","speed":1.0}'
```

Expected:
- `default` and `alloy` resolve to the same initial Kokoro backend voice
- unknown voices return clean `400` by default, unless config explicitly enables fallback

Control-plane checks:
```bash
curl -fsS http://192.168.1.93:18080/ops >/dev/null
curl -fsS http://192.168.1.93:18080/ops/api/registry/curated -H "Authorization: Bearer ${VOICE_GATEWAY_API_KEY}" | jq .
curl -fsS http://192.168.1.93:18080/ops/api/state -H "Authorization: Bearer ${VOICE_GATEWAY_API_KEY}" | jq '.curated_registry, .deploy_manifest'

# deploy checkout CLI smoke (run on Orin)
PYTHONPATH=/home/christopherbailey/voice-gateway-canary/src \
  python3 -m voice_gateway.ops_cli registry-list
PYTHONPATH=/home/christopherbailey/voice-gateway-canary/src \
  python3 -m voice_gateway.ops_cli --base-url http://192.168.1.93:18080 --api-key "${VOICE_GATEWAY_API_KEY}" status
```

## LiteLLM speech canary (Mini)
```bash
source /home/christopherbailey/homelab-llm/services/litellm-orch/config/env.local

curl -fsS http://127.0.0.1:4000/v1/audio/speech   -H "Authorization: Bearer ${LITELLM_MASTER_KEY}"   -H "Content-Type: application/json"   -d '{"model":"voice-tts-canary","input":"LiteLLM speech canary.","voice":"alloy","response_format":"wav","speed":1.0}'   --output /tmp/litellm-voice-canary.wav

curl -fsS http://127.0.0.1:4000/v1/audio/transcriptions   -H "Authorization: Bearer ${LITELLM_MASTER_KEY}"   -F 'file=@/tmp/litellm-voice-canary.wav'   -F 'model=voice-stt-canary'
```

## Open WebUI voice canary
Target values:
```bash
AUDIO_STT_ENGINE=openai
AUDIO_STT_OPENAI_API_BASE_URL=http://127.0.0.1:4000/v1
AUDIO_STT_MODEL=voice-stt-canary
AUDIO_TTS_ENGINE=openai
AUDIO_TTS_OPENAI_API_BASE_URL=http://127.0.0.1:4000/v1
AUDIO_TTS_MODEL=voice-tts-canary
AUDIO_TTS_VOICE=alloy
```

Post-restart verification is required:
```bash
systemctl show -p Environment open-webui.service --no-pager | tr ' ' '\n' | rg '^"?AUDIO_STT_'
systemctl show -p Environment open-webui.service --no-pager | tr ' ' '\n' | rg '^"?AUDIO_TTS_'
curl -fsS http://127.0.0.1:3000/health | jq .
```

Promotion is blocked if stale Admin UI audio state overrides the env-backed values
after restart.

## Diarization promotion gate
Do not promote any diarization-capable enriched transcription format until an
end-to-end test proves it survives the LiteLLM/OpenAI-compatible transcription
path without breaking clients.

Verify OptiLLM directly (Mini): see “OptiLLM via LiteLLM `boost` (Mini)” above.

## OpenVINO (Mini)
```bash
curl -fsS http://127.0.0.1:9000/health | jq .
```

## OpenVINO device mode evaluation (Mini)
Test latency and throughput with the same 1500-char input:
```bash
# GPU only (current)
sudo sed -i 's/^OV_DEVICE=.*/OV_DEVICE=GPU/' /etc/homelab-llm/ov-server.env
sudo systemctl restart ov-server.service

# AUTO
sudo sed -i 's/^OV_DEVICE=.*/OV_DEVICE=AUTO/' /etc/homelab-llm/ov-server.env
sudo systemctl restart ov-server.service

# MULTI CPU+GPU
sudo sed -i 's/^OV_DEVICE=.*/OV_DEVICE=MULTI:GPU,CPU/' /etc/homelab-llm/ov-server.env
sudo systemctl restart ov-server.service
```

## Non-LLM pilot tests (Mini)
Run and capture timing + quality notes:
```bash
platform/ops/.venv-onnx/bin/python /home/christopherbailey/homelab-llm/platform/ops/scripts/onnx_eval.py
platform/ops/.venv-onnx/bin/python /home/christopherbailey/homelab-llm/platform/ops/scripts/clean_punct_onnx.py
```

## STT/TTS/Vision evaluation (planned)
Track candidate models, ports, and benchmarks in `docs/journal/`.

## AFM (Studio, planned)
Once the AFM OpenAI-compatible API is running:
```bash
curl -fsS http://192.168.1.72:9999/v1/models | jq .
```

## SearXNG (Mini, once installed)
```bash
curl -fsS "http://127.0.0.1:8888/search?q=ping&format=json" | jq .
```

## Samba SMB (Mini Finder)
```bash
sudo testparm -s | rg 'interfaces =|bind interfaces only =|map to guest =|server min protocol ='
sudo testparm -s | sed -n '/\\[mini-root\\]/,/^\\[/p'
sudo testparm -s | sed -n '/\\[seagate\\]/,/^\\[/p'
sudo pdbedit -L | rg '^christopherbailey:'
sudo systemctl --no-pager --full status smbd.service nmbd.service
sudo journalctl -u smbd -u nmbd -n 50 --no-pager
```

Finder manual checks from the MacBook:
- Connect with `Cmd-K` to `smb://192.168.1.71/mini-root`
- Connect with `Cmd-K` to `smb://192.168.1.71/seagate`
- Browse `/home`, `/mnt`, `/etc`, `/usr`
- Create and delete a test file in `/home/christopherbailey/Downloads`
- Create and delete a test file in `/mnt/seagate/backups`
- Verify writes to `/etc` fail

## Open WebUI Web Search Phase A Baseline (Mini, end-user flow)
Goal: verify baseline search viability before adding rerankers/vector stores.

1) Generate a run-specific prompt pack:
```bash
cd /home/christopherbailey/homelab-llm
python3 scripts/openwebui_phase_a_baseline.py print-pack --run-id PHASEA-001
```

2) Programmatic run (recommended for speed/repeatability):
```bash
cd /home/christopherbailey/homelab-llm
export OWUI_API_KEY=<your_openwebui_api_key>
python3 scripts/openwebui_phase_a_baseline.py run-pack --run-id PHASEA-001 --model fast
```

3) End-user test in Open WebUI (manual alternative):
- Open the UI normally.
- Ensure web search is enabled for the chat.
- Send each printed prompt as a separate message (keep `[PHASEA-001:Qxx]` prefix intact).

4) Score from logs:
```bash
cd /home/christopherbailey/homelab-llm
python3 scripts/openwebui_phase_a_baseline.py score --run-id PHASEA-001 --since "45 minutes ago"
```

5) Fresh proof check (most recent activity only):
```bash
sudo journalctl -u open-webui.service --since "2 minutes ago" --no-pager \
  | rg -n 'OWUI_SEARXNG_RAW_JSON|source id=|web search|loader|fetch'
```

Pass guidance:
- `searx_rate_limit_or_429_errors == 0`
- `phase2_quality.poisoned_query_events == 0`
- `phase2_quality.grounding_warn_rate <= 0.10` (when present)
- `phase2_quality.citation_map_ready_rate >= 0.90` (when present)

If pass criteria fail, fix retrieval/extraction baseline first and re-run Phase A.

## Open WebUI Native Web Search (Mini)
Config authority checks:
```bash
systemctl show -p Environment open-webui.service --no-pager | rg -n \
  'ENABLE_WEB_SEARCH=True|WEB_SEARCH_ENGINE=searxng|SEARXNG_QUERY_URL=http://127.0.0.1:8888/search\\?q=<query>&format=json|WEB_SEARCH_RESULT_COUNT=6|WEB_SEARCH_CONCURRENT_REQUESTS=1|WEB_LOADER_ENGINE=safe_web|WEB_LOADER_TIMEOUT=15|WEB_LOADER_CONCURRENT_REQUESTS=2|WEB_FETCH_FILTER_LIST=|WEB_SEARCH_DOMAIN_FILTER_LIST='

systemctl show -p Environment open-webui.service --no-pager | rg -n \
  'EXTERNAL_WEB_LOADER_URL|SEARXNG_QUERY_URL=http://127.0.0.1:8899/search\\?q=<query>|WEB_LOADER_ENGINE=external'
```

SearXNG JSON smoke:
```bash
curl -fsS "http://127.0.0.1:8888/search?q=openwebui+searxng&format=json" \
  | jq '{count:(.results|length), first:(.results[0] // {}) | {title, url}}'
```

Open WebUI end-to-end smoke:
```bash
export OWUI_API_KEY='<open-webui-api-key>'
curl -N -fsS http://127.0.0.1:3000/api/chat/completions \
  -H "Authorization: Bearer ${OWUI_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model":"fast",
    "stream":true,
    "messages":[{"role":"user","content":"Search the web for two recent Open WebUI and SearXNG references and summarize them in two bullets."}],
    "features":{"web_search":true}
  }' | tee /tmp/owui-websearch-smoke.ndjson

rg -n '"type": "web_search"|"type":"web_search"|"sources": \\[' /tmp/owui-websearch-smoke.ndjson
rg -n '"content"|"delta"' /tmp/owui-websearch-smoke.ndjson | tail -n 40
```

Pass guidance:
- `WEB_SEARCH_ENGINE=searxng` and `WEB_LOADER_ENGINE=safe_web` are present.
- Result count, concurrency, and filter-list controls are visible in the service environment.
- No `EXTERNAL_WEB_LOADER_URL`, `WEB_LOADER_ENGINE=external`, or `:8899/search` reference remains.
- The SearXNG smoke returns at least one result.
- The Open WebUI stream shows a `sources` event with `type: "web_search"` and returns assistant content.
- If this host is not running `ENABLE_PERSISTENT_CONFIG=False`, treat any
  drop-in-based web-search tuning as a separate migration task rather than an
  assumed supported path.

## Promptfoo Web Search Eval Baseline (Mini)
Purpose:
- measure the supported Open WebUI web-search path without adding middleware
- compare the current lanes (`owui-fast`, `owui-research`) using repo-tracked data
- lock the winning lane first, then tune only `WEB_SEARCH_DOMAIN_FILTER_LIST`
- keep artifacts outside git under `evals/websearch/artifacts/`

Tracked files:
- config: `evals/websearch/promptfooconfig.yaml`
- dataset: `evals/websearch/queries.jsonl`
- assertions: `evals/websearch/assertions.py`
- blocked-domain policy: `evals/websearch/blocked_domains.txt`
- provider: `evals/websearch/providers/owui_websearch.py`
- scoring template: `evals/websearch/scoring_template.csv`
- tuning manifest: `evals/websearch/owui_tuning_matrix.yaml`

Pinned promptfoo version:
- use `npx promptfoo@0.120.27`
- this version was validated on Mini and should stay pinned for reproducible runs
- use JSON output as the canonical saved artifact on this version

Node preflight:
- promptfoo requires Node.js `20.20+` or `22.22+`

```bash
node -v
npm -v
npx promptfoo@0.120.27 --version
```

Required env:
```bash
export OWUI_API_KEY='<open-webui-api-key>'
export OWUI_API_BASE='http://127.0.0.1:3000'
export PROMPTFOO_PYTHON="$(command -v python3)"
```

Validate config before the first run:
```bash
cd /home/christopherbailey/homelab-llm
export PROMPTFOO_PYTHON="$(command -v python3)"
npx promptfoo@0.120.27 validate -c evals/websearch/promptfooconfig.yaml
```

Stage 0: lane lock from existing baseline artifacts
1. score `20260308T193329Z-baseline-fast-smoke.json`
2. score `20260308T193329Z-baseline-deep-smoke.json`
3. score `20260308T193329Z-baseline-fast-freshness-high-extra.json`
4. score `20260308T193329Z-baseline-deep-freshness-high-extra.json`
5. roll up those scored CSVs before any runtime mutation

Build one reviewer-friendly directory first:
```bash
uv run python scripts/websearch_review_packet.py \
  --input evals/websearch/artifacts/20260308T193329Z-baseline-fast-smoke.json \
  --input evals/websearch/artifacts/20260308T193329Z-baseline-deep-smoke.json \
  --input evals/websearch/artifacts/20260308T193329Z-baseline-fast-freshness-high-extra.json \
  --input evals/websearch/artifacts/20260308T193329Z-baseline-deep-freshness-high-extra.json \
  --output-dir evals/websearch/review/20260308T193329Z-lane-review
```

That directory includes:
- `README.md` with the review order and rollup command
- one markdown file per slice with the query, both lane answers, source domains,
  source URLs, and latency in one place
- copied aggregate summaries under `summaries/`
- blank scoring CSVs beside the markdown files

Score rollup:
```bash
uv run python scripts/websearch_score_rollup.py   --input evals/websearch/artifacts/20260308T193329Z-lane-smoke-review.csv   --input evals/websearch/artifacts/20260308T193329Z-lane-freshness-high-extra-review.csv   --baseline baseline:owui-fast   --output evals/websearch/artifacts/20260308T193329Z-lane-rollup.md
```

If the lane decision is ambiguous, keep `owui-fast`.

Stage 1: supported domain-filter tuning on the winning lane only
- mutate only `WEB_SEARCH_DOMAIN_FILTER_LIST`
- keep `WEB_FETCH_FILTER_LIST` fixed
- keep `WEB_LOADER_ENGINE=safe_web`
- keep `WEB_SEARCH_CONCURRENT_REQUESTS=1`
- do not change loader/concurrency/timeouts yet
- do not start provider bakeoffs

Conservative candidate profiles:
- `df-zhihu`
- `df-zhihu-explicit`
- `df-zhihu-explicit-spam`

Required slices for every candidate on the winning lane:
1. `smoke`
2. `freshness-high-extra`
3. `adversarial-junk`
4. `technical-docs`

Preflight before writing `25-websearch-tuning.conf`:
```bash
systemctl show -p Environment open-webui.service --no-pager | tr ' ' '
' | rg '^"?WEB_SEARCH_DOMAIN_FILTER_LIST='
curl -fsS http://127.0.0.1:3000/health | jq .
```

Reason:
- `WEB_SEARCH_DOMAIN_FILTER_LIST` is a PersistentConfig-backed variable
- if `ENABLE_PERSISTENT_CONFIG=False` is not active, the systemd drop-in may not control the effective value and this tuning flow should not be used as-is

Temporary tuning override for one variable at a time:
```bash
sudo tee /etc/systemd/system/open-webui.service.d/25-websearch-tuning.conf >/dev/null <<'EOF'
[Service]
Environment="WEB_SEARCH_DOMAIN_FILTER_LIST=<candidate_value>"
EOF
sudo systemctl daemon-reload
sudo systemctl restart open-webui.service
```

Post-restart env verification:
```bash
systemctl show -p Environment open-webui.service --no-pager | tr ' ' '
' | rg '^"?WEB_SEARCH_DOMAIN_FILTER_LIST='
systemctl show -p Environment open-webui.service --no-pager | tr ' ' '
' | rg '^"?WEB_FETCH_FILTER_LIST='
systemctl show -p Environment open-webui.service --no-pager | tr ' ' '
' | rg '^"?WEB_SEARCH_ENGINE=searxng$|^"?WEB_LOADER_ENGINE=safe_web$|^"?WEB_SEARCH_CONCURRENT_REQUESTS=1$'
curl -fsS http://127.0.0.1:3000/health | jq .
```

If the preflight or post-restart env check fails:
- stop the candidate
- remove `25-websearch-tuning.conf`
- restore baseline
- do not treat the outcome as a valid experiment result

Promptfoo run pattern for the winning lane:
```bash
RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)"
npx promptfoo@0.120.27 eval   -c evals/websearch/promptfooconfig.yaml   --filter-providers '^<winning-lane>$'   --filter-metadata enabled=true   --filter-metadata category=adversarial-junk   --no-cache   --output "evals/websearch/artifacts/${RUN_ID}-<profile>-<winning-lane>-adversarial-junk.json"
```

Summary per run:
```bash
uv run python scripts/websearch_eval_summary.py   --input "evals/websearch/artifacts/${RUN_ID}-<profile>-<winning-lane>-adversarial-junk.json"   --output "evals/websearch/artifacts/${RUN_ID}-<profile>-<winning-lane>-adversarial-junk-summary.md"
```

Manual scoring:
- use `evals/websearch/scoring_template.csv`
- keep one row per query with `profile_id`, `lane`, `run_id`, and the four 1-5 scores
- keep the same reviewer across compared runs
- score `adversarial-junk` to prove the filter helps where it should
- score `technical-docs` to detect collateral damage

Candidate promotion:
- candidate must improve `adversarial-junk` materially
- must not regress `technical-docs` beyond the documented threshold
- must keep machine checks clean on assertions, blocked internal-domain hits, and zero-source behavior
- if more than one candidate passes, choose the narrowest denylist
- if no candidate passes, keep the current baseline unchanged

Rollback:
```bash
sudo rm -f /etc/systemd/system/open-webui.service.d/25-websearch-tuning.conf
sudo systemctl daemon-reload
sudo systemctl restart open-webui.service
systemctl show -p Environment open-webui.service --no-pager | tr ' ' '
' | rg '^"?WEB_SEARCH_DOMAIN_FILTER_LIST=|^"?WEB_FETCH_FILTER_LIST='
curl -fsS http://127.0.0.1:3000/health | jq .
```

Guardrails:
- blocked-domain checks are eval-only and must not be treated as runtime config
- `WEB_FETCH_FILTER_LIST` stays fixed; do not use it as a quality-tuning control
- `smoke_latency` is diagnostic-only in reporting, not a product-quality gate
- this harness is for measuring supported paths and tuning documented Open WebUI knobs only
- it is not a license to add middleware, hidden search policy, or custom citation logic
- provider bakeoffs remain out of scope for this phase

## LiteLLM Web Search Reset Checks (Mini)
Readiness and model checks:
```bash
curl -fsS http://127.0.0.1:4000/health/readiness | jq .
curl -fsS http://127.0.0.1:4000/health/readiness | jq -e '.db != "Not connected"'
curl -fsS http://127.0.0.1:4000/health/readiness | jq -r '.success_callbacks[]' | rg 'WebsearchSchemaGuardrail'

source /home/christopherbailey/homelab-llm/services/litellm-orch/config/env.local
curl -fsS -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" \
  http://127.0.0.1:4000/v1/models | jq -r '.data[].id' | sort
```

Generic search-tool smoke:
```bash
source /home/christopherbailey/homelab-llm/services/litellm-orch/config/env.local
curl -fsS -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" \
  -H "Content-Type: application/json" \
  http://127.0.0.1:4000/v1/search/searxng-search \
  -d '{"query":"openwebui searxng","max_results":2}' | jq .
```

Pass guidance:
- readiness JSON does not report `db: "Not connected"`.
- `WebsearchSchemaGuardrail` is absent from readiness callbacks.
- `/v1/models` does not include `fast-research`.
- `/v1/search/searxng-search` still works for direct callers and MCP tools.

## LiteLLM Transcript Cleanup Alias Checks (Mini)
```bash
set -a
source /home/christopherbailey/homelab-llm/services/litellm-orch/config/env.local
set +a

curl -fsS -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" \
  http://127.0.0.1:4000/v1/models | jq -r '.data[].id' | sort

curl -fsS http://127.0.0.1:4000/v1/responses \
  -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"model":"task-transcribe","input":[{"role":"user","content":"um i i think this should probably work maybe yes"}],"max_output_tokens":384}' | jq -r '.output[0].content[0].text'

curl -fsS http://127.0.0.1:4000/v1/responses \
  -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"model":"task-transcribe-vivid","input":[{"role":"user","content":"uh okay this is kind of sudden but it matters a lot actually"}],"prompt_variables":{"audience":"internal notes","tone":"lightly polished"},"max_output_tokens":256}' | jq -r '.output[0].content[0].text'

python3 - <<'PY'
import json, urllib.request

key = None
for line in open("/home/christopherbailey/homelab-llm/services/litellm-orch/config/env.local", encoding="utf-8"):
    if line.startswith("LITELLM_MASTER_KEY="):
        key = line.split("=", 1)[1].strip().strip('"').strip("'")
        break

url = "http://127.0.0.1:4000/v1/responses"
headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
first = {
    "model": "task-transcribe-vivid",
    "input": [{"role": "user", "content": "uh okay this is kind of sudden but it matters a lot actually"}],
    "prompt_variables": {"audience": "internal notes", "tone": "lightly polished"},
    "max_output_tokens": 256,
}
req = urllib.request.Request(url, data=json.dumps(first).encode(), headers=headers, method="POST")
with urllib.request.urlopen(req, timeout=90) as resp:
    first_body = json.loads(resp.read().decode())

second = {
    "model": "task-transcribe-vivid",
    "previous_response_id": first_body["id"],
    "input": [{"role": "user", "content": "Make that a little more formal."}],
    "prompt_variables": {"audience": "internal notes", "tone": "lightly polished"},
    "max_output_tokens": 192,
}
req = urllib.request.Request(url, data=json.dumps(second).encode(), headers=headers, method="POST")
with urllib.request.urlopen(req, timeout=90) as resp:
    second_body = json.loads(resp.read().decode())

print(json.dumps({
    "first_id": first_body.get("id"),
    "first_cached_tokens": ((first_body.get("usage") or {}).get("input_tokens_details") or {}).get("cached_tokens"),
    "second_previous_response_id": second_body.get("previous_response_id"),
    "second_cached_tokens": ((second_body.get("usage") or {}).get("input_tokens_details") or {}).get("cached_tokens"),
    "second_output_text": second_body.get("output_text"),
}, indent=2))
PY

SMOKE_KEY_JSON="$(curl -fsS http://127.0.0.1:4000/key/generate \
  -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"key_alias":"task-transcribe-smoke","key_type":"llm_api","duration":"1h","models":["task-transcribe","task-transcribe-vivid"],"allowed_routes":["/v1/models","/v1/responses","/v1/chat/completions"]}')"
SMOKE_KEY="$(printf '%s' "$SMOKE_KEY_JSON" | jq -r '.key')"

curl -fsS http://127.0.0.1:4000/v1/models \
  -H "Authorization: Bearer ${SMOKE_KEY}" | jq -r '.data[].id' | sort

curl -fsS http://127.0.0.1:4000/v1/responses \
  -H "Authorization: Bearer ${SMOKE_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"model":"task-transcribe","input":[{"role":"user","content":"um i i think this should probably work maybe yes"}],"max_output_tokens":384}' | jq -r '.output[0].content[0].text'
```

Pass guidance:
- `/health/readiness` does not report `db: "Not connected"`.
- `/key/generate` succeeds for a short-lived non-master smoke key.
- the smoke key can call `/v1/models` and `POST /v1/responses` for the
  allowed transcript aliases.
- `/v1/models` includes `task-transcribe` and `task-transcribe-vivid`.
- both aliases succeed through `POST /v1/responses`
- outputs are plain cleaned transcript text with no wrapper heading, label, or commentary
- `task-transcribe-vivid` accepts optional `audience` and `tone` prompt variables
- vivid follow-up accepts the prior public response `id` as
  `previous_response_id`
- the echoed `previous_response_id` does not need to equal that public `id`
  byte-for-byte
- vivid follow-up exposes `usage.input_tokens_details.cached_tokens`

## Legacy Path Removal Checks (Mini)
Service removal and active-surface grep:
```bash
systemctl is-active open-webui.service litellm-orch.service searxng.service
systemctl is-enabled websearch-orch.service
systemctl status websearch-orch.service --no-pager

rg -n --hidden --glob '!.git' --glob '!.venv/**' --glob '!docs/journal/**' --glob '!docs/archive/**' --glob '!docs/_core/consistency_audit_2026-03.md' \
  'websearch_schema_guardrail|<source id=|web_answer(\\.schema\\.json)?|EXTERNAL_WEB_LOADER_URL|SEARXNG_QUERY_URL=http://127.0.0.1:8899/search\\?q=<query>|WEB_LOADER_ENGINE=external|QUERY_GUARD_ENABLED|TRUST_POLICY_ENABLED|RERANK_ENABLED|CITATION_CONTRACT_ENABLED|fast-research' \
  /home/christopherbailey/homelab-llm
```

Pass guidance:
- `websearch-orch.service` is disabled or not found.
- Active repo surfaces do not depend on the removed custom middleware or legacy path markers.

## LiteLLM Search Proxy (Mini)
```bash
curl -fsS http://127.0.0.1:4000/v1/search/searxng-search \
  -H "Authorization: Bearer $LITELLM_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query":"openvino llm","max_results":3}' | jq .
```

## MCP web.fetch (Mini, stdio)
```bash
cd /home/christopherbailey/homelab-llm/services/mcp-tools/web-fetch
uv venv .venv
uv pip install -e .
.venv/bin/python3 scripts/demo_client.py --url https://example.com --print-clean-text
```

## MCP search.web (Mini, stdio)
```bash
cd /home/christopherbailey/homelab-llm/services/mcp-tools/web-fetch
.venv/bin/python3 scripts/demo_client.py --tool search.web --query "openvino llm" --max-results 3
```

## TinyAgents (Mini, once wired)
Run the agent with a known MCP tool and confirm tool output is reflected in the
response.

## MCP registry + TinyAgents env (MVP)
```bash
sudo cp /home/christopherbailey/homelab-llm/platform/ops/templates/mcp-registry.json /etc/homelab-llm/mcp-registry.json
sudo cp /home/christopherbailey/homelab-llm/platform/ops/templates/tiny-agents.env /etc/homelab-llm/tiny-agents.env
diff -u /home/christopherbailey/homelab-llm/platform/ops/templates/mcp-registry.json /etc/homelab-llm/mcp-registry.json
```

Expected:
- runtime registry matches the repo template exactly
- registry currently contains TinyAgents-facing stdio tools only
- Open Terminal MCP remains LiteLLM-managed and is intentionally absent from
  the TinyAgents registry in this slice

## OpenVINO model control (ovctl)
```bash
/home/christopherbailey/homelab-llm/platform/ops/scripts/ovctl list
/home/christopherbailey/homelab-llm/platform/ops/scripts/ovctl profiles
/home/christopherbailey/homelab-llm/platform/ops/scripts/ovctl warm-profile ov-only-expanded
/home/christopherbailey/homelab-llm/platform/ops/scripts/ovctl status
```

## ONNX evaluation (route + summarize)
```bash
platform/ops/.venv-onnx/bin/python /home/christopherbailey/homelab-llm/platform/ops/scripts/onnx_eval.py
```

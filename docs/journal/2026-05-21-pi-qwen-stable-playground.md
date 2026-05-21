# 2026-05-21 - Pi Qwen stable playground

## Objective
Turn the proven Pi + Mini-local oMLX Qwen path into a boring scratch-only human
playground before trying a GUI or larger agent framework.

## Runtime Shape
- Playground:
  `/home/christopherbailey/pi-qwen-trials/current`
- Launcher:
  `/home/christopherbailey/pi-qwen-trials/current/run_pi_qwen.py`
- Pi install:
  `/home/christopherbailey/pi-qwen-trials/current/pi-tooling`
- Pi config:
  `/home/christopherbailey/pi-qwen-trials/current/pi-config/models.json`
- Request knob extension:
  `/home/christopherbailey/pi-qwen-trials/current/extensions/request-knobs.ts`
- Sidecar:
  `http://127.0.0.1:4022/v1`
- Model:
  `local-qwen` / `omlx-qwen36-27b-optiq-4bit`

The launcher creates one disposable scratch repo per run under
`/home/christopherbailey/pi-qwen-trials/current/runs/<timestamp>/scratch-repo`.
It exposes only request-level knobs: task prompt, model, temperature, and max
tokens. It does not mutate oMLX runtime settings, expose new ports, or route
through LiteLLM/OpenHands/Open WebUI.

## Acceptance Smoke
Command:

```bash
python3 /home/christopherbailey/pi-qwen-trials/current/run_pi_qwen.py \
  --run-id 20260521-acceptance-smoke
```

Result:

```json
{
  "pi_returncode": 0,
  "final_test_returncode": 0,
  "success": true
}
```

The launcher confirmed the Mini sidecar was healthy:

```json
{
  "status": "ok",
  "model": "omlx-qwen36-27b-optiq-4bit",
  "backend_base_url": "http://192.168.1.72:8120/v1",
  "backend_model": "omlx-qwen36-27b-optiq-4bit",
  "bind": "127.0.0.1:4022"
}
```

Baseline test failed as intended on `test_rejects_reversed_intervals`. Pi then
patched `src/tinycalc/intervals.py`; final validation passed:

```text
Ran 3 tests in 0.000s

OK
```

## Evidence
- Run directory:
  `/home/christopherbailey/pi-qwen-trials/current/runs/20260521-acceptance-smoke`
- Transcript:
  `artifacts/pi-run.jsonl`
- Final diff:
  `artifacts/final-diff.patch`
- Final test output:
  `artifacts/final-test.log` and `artifacts/final-test.stderr.log`
- Manifest:
  `artifacts/manifest.json`

## Decision
This is the stable starting point for manual daily scratch use. Defer Kanban or
other GUI/control-surface evaluation until this playground has survived a few
normal human-driven runs.

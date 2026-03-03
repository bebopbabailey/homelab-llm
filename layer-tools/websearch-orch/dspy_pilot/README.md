# DSPy Citation-Fidelity Pilot (Learning-First)

This pilot is intentionally hands-on: you run small loops, inspect output, tweak one setting, then rerun.

## What this pilot is for
- Optimize citation fidelity for web-research answers.
- Keep runtime routing unchanged while we tune behavior offline.
- Learn DSPy by observing measurable changes, not by reading theory only.

## Files in this pilot
- `layer-tools/websearch-orch/dspy_pilot/models.py` - dataset/prediction contracts
- `layer-tools/websearch-orch/dspy_pilot/metrics.py` - citation scoring rubric
- `layer-tools/websearch-orch/dspy_pilot/program.py` - `mock` and `dspy` backends
- `scripts/dspy_citation_fidelity.py` - CLI driver
- `layer-tools/websearch-orch/dspy_pilot/data/citation_fidelity.sample.jsonl` - starter dataset
- `layer-tools/websearch-orch/dspy_pilot/schemas/citation_response.schema.json` - output schema

## Optional dependencies
```bash
uv pip install --python /home/christopherbailey/homelab-llm/layer-tools/websearch-orch/.venv/bin/python \
  -r /home/christopherbailey/homelab-llm/layer-tools/websearch-orch/requirements-dspy-pilot.txt
```

## Hands-on labs

### Lab 1 - Understand the contract (5 minutes)
```bash
cd /home/christopherbailey/homelab-llm
uv run python scripts/dspy_citation_fidelity.py print-contract
uv run python scripts/dspy_citation_fidelity.py validate-dataset \
  --dataset layer-tools/websearch-orch/dspy_pilot/data/citation_fidelity.sample.jsonl
```
Expected:
- Dataset loads cleanly.
- You can point to `question`, `retrieved_sources`, and `expected` in each case.

### Lab 2 - Run deterministic baseline (5 minutes)
```bash
cd /home/christopherbailey/homelab-llm
uv run python scripts/dspy_citation_fidelity.py eval \
  --backend mock \
  --dataset layer-tools/websearch-orch/dspy_pilot/data/citation_fidelity.sample.jsonl \
  --report-out /tmp/dspy_citation_mock_report.json
```
Expected:
- A report is written to `/tmp/dspy_citation_mock_report.json`.
- You see per-case scores and a summary pass rate.

### Lab 3 - Run real DSPy against local gateway (10-15 minutes)
```bash
cd /home/christopherbailey/homelab-llm
export LITELLM_MASTER_KEY='<your-key>'
uv run python scripts/dspy_citation_fidelity.py eval \
  --backend dspy \
  --dataset layer-tools/websearch-orch/dspy_pilot/data/citation_fidelity.sample.jsonl \
  --model openai/fast \
  --api-base http://127.0.0.1:4000/v1 \
  --api-key-env LITELLM_MASTER_KEY \
  --report-out /tmp/dspy_citation_dspy_report.json
```
Expected:
- DSPy calls your local OpenAI-compatible endpoint.
- You can compare real-model citation behavior vs mock baseline.

### Lab 4 - Compile and compare (15-25 minutes)
```bash
cd /home/christopherbailey/homelab-llm
export LITELLM_MASTER_KEY='<your-key>'
uv run python scripts/dspy_citation_fidelity.py compile \
  --train-dataset layer-tools/websearch-orch/dspy_pilot/data/citation_fidelity.sample.jsonl \
  --dev-dataset layer-tools/websearch-orch/dspy_pilot/data/citation_fidelity.sample.jsonl \
  --model openai/fast \
  --api-base http://127.0.0.1:4000/v1 \
  --api-key-env LITELLM_MASTER_KEY \
  --optimizer bootstrap \
  --num-trials 8 \
  --artifact-dir /tmp/dspy-citation-artifacts
```
Expected:
- Compiled artifact + report files appear under `/tmp/dspy-citation-artifacts`.
- You can run eval again with `--compiled-program` to compare baseline vs compiled.

## Notes
- `mock` backend exists for fast metric debugging and contract validation.
- `dspy` backend is for real optimization and requires `dspy-ai`.
- This pilot does not change `websearch-orch` live request handling.

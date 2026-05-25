# 2026-05-25 - LiteLLM dotprompt startup repair

## Objective
Restore Mini LiteLLM startup so GPT-OSS-backed `task-*` aliases can be tested
without interfering with the oMLX Qwen/Pi project.

## Finding
`litellm-orch.service` was in a restart loop before this repair. Journald showed
LiteLLM failing during prompt initialization:

```text
ValueError: Cannot set prompt_directory when working with prompt_initializer.
Needs to be a specific dotprompt file
```

The live router registered `task-transcribe` in `prompts:` with
`prompt_directory: ./prompts`. The installed LiteLLM now requires a specific
dotprompt file for the native prompt registry path.

## Change
Updated the `task-transcribe` native prompt registration to use:

```yaml
prompt_file: ./prompts/task-transcribe.prompt
```

The existing `global_prompt_directory: ./prompts` remains in place for local
guardrails that render prompt files directly.

## Validation
- Router expectation test passed:
  `uv run --with pytest --with pyyaml python -m pytest services/litellm-orch/tests/test_router_drop_params.py -q`
- Config startup validation passed using the deployed LiteLLM venv:
  `litellm --config config/router.yaml --skip_server_startup`

Live service restart and task-alias smokes are the remaining runtime gate after
the repair is landed to `master`.

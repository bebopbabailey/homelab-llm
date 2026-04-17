# NOW

Active
- Build the `qwen-agent-proxy` shadow sidecar for OpenHands over
  `Qwen3-Coder-Next`.
- Keep the trusted `code-reasoning` worker lane unchanged while validating the
  adapter-backed shadow alias `code-qwen-agent`.
- Current target shape:
  - Docker-bridge sidecar on `172.17.0.1:4021`
  - direct OpenHands shadow provider path `http://host.docker.internal:4021/v1`
  - `Qwen3-Coder-Next` benchmark trial prepared in the disposable workspace

NEXT UP
- Run the first joint OpenHands/Codex coding task on the prepared
  SWE-bench-style micro bugfix repo.

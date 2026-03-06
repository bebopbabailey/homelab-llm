# Constraints: mcp-tools

Inherits global + tools-layer constraints:
- Global: `../../CONSTRAINTS.md`
- Tools layer: `../CONSTRAINTS.md`

## Hard constraints
- MCP tools are stdio-invoked; do not introduce listeners/ports without
  explicit approval.
- Keep tool behavior deterministic and documented per tool contract.
- No secrets in repo.

## Allowed operations
- Tool-level documentation/contract updates.
- MCP client integration updates that preserve no-listener default.

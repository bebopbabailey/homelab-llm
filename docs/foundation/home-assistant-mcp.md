# Home Assistant MCP (Official) — Notes for This Homelab

This document summarizes the **official Home Assistant MCP integrations** so
we can plan TinyAgents + MCP wiring correctly.

## Two official integrations (server vs client)

### 1) Model Context Protocol **Server** (Home Assistant as MCP server)
- Integration: **Model Context Protocol Server**.
- Home Assistant exposes MCP tools via the Assist API. citeturn0search1
- Remote MCP server URL is `https://<your_home_assistant_url>/api/mcp`. citeturn0search1
- MCP clients (Claude Desktop, Cursor, gemini‑cli, etc.) connect to HA using
  Streamable HTTP; OAuth and access tokens can be used depending on client. citeturn0search1
- Clients can control only entities exposed to Assist. citeturn0search1

### 2) Model Context Protocol **Client** (Home Assistant as MCP client)
- Integration: **Model Context Protocol**.
- Home Assistant can connect to **external MCP servers** to add tools for
  conversation agents. citeturn0search0
- Requires an MCP server with SSE; if a server is stdio‑only, use an MCP proxy. citeturn0search0
- Supports **Tools** only (no Prompts, Resources, Sampling, Notifications). citeturn0search0

## Why this matters for the homelab
- If we want **HA to be controlled by agents**, we should use **MCP Server**
  integration and point TinyAgents/other MCP clients at `/api/mcp`. citeturn0search1
- If we want **HA to call other tools** (external MCP servers) as part of HA’s
  conversation agent, we would use **MCP client** integration. citeturn0search0

## Planning guidance
- Keep **Home Assistant as MCP server** for control and automation.
- Keep **TinyAgents** as the MCP client/orchestrator on the Mini.
- Use **Streamable HTTP** for MCP clients that require it (Open WebUI MCP also
  uses Streamable HTTP).

## References (official)
- HA MCP Server integration:  
  `https://www.home-assistant.io/integrations/mcp_server/` citeturn0search1
- HA MCP Client integration:  
  `https://www.home-assistant.io/integrations/mcp/` citeturn0search0

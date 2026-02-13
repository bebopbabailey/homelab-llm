from __future__ import annotations

import uuid
from typing import Any

from .litellm_client import LiteLLMClient
from .mcp_client import MCPToolClient
from .mcp_registry import build_tool_index, load_registry
from .models import ChatMessage, RunRequest, RunResponse, ToolCallRecord
from .settings import TinyAgentsSettings


class TinyAgentRunner:
    def __init__(self, settings: TinyAgentsSettings):
        self._settings = settings
        self._litellm = LiteLLMClient(settings)
        self._mcp = MCPToolClient()
        self._servers = load_registry(settings.mcp_registry_path)
        self._tool_index = build_tool_index(self._servers)

    def list_tools(self) -> list[str]:
        return sorted(self._tool_index.keys())

    async def run(self, req: RunRequest) -> RunResponse:
        allowed = req.allowed_tools or self.list_tools()
        run_id = req.run_id or f"run-{uuid.uuid4()}"

        tool_calls: list[ToolCallRecord] = []
        messages = [m.model_dump() for m in req.messages]

        unknown = [t for t in allowed if t not in self._tool_index]
        if unknown:
            raise ValueError(f"Unknown allowed_tools: {', '.join(unknown)}")

        # MVP deterministic tool step: at most one tool call before model response.
        if req.max_tool_calls > 0 and allowed:
            first_user = next((m for m in req.messages if m.role == "user"), None)
            if first_user:
                selected_tool, payload = _select_tool_and_payload(allowed, first_user.content)
                if selected_tool and selected_tool in self._tool_index:
                    server = self._tool_index[selected_tool]
                    record = ToolCallRecord(tool_name=selected_tool, input_json=payload)
                    try:
                        output = await self._mcp.call_tool(
                            server=server,
                            tool_name=selected_tool,
                            input_json=payload,
                        )
                        record.output_json = output
                        messages.append(
                            {
                                "role": "system",
                                "content": f"Tool {selected_tool} output: {output}",
                            }
                        )
                    except Exception as exc:  # noqa: BLE001
                        record.error = str(exc)
                    tool_calls.append(record)

        response = await self._litellm.chat_completions(
            model=req.model,
            messages=messages,
            timeout_s=req.timeout_s,
        )

        final = _extract_assistant_message(response)
        return RunResponse(
            run_id=run_id,
            model=req.model,
            tool_calls=tool_calls,
            final_message=final,
            stats={"usage": response.get("usage", {})},
        )


def _select_tool_and_payload(allowed_tools: list[str], user_text: str) -> tuple[str | None, dict[str, Any]]:
    user_text = user_text.strip()
    if "web.fetch" in allowed_tools and user_text.startswith(("http://", "https://")):
        return "web.fetch", {"url": user_text, "include_raw_html": False}
    if "search.web" in allowed_tools:
        return "search.web", {"query": user_text, "max_results": 3}
    return None, {}


def _extract_assistant_message(raw: dict[str, Any]) -> ChatMessage:
    choices = raw.get("choices", [])
    if not choices:
        return ChatMessage(role="assistant", content="")
    msg = choices[0].get("message", {})
    content = msg.get("content", "") or ""
    return ChatMessage(role="assistant", content=content)

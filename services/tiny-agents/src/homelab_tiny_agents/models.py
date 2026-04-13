from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: str


class ToolCallRecord(BaseModel):
    tool_name: str
    input_json: dict[str, Any]
    output_json: dict[str, Any] | None = None
    error: str | None = None


class RunRequest(BaseModel):
    model: str
    messages: list[ChatMessage]
    allowed_tools: list[str] | None = None
    max_tool_calls: int = Field(default=8, ge=0, le=32)
    timeout_s: int = Field(default=120, ge=1, le=600)
    run_id: str | None = None


class RunResponse(BaseModel):
    run_id: str
    model: str
    tool_calls: list[ToolCallRecord]
    final_message: ChatMessage
    stats: dict[str, Any] = Field(default_factory=dict)


class McpServerSpec(BaseModel):
    name: str
    purpose: str = ""
    transport: Literal["stdio", "http"]
    command: str | None = None
    args: list[str] = Field(default_factory=list)
    env: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    notes: str | None = None

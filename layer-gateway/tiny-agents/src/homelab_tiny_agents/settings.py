from __future__ import annotations

import os
from pydantic import BaseModel, Field, field_validator


class TinyAgentsSettings(BaseModel):
    litellm_api_base: str = Field(default="http://127.0.0.1:4000/v1")
    litellm_api_key_env: str = Field(default="LITELLM_API_KEY")
    mcp_registry_path: str = Field(default="/etc/homelab-llm/mcp-registry.json")
    service_host: str = Field(default="127.0.0.1")
    service_port: int = Field(default=4030)

    @field_validator("litellm_api_base")
    @classmethod
    def _validate_local_base(cls, value: str) -> str:
        if not value.startswith("http://127.0.0.1:"):
            raise ValueError("LITELLM_API_BASE must be localhost for MVP")
        return value

    @field_validator("service_host")
    @classmethod
    def _validate_service_host(cls, value: str) -> str:
        if value != "127.0.0.1":
            raise ValueError("tiny-agents service must bind to 127.0.0.1")
        return value


def load_settings() -> TinyAgentsSettings:
    return TinyAgentsSettings(
        litellm_api_base=os.getenv("LITELLM_API_BASE", "http://127.0.0.1:4000/v1"),
        litellm_api_key_env=os.getenv("LITELLM_API_KEY_ENV", "LITELLM_API_KEY"),
        mcp_registry_path=os.getenv("MCP_REGISTRY_PATH", "/etc/homelab-llm/mcp-registry.json"),
        service_host=os.getenv("TINY_AGENTS_HOST", "127.0.0.1"),
        service_port=int(os.getenv("TINY_AGENTS_PORT", "4030")),
    )

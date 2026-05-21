from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    host: str = "127.0.0.1"
    port: int = 4022
    public_model_id: str = "omlx-qwen36-27b-optiq-4bit"
    backend_base_url: str = "http://192.168.1.72:8120/v1"
    backend_model: str = "omlx-qwen36-27b-optiq-4bit"
    backend_api_key: str = ""
    auth_token: str = ""
    timeout_seconds: float = 180.0
    max_input_tokens: int = 32768
    max_output_tokens: int = 32768


def load_settings() -> Settings:
    host = os.getenv("OMLX_AGENT_GATEWAY_HOST", "127.0.0.1")
    if host != "127.0.0.1":
        raise ValueError("OMLX_AGENT_GATEWAY_HOST must stay 127.0.0.1")
    return Settings(
        host=host,
        port=int(os.getenv("OMLX_AGENT_GATEWAY_PORT", "4022")),
        public_model_id=os.getenv("OMLX_AGENT_GATEWAY_MODEL_ID", "omlx-qwen36-27b-optiq-4bit"),
        backend_base_url=os.getenv("OMLX_AGENT_GATEWAY_BACKEND_BASE_URL", "http://192.168.1.72:8120/v1").rstrip("/"),
        backend_model=os.getenv("OMLX_AGENT_GATEWAY_BACKEND_MODEL", "omlx-qwen36-27b-optiq-4bit"),
        backend_api_key=os.getenv("OMLX_AGENT_GATEWAY_BACKEND_API_KEY", ""),
        auth_token=os.getenv("OMLX_AGENT_GATEWAY_AUTH_TOKEN", ""),
        timeout_seconds=float(os.getenv("OMLX_AGENT_GATEWAY_TIMEOUT_SECONDS", "180")),
        max_input_tokens=int(os.getenv("OMLX_AGENT_GATEWAY_MAX_INPUT_TOKENS", "32768")),
        max_output_tokens=int(os.getenv("OMLX_AGENT_GATEWAY_MAX_OUTPUT_TOKENS", "32768")),
    )

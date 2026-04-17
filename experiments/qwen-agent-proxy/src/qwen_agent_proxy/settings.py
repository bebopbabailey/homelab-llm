from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class QwenAgentProxySettings:
    host: str = "127.0.0.1"
    port: int = 4021
    auth_token: str = ""
    public_model_id: str = "qwen-agent-coder-next-shadow"
    backend_base_url: str = "http://127.0.0.1:18134/v1"
    backend_model: str = "mlx-qwen3-coder-next-4bit-shadow"
    backend_api_key: str = "EMPTY"
    use_raw_api: bool = False
    default_max_tokens: int = 1024
    default_temperature: float = 0.0


def _parse_bool(value: str, *, default: bool) -> bool:
    if value is None:
        return default
    lowered = value.strip().lower()
    if lowered in {"1", "true", "yes", "on"}:
        return True
    if lowered in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"invalid boolean value: {value}")


def load_settings() -> QwenAgentProxySettings:
    host = os.getenv("QWEN_AGENT_PROXY_HOST", "127.0.0.1")
    if host not in {"127.0.0.1", "172.17.0.1"}:
        raise ValueError("QWEN_AGENT_PROXY_HOST must be 127.0.0.1 or 172.17.0.1")
    return QwenAgentProxySettings(
        host=host,
        port=int(os.getenv("QWEN_AGENT_PROXY_PORT", "4021")),
        auth_token=os.getenv("QWEN_AGENT_PROXY_AUTH_TOKEN", ""),
        public_model_id=os.getenv("QWEN_AGENT_PROXY_MODEL_ID", "qwen-agent-coder-next-shadow"),
        backend_base_url=os.getenv("QWEN_AGENT_PROXY_BACKEND_BASE_URL", "http://127.0.0.1:18134/v1"),
        backend_model=os.getenv("QWEN_AGENT_PROXY_BACKEND_MODEL", "mlx-qwen3-coder-next-4bit-shadow"),
        backend_api_key=os.getenv("QWEN_AGENT_PROXY_BACKEND_API_KEY", "EMPTY"),
        use_raw_api=_parse_bool(os.getenv("QWEN_AGENT_PROXY_USE_RAW_API"), default=False),
        default_max_tokens=int(os.getenv("QWEN_AGENT_PROXY_DEFAULT_MAX_TOKENS", "1024")),
        default_temperature=float(os.getenv("QWEN_AGENT_PROXY_DEFAULT_TEMPERATURE", "0.0")),
    )

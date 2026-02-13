from __future__ import annotations

import os
from typing import Any

import httpx

from .settings import TinyAgentsSettings


class LiteLLMClient:
    def __init__(self, settings: TinyAgentsSettings):
        self._settings = settings

    async def chat_completions(
        self,
        *,
        model: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        timeout_s: int = 120,
    ) -> dict[str, Any]:
        api_key = os.getenv(self._settings.litellm_api_key_env)
        if not api_key:
            raise RuntimeError(
                f"Missing API key env var: {self._settings.litellm_api_key_env}"
            )

        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
        }
        if tools:
            payload["tools"] = tools

        url = f"{self._settings.litellm_api_base.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=timeout_s) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()

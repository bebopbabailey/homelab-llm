from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from litellm.integrations.custom_logger import CustomLogger

_PROMPT_ROOT = Path(__file__).resolve().parents[3] / "docs" / "prompts" / "ov"
_PROMPT_CACHE: Dict[str, str] = {}


def _strip_front_matter(text: str) -> str:
    lines = text.splitlines()
    if lines and lines[0].strip() == "---":
        for idx in range(1, len(lines)):
            if lines[idx].strip() == "---":
                return "\n".join(lines[idx + 1 :]).strip()
    return text.strip()


def _extract_system_prompt(text: str) -> Optional[str]:
    body = _strip_front_matter(text)
    if not body:
        return None
    lines = body.splitlines()
    user_idx = None
    for idx, line in enumerate(lines):
        if line.strip().startswith("User:"):
            user_idx = idx
            break
    if user_idx is not None:
        body = "\n".join(lines[:user_idx]).strip()
    return body or None


def _load_prompt(model: str) -> Optional[str]:
    if model in _PROMPT_CACHE:
        return _PROMPT_CACHE[model]
    path = _PROMPT_ROOT / f"{model}.prompt.md"
    if not path.exists():
        return None
    prompt_text = _extract_system_prompt(path.read_text(encoding="utf-8"))
    if prompt_text:
        _PROMPT_CACHE[model] = prompt_text
    return prompt_text


class PromptInjector(CustomLogger):
    def _apply_prompt(self, data: dict) -> dict:
        model = data.get("model")
        if not isinstance(model, str) or not model.startswith("ov-"):
            return data

        prompt_text = _load_prompt(model)
        if not prompt_text:
            return data

        messages = data.get("messages")
        if not isinstance(messages, list):
            return data

        metadata_key = "litellm_metadata"
        metadata = data.get(metadata_key)
        if isinstance(metadata, dict) and metadata.get("ov_prompt_injected") == model:
            return data

        data["messages"] = [{"role": "system", "content": prompt_text}, *messages]
        if metadata is None:
            metadata = {}
        if isinstance(metadata, dict):
            metadata = {**metadata, "ov_prompt_injected": model}
            data[metadata_key] = metadata
        return data

    async def async_pre_call_hook(
        self,
        user_api_key_dict: Any,
        cache: Any,
        data: dict,
        call_type: Any,
    ) -> Optional[dict]:
        return self._apply_prompt(data)


prompt_injector_instance = PromptInjector()

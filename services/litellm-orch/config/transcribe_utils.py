from __future__ import annotations

import re

__all__ = ["prepare_transcript_text", "strip_wrappers"]

_CODE_FENCE_RE = re.compile(r"^\s*```[a-zA-Z0-9_-]*\s*\n(.*)\n```\s*$", re.DOTALL)
_PREAMBLE_RE = re.compile(
    r"^\s*(?:#+\s*)?(?:\*\*)?\s*(?:cleaned transcript|transcript)\s*(?:\*\*)?\s*[:\-]\s*",
    re.IGNORECASE,
)


def prepare_transcript_text(text: str) -> str:
    if not isinstance(text, str):
        return text

    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n[ \t]+", "\n", text)
    return text.strip()


def strip_wrappers(text: str) -> str:
    if not isinstance(text, str):
        return text

    original = text
    stripped = text.strip()

    match = _CODE_FENCE_RE.match(stripped)
    if match:
        stripped = match.group(1).strip()

    stripped = stripped.strip("\"'`\n ")

    cleaned = _PREAMBLE_RE.sub("", stripped).lstrip()
    lowered = cleaned.lower()
    for prefix in (
        "here is the cleaned transcript:",
        "here's the cleaned transcript:",
        "here is the transcript:",
        "here's the transcript:",
        "cleaned transcript output:",
    ):
        if lowered.startswith(prefix):
            cleaned = cleaned[len(prefix):].lstrip()
            break

    return cleaned if cleaned else original

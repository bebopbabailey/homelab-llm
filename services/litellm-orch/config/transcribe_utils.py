from __future__ import annotations

import re

__all__ = ["strip_wrappers", "strip_punct_outside_words"]

_CODE_FENCE_RE = re.compile(r"^\s*```[a-zA-Z0-9_-]*\s*\n(.*)\n```\s*$", re.DOTALL)
_PREAMBLE_RE = re.compile(
    r"^\s*(?:#+\s*)?(?:\*\*)?\s*(?:cleaned transcript|transcript)\s*(?:\*\*)?\s*[:\-]\s*",
    re.IGNORECASE,
)


def strip_punct_outside_words(text: str) -> str:
    if not isinstance(text, str):
        return text

    masked = re.sub(r"(?<=[A-Za-z0-9])['](?=[A-Za-z0-9])", "__ASCII_APOSTROPHE__", text)
    masked = re.sub(r"(?<=[A-Za-z0-9])[’](?=[A-Za-z0-9])", "__CURLY_APOSTROPHE__", masked)
    masked = re.sub(r"(?<=[A-Za-z0-9])-(?=[A-Za-z0-9])", "__INTERNAL_HYPHEN__", masked)
    masked = re.sub(r"[^\w\s]", " ", masked)
    masked = masked.replace("__ASCII_APOSTROPHE__", "'")
    masked = masked.replace("__CURLY_APOSTROPHE__", "’")
    masked = masked.replace("__INTERNAL_HYPHEN__", "-")
    masked = re.sub(r"\s+", " ", masked)
    return masked.strip()


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

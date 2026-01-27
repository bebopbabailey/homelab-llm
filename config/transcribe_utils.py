from __future__ import annotations

import re


def strip_punct_outside_words(text: str) -> str:
    if not isinstance(text, str):
        return text
    text = text.replace("’", "'")
    # Normalize dash variants to hyphen for consistent handling.
    text = text.replace("–", "-").replace("—", "-")
    # Replace punctuation (except apostrophes and hyphens) with spaces.
    text = re.sub(r"[^\w\s'-]", " ", text)
    # Remove apostrophes not between letters/digits.
    text = re.sub(r"(?<![A-Za-z0-9])'", " ", text)
    text = re.sub(r"'(?![A-Za-z0-9])", " ", text)
    # Remove hyphens not between letters/digits.
    text = re.sub(r"(?<![A-Za-z0-9])-", " ", text)
    text = re.sub(r"-(?![A-Za-z0-9])", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def strip_wrappers(text: str) -> str:
    if not isinstance(text, str):
        return text
    original = text
    text = text.strip()

    if text.startswith("```") and text.endswith("```"):
        text = text.strip("`\n ")
    text = text.strip("\"'`\n ")

    patterns = [
        r"^#+\s*cleaned transcript\s*(?:[:\\-])\s*",
        r"^\*\*cleaned transcript\*\*\s*(?:[:\\-])\s*",
        r"^cleaned transcript\s*(?:[:\\-])\s*",
        r"^here is the cleaned transcript\s*(?:[:\\-])\s*",
        r"^here's the cleaned transcript\s*(?:[:\\-])\s*",
        r"^cleaned transcript output\s*(?:[:\\-])\s*",
    ]
    lowered = text.lower()
    for pat in patterns:
        match = re.match(pat, lowered, flags=re.IGNORECASE)
        if match:
            text = text[match.end():].lstrip()
            break

    return text if text else original

#!/usr/bin/env python3
import argparse
import re
from pathlib import Path
from typing import List

from punctuators.models import PunctCapSegModelONNX


FILLERS = {"um", "uh", "er", "ah", "like"}


def _normalize_input(text: str) -> str:
    text = text.replace("\n", " ").strip()
    text = re.sub(r"\s+", " ", text)
    return text.lower()


def _collapse_stutters(text: str) -> str:
    # Collapse repeated single-word stutters: "i i i" -> "i", "i-i-i" -> "i"
    text = re.sub(r"\b(\w+)(?:[\s-]+\1\b){1,}", r"\1", text, flags=re.IGNORECASE)
    return text


def _remove_fillers(text: str) -> str:
    tokens = []
    for token in text.split():
        clean = re.sub(r"[^\w']", "", token.lower())
        if clean in FILLERS:
            continue
        tokens.append(token)
    return " ".join(tokens)


def _post_process(text: str) -> str:
    text = _collapse_stutters(text)
    text = _remove_fillers(text)
    text = re.sub(r"\bDOt\b", "dot", text, flags=re.IGNORECASE)
    text = re.sub(r"\bHTTPs\b", "https", text, flags=re.IGNORECASE)
    text = re.sub(r"\bCC\b", "cc", text)
    text = re.sub(r"\bAPt\b", "Apt", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def clean_text(model: PunctCapSegModelONNX, text: str) -> str:
    normalized = _normalize_input(text)
    normalized = _collapse_stutters(normalized)
    normalized = _remove_fillers(normalized)
    puncted = model.infer([normalized], apply_sbd=False)[0]
    if isinstance(puncted, list):
        puncted = " ".join(puncted)
    return _post_process(puncted)


def load_inputs(path: Path) -> List[str]:
    lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines()]
    return [line for line in lines if line]


def main():
    parser = argparse.ArgumentParser(description="ONNX punctuation + casing cleaner")
    parser.add_argument(
        "--model",
        default="pcs_en",
        help="punctuators model name (default: pcs_en)",
    )
    parser.add_argument("--text", help="Text to clean")
    parser.add_argument("--file", type=Path, help="File with one input per line")
    args = parser.parse_args()

    if not args.text and not args.file:
        raise SystemExit("Provide --text or --file")

    model = PunctCapSegModelONNX.from_pretrained(args.model)

    if args.text:
        print(clean_text(model, args.text))
        return

    for line in load_inputs(args.file):
        print(clean_text(model, line))


if __name__ == "__main__":
    main()

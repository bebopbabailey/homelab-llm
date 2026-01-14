#!/usr/bin/env python3
import json
import time
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import onnxruntime as ort
from huggingface_hub import snapshot_download
from transformers import AutoTokenizer
from optimum.onnxruntime import ORTModelForSeq2SeqLM

ROOT = Path("/home/christopherbailey/homelab-llm")
GOLDEN_ROUTE = ROOT / "docs" / "foundation" / "golden-set-route.md"
GOLDEN_SUMMARIZE = ROOT / "docs" / "foundation" / "golden-set-summarize.md"

EMBEDDING_MODEL = "onnx-models/all-MiniLM-L6-v2-onnx"
SUMMARIZE_MODEL = "sshleifer/distilbart-cnn-12-6"

LABELS = {
    "clean": "clean a transcript, fix punctuation and casing, remove filler",
    "summarize": "summarize a note or message in 1-2 sentences",
    "extract": "extract structured facts like dates, names, amounts",
    "rewrite": "rewrite text to a different tone without changing meaning",
    "tool": "use a tool or web search to look up information",
}


def load_route_set() -> List[Tuple[str, str]]:
    items = []
    current = {"input": "", "expected": ""}
    for raw in GOLDEN_ROUTE.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "input:" in line:
            current["input"] = line.split("input:", 1)[1].strip().strip("\"")
        if "expected:" in line:
            current["expected"] = line.split("expected:", 1)[1].strip()
        if current["input"] and current["expected"]:
            items.append((current["input"], current["expected"]))
            current = {"input": "", "expected": ""}
    return items


def load_summarize_set() -> List[Tuple[str, str]]:
    items = []
    current_input = None
    current_expected = None
    state = None
    for raw in GOLDEN_SUMMARIZE.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "input:" in line:
            state = "input"
            current_input = None
            current_expected = None
            continue
        if "expected:" in line:
            state = "expected"
            continue
        if state == "input":
            current_input = line.strip("\"")
        elif state == "expected":
            current_expected = line.strip("\"")
        if current_input and current_expected:
            items.append((current_input, current_expected))
            current_input = None
            current_expected = None
            state = None
    return items


def _find_onnx_model(model_dir: Path) -> Path:
    candidates = list(model_dir.rglob("*.onnx"))
    if not candidates:
        raise FileNotFoundError(f"No .onnx files found in {model_dir}")
    for name in ("model.onnx", "encoder_model.onnx", "model_quantized.onnx"):
        for path in candidates:
            if path.name == name:
                return path
    return candidates[0]


def _mean_pooling(last_hidden: np.ndarray, mask: np.ndarray) -> np.ndarray:
    mask = mask[..., None]
    summed = (last_hidden * mask).sum(axis=1)
    counts = np.clip(mask.sum(axis=1), 1e-9, None)
    return summed / counts


def _normalize(vec: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(vec, axis=1, keepdims=True)
    return vec / np.clip(norm, 1e-9, None)


def build_embedder():
    model_dir = Path(snapshot_download(EMBEDDING_MODEL))
    tokenizer = AutoTokenizer.from_pretrained(model_dir)
    model_path = _find_onnx_model(model_dir)
    session = ort.InferenceSession(str(model_path), providers=["CPUExecutionProvider"])
    return tokenizer, session


def embed_texts(tokenizer, session, texts: List[str]) -> np.ndarray:
    encoded = tokenizer(texts, padding=True, truncation=True, return_tensors="np")
    inputs = {
        k: v
        for k, v in encoded.items()
        if k in {"input_ids", "attention_mask", "token_type_ids"}
    }
    outputs = session.run(None, inputs)
    last_hidden = outputs[0]
    pooled = _mean_pooling(last_hidden, inputs["attention_mask"])
    return _normalize(pooled)


def eval_route():
    tokenizer, session = build_embedder()
    label_texts = list(LABELS.values())
    label_names = list(LABELS.keys())
    label_emb = embed_texts(tokenizer, session, label_texts)
    results = []
    for text, expected in load_route_set():
        start = time.perf_counter()
        emb = embed_texts(tokenizer, session, [text])[0]
        scores = (label_emb @ emb).tolist()
        best_idx = int(np.argmax(scores))
        elapsed = time.perf_counter() - start
        results.append(
            {
                "input": text,
                "expected": expected,
                "predicted": label_names[best_idx],
                "scores": dict(zip(label_names, scores)),
                "elapsed_s": elapsed,
            }
        )
    return results


def eval_summarize():
    model = ORTModelForSeq2SeqLM.from_pretrained(SUMMARIZE_MODEL, export=True)
    tokenizer = AutoTokenizer.from_pretrained(SUMMARIZE_MODEL)
    results = []
    for text, expected in load_summarize_set():
        start = time.perf_counter()
        inputs = tokenizer(text, return_tensors="pt", truncation=True)
        output_ids = model.generate(
            **inputs,
            max_new_tokens=64,
            min_new_tokens=12,
            num_beams=4,
            no_repeat_ngram_size=3,
            early_stopping=True,
        )
        summary = tokenizer.decode(output_ids[0], skip_special_tokens=True)
        elapsed = time.perf_counter() - start
        results.append(
            {
                "input": text,
                "expected": expected,
                "summary": summary,
                "elapsed_s": elapsed,
            }
        )
    return results


def main():
    output = {
        "route": eval_route(),
        "summarize": eval_summarize(),
    }
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
import argparse
import os
from typing import Dict

import numpy as np
from huggingface_hub import hf_hub_download
import openvino as ov
from safetensors import safe_open
from transformers import AutoTokenizer

APPROACHES = [
    "none",
    "mcts",
    "bon",
    "moa",
    "rto",
    "z3",
    "self_consistency",
    "pvg",
    "rstar",
    "cot_reflection",
    "plansearch",
    "leap",
    "re2",
]


def softmax(logits: np.ndarray) -> np.ndarray:
    logits = logits - np.max(logits, axis=1, keepdims=True)
    exp = np.exp(logits)
    return exp / np.sum(exp, axis=1, keepdims=True)


def load_head_weights(repo_id: str, cache_dir: str | None) -> Dict[str, np.ndarray]:
    path = hf_hub_download(repo_id=repo_id, filename="model.safetensors", cache_dir=cache_dir)
    with safe_open(path, framework="np") as handle:
        weights = {name: handle.get_tensor(name) for name in handle.keys()}
    return weights


def mlp_effort(effort: np.ndarray, weights: Dict[str, np.ndarray]) -> np.ndarray:
    w0 = weights["effort_encoder.0.weight"]
    b0 = weights["effort_encoder.0.bias"]
    w2 = weights["effort_encoder.2.weight"]
    b2 = weights["effort_encoder.2.bias"]
    hidden = np.maximum(0, effort @ w0.T + b0)
    return np.maximum(0, hidden @ w2.T + b2)


def classify(cls_vec: np.ndarray, effort_vec: np.ndarray, weights: Dict[str, np.ndarray]) -> np.ndarray:
    w = weights["classifier.weight"]
    b = weights["classifier.bias"]
    combined = np.concatenate([cls_vec, effort_vec], axis=1)
    return combined @ w.T + b


def build_input_map(compiled, input_ids: np.ndarray, attention_mask: np.ndarray) -> Dict[str, np.ndarray]:
    mapping = {}
    for inp in compiled.inputs:
        name = inp.get_any_name()
        if "input_ids" in name:
            mapping[name] = input_ids
        elif "attention_mask" in name:
            mapping[name] = attention_mask
    if len(mapping) != len(compiled.inputs):
        mapping = {
            compiled.inputs[0].get_any_name(): input_ids,
            compiled.inputs[1].get_any_name(): attention_mask,
        }
    return mapping


def main() -> None:
    parser = argparse.ArgumentParser(description="OV ModernBERT router POC (encoder + NumPy head).")
    parser.add_argument(
        "--model-dir",
        default="/home/christopherbailey/models/converted_models/ov-modernbert-large-router-encoder-fp32/task-feature-extraction__wf-fp32",
        help="Path to OV encoder directory.",
    )
    parser.add_argument("--router-head", default="codelion/optillm-modernbert-large", help="HF repo for head.")
    parser.add_argument("--tokenizer-repo", default="codelion/optillm-modernbert-large", help="HF repo for tokenizer.")
    parser.add_argument("--cache-dir", default=None, help="HF cache dir (optional).")
    parser.add_argument("--device", default=os.environ.get("OV_DEVICE", "CPU"), help="OpenVINO device.")
    parser.add_argument("--system", default="You are a router. Pick the best approach.", help="System prompt.")
    parser.add_argument("--user", default="Explain the tradeoffs of X and Y.", help="User prompt.")
    parser.add_argument("--max-length", type=int, default=1024, help="Tokenizer max length.")
    parser.add_argument("--effort", type=float, default=0.7, help="Effort scalar.")
    args = parser.parse_args()

    tokenizer = AutoTokenizer.from_pretrained(args.tokenizer_repo)
    combined = f"{args.system}\n\nUser: {args.user}"
    enc = tokenizer(
        combined,
        add_special_tokens=True,
        max_length=args.max_length,
        padding="max_length",
        truncation=True,
        return_attention_mask=True,
        return_tensors="np",
    )
    input_ids = enc["input_ids"]
    attention_mask = enc["attention_mask"]

    core = ov.Core()
    model_path = os.path.join(args.model_dir, "openvino_model.xml")
    compiled = core.compile_model(core.read_model(model_path), args.device)
    output = compiled(build_input_map(compiled, input_ids, attention_mask))
    last_hidden = next(iter(output.values()))
    cls_vec = last_hidden[:, 0, :]

    weights = load_head_weights(args.router_head, args.cache_dir)
    effort_vec = mlp_effort(np.array([[args.effort]], dtype=np.float32), weights)
    logits = classify(cls_vec, effort_vec, weights)
    probs = softmax(logits)
    idx = int(np.argmax(probs, axis=1)[0])
    approach = APPROACHES[idx]
    confidence = float(probs[0][idx])

    print(f"approach={approach} confidence={confidence:.4f}")


if __name__ == "__main__":
    main()

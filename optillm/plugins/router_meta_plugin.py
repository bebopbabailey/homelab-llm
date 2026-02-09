import logging
import os
import time
import threading

import httpx
import torch
import torch.nn as nn
import torch.nn.functional as F
from flask import request
from huggingface_hub import hf_hub_download
from safetensors.torch import load_model
from transformers import AutoModel, AutoTokenizer

SLUG = "router_meta"

MAX_LENGTH = 1024
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

BASE_MODEL = "answerdotai/ModernBERT-large"
OPTILLM_MODEL_NAME = "codelion/optillm-modernbert-large"

LOCAL_ONLY_DEFAULT = {"bon", "moa", "mcts", "pvg"}
HOP_HEADER = "X-Opti-Hop"
FROM_HEADER = "X-Opti-From"
SOURCE_PROXY = "opti-proxy"
SOURCE_LOCAL = "opti-local"

LOCAL_URL = os.environ.get("ROUTER_META_LOCAL_URL", "http://127.0.0.1:4040/v1")
PROXY_URL = os.environ.get("ROUTER_META_PROXY_URL", "http://127.0.0.1:4020/v1")
LOCAL_BASE_MODEL = os.environ.get("ROUTER_META_LOCAL_MODEL", "")
LOCAL_AUTH = os.environ.get("ROUTER_META_LOCAL_AUTH", "")
PROXY_AUTH = os.environ.get("ROUTER_META_PROXY_AUTH", "")
TIMEOUT_S = float(os.environ.get("ROUTER_META_TIMEOUT_S", "120"))
DEFAULT_DESTINATION = os.environ.get("ROUTER_META_DEFAULT_DESTINATION", "proxy").lower()
FALLBACK_POLICY = os.environ.get("ROUTER_META_FALLBACK", "none").lower()


def _parse_set(value, default):
    if not value:
        return set(default)
    return {item.strip() for item in value.split(",") if item.strip()}


LOCAL_ONLY = _parse_set(os.environ.get("ROUTER_META_LOCAL_ONLY", ""), LOCAL_ONLY_DEFAULT)
PROXY_ONLY = _parse_set(os.environ.get("ROUTER_META_PROXY_ONLY", ""), set())

_ROUTER_LOCK = threading.Lock()
_ROUTER_CACHE = None  # (model, tokenizer, device)

logger = logging.getLogger("optillm.router_meta")


class OptILMClassifier(nn.Module):
    def __init__(self, base_model, num_labels):
        super().__init__()
        self.base_model = base_model
        self.effort_encoder = nn.Sequential(
            nn.Linear(1, 64),
            nn.ReLU(),
            nn.Linear(64, 64),
            nn.ReLU(),
        )
        self.classifier = nn.Linear(base_model.config.hidden_size + 64, num_labels)

    def forward(self, input_ids, attention_mask, effort):
        outputs = self.base_model(input_ids=input_ids, attention_mask=attention_mask)
        pooled_output = outputs.last_hidden_state[:, 0]
        effort_encoded = self.effort_encoder(effort.unsqueeze(1))
        combined_input = torch.cat((pooled_output, effort_encoded), dim=1)
        logits = self.classifier(combined_input)
        return logits


def load_optillm_model():
    device = torch.device(
        "mps" if torch.backends.mps.is_available()
        else "cuda" if torch.cuda.is_available()
        else "cpu"
    )
    base_model = AutoModel.from_pretrained(BASE_MODEL)
    model = OptILMClassifier(base_model, num_labels=len(APPROACHES))
    model.to(device)
    safetensors_path = hf_hub_download(repo_id=OPTILLM_MODEL_NAME, filename="model.safetensors")
    load_model(model, safetensors_path)
    tokenizer = AutoTokenizer.from_pretrained(OPTILLM_MODEL_NAME)
    return model, tokenizer, device


def get_optillm_model():
    global _ROUTER_CACHE
    if _ROUTER_CACHE is not None:
        return _ROUTER_CACHE
    with _ROUTER_LOCK:
        if _ROUTER_CACHE is None:
            _ROUTER_CACHE = load_optillm_model()
    return _ROUTER_CACHE


def preprocess_input(tokenizer, system_prompt, initial_query):
    combined_input = f"{system_prompt}\n\nUser: {initial_query}"
    encoding = tokenizer.encode_plus(
        combined_input,
        add_special_tokens=True,
        max_length=MAX_LENGTH,
        padding="max_length",
        truncation=True,
        return_attention_mask=True,
        return_tensors="pt",
    )
    return encoding["input_ids"], encoding["attention_mask"]


def predict_approach(model, input_ids, attention_mask, device, effort=0.7):
    model.eval()
    with torch.no_grad():
        input_ids = input_ids.to(device)
        attention_mask = attention_mask.to(device)
        effort_tensor = torch.tensor([effort], dtype=torch.float).to(device)
        logits = model(input_ids, attention_mask=attention_mask, effort=effort_tensor)
        probabilities = F.softmax(logits, dim=1)
        predicted_approach_index = torch.argmax(probabilities, dim=1).item()
        confidence = probabilities[0][predicted_approach_index].item()
    return APPROACHES[predicted_approach_index], confidence


def _build_forward_payload(raw, model_override):
    payload = dict(raw)
    payload.pop("optillm_approach", None)
    payload["model"] = model_override
    return payload


def _auth_header(default_auth, incoming_auth):
    if default_auth:
        return {"Authorization": f"Bearer {default_auth}"}
    if incoming_auth:
        return {"Authorization": incoming_auth}
    return {}

def _choose_destination(approach):
    if approach in LOCAL_ONLY:
        return "local"
    if approach in PROXY_ONLY:
        return "proxy"
    return DEFAULT_DESTINATION

def _apply_fallback():
    if FALLBACK_POLICY == "error":
        raise RuntimeError("router_meta fallback policy set to error")
    if FALLBACK_POLICY in ("none", "re2", "cot_reflection"):
        return FALLBACK_POLICY
    return "none"


def run(system_prompt, initial_query, client, model, request_config=None):
    start = time.perf_counter()
    raw = request.get_json(silent=True) or {}
    incoming_auth = request.headers.get("Authorization", "")
    hop = request.headers.get(HOP_HEADER)
    origin = request.headers.get(FROM_HEADER)

    if hop or origin:
        logger.info("router_meta hop/origin detected; bypassing routing")
        payload = _build_forward_payload(raw, raw.get("model", model))
        headers = _auth_header(PROXY_AUTH, incoming_auth)
        headers[HOP_HEADER] = "1"
        headers[FROM_HEADER] = origin or SOURCE_PROXY
        with httpx.Client(timeout=TIMEOUT_S) as http:
            resp = http.post(f"{PROXY_URL}/chat/completions", headers=headers, json=payload)
        return resp.json(), 0

    router_model, tokenizer, device = get_optillm_model()
    input_ids, attention_mask = preprocess_input(tokenizer, system_prompt, initial_query)
    approach, confidence = predict_approach(router_model, input_ids, attention_mask, device)

    original_model = raw.get("model", model)
    destination = _choose_destination(approach)
    target_url = PROXY_URL
    target_model = original_model if approach == "none" else f"{approach}-{original_model}"
    headers = _auth_header(PROXY_AUTH, incoming_auth)

    if destination == "local":
        target_url = LOCAL_URL
        if not LOCAL_BASE_MODEL:
            logger.warning("router_meta local route requested but ROUTER_META_LOCAL_MODEL is unset; falling back")
            fallback = _apply_fallback()
            destination = "proxy"
            if fallback != "none":
                approach = fallback
            target_model = original_model if approach == "none" else f"{approach}-{original_model}"
        else:
            target_model = f"{approach}-{LOCAL_BASE_MODEL}"
            headers = _auth_header(LOCAL_AUTH, incoming_auth)

    payload = _build_forward_payload(raw, target_model)
    headers[HOP_HEADER] = "1"
    headers[FROM_HEADER] = SOURCE_PROXY

    with httpx.Client(timeout=TIMEOUT_S) as http:
        try:
            resp = http.post(f"{target_url}/chat/completions", headers=headers, json=payload)
            response_json = resp.json()
        except Exception as exc:
            logger.warning("router_meta forward failed (%s). applying fallback", exc)
            fallback = _apply_fallback()
            if fallback == "error":
                raise
            if fallback != "none":
                approach = fallback
            payload = _build_forward_payload(raw, original_model if approach == "none" else f"{approach}-{original_model}")
            headers = _auth_header(PROXY_AUTH, incoming_auth)
            headers[HOP_HEADER] = "1"
            headers[FROM_HEADER] = SOURCE_PROXY
            resp = http.post(f"{PROXY_URL}/chat/completions", headers=headers, json=payload)
            response_json = resp.json()

    latency_ms = int((time.perf_counter() - start) * 1000)
    meta = {
        "approach": approach,
        "confidence": confidence,
        "destination": destination,
        "latency_ms": latency_ms,
        "model": target_model,
    }
    response_json["optillm_meta"] = meta
    logger.info(
        "router_meta approach=%s confidence=%.4f destination=%s latency_ms=%d",
        approach,
        confidence,
        destination,
        latency_ms,
    )
    return response_json, 0

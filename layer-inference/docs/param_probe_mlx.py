#!/usr/bin/env python3
import json
import time
import urllib.request
import urllib.error

MODELS = {
    "mlx-gpt-oss-120b-mxfp4-q4": "http://192.168.1.72:8100/v1/chat/completions",
    "mlx-gemma-3-27b-it-qat-4bit": "http://192.168.1.72:8101/v1/chat/completions",
    "mlx-gpt-oss-20b-mxfp4-q4": "http://192.168.1.72:8102/v1/chat/completions",
}

PROMPTS = {
    "base": "Ping with a short response.",
    "stop": "Say 'alpha STOP beta' and nothing else.",
    "penalty": "Repeat the word blue ten times, separated by spaces.",
}

TIMEOUT = 10


def post(url, payload):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, body
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode("utf-8")
        except Exception:
            body = ""
        return e.code, body
    except Exception as e:
        return "error", str(e)


def extract_text(body):
    try:
        data = json.loads(body)
    except Exception:
        return None
    try:
        return "".join([c["message"]["content"] or "" for c in data.get("choices", [])])
    except Exception:
        return None


def has_logprobs(body):
    try:
        data = json.loads(body)
    except Exception:
        return False
    for choice in data.get("choices", []):
        if "logprobs" in choice and choice["logprobs"] is not None:
            return True
    return False


def choices_count(body):
    try:
        data = json.loads(body)
    except Exception:
        return None
    return len(data.get("choices", []))


def probe_model(model, url):
    results = {}

    # temperature effect (0 vs 1)
    base = {"model": model, "messages": [{"role": "user", "content": PROMPTS["base"]}], "max_tokens": 32}
    s0, b0 = post(url, {**base, "temperature": 0})
    s1, b1 = post(url, {**base, "temperature": 1})
    results["temperature"] = {
        "status": [s0, s1],
        "effect_detected": extract_text(b0) != extract_text(b1),
    }

    # top_p effect (0.1 vs 1.0)
    s2, b2 = post(url, {**base, "temperature": 0.8, "top_p": 0.1})
    s3, b3 = post(url, {**base, "temperature": 0.8, "top_p": 1.0})
    results["top_p"] = {
        "status": [s2, s3],
        "effect_detected": extract_text(b2) != extract_text(b3),
    }

    # presence_penalty effect
    s4, b4 = post(url, {**base, "temperature": 0.5, "presence_penalty": 0.0})
    s5, b5 = post(url, {**base, "temperature": 0.5, "presence_penalty": 0.8})
    results["presence_penalty"] = {
        "status": [s4, s5],
        "effect_detected": extract_text(b4) != extract_text(b5),
    }

    # frequency_penalty effect
    s6, b6 = post(url, {**base, "temperature": 0.5, "frequency_penalty": 0.0})
    s7, b7 = post(url, {**base, "temperature": 0.5, "frequency_penalty": 0.8})
    results["frequency_penalty"] = {
        "status": [s6, s7],
        "effect_detected": extract_text(b6) != extract_text(b7),
    }

    # stop
    stop_base = {"model": model, "messages": [{"role": "user", "content": PROMPTS["stop"]}], "max_tokens": 64}
    s8, b8 = post(url, {**stop_base, "stop": ["STOP"]})
    results["stop"] = {
        "status": [s8],
        "contains_STOP": ("STOP" in (extract_text(b8) or "")),
    }

    # n
    s9, b9 = post(url, {**base, "n": 2})
    results["n"] = {
        "status": [s9],
        "choices": choices_count(b9),
    }

    # logprobs
    s10, b10 = post(url, {**base, "logprobs": True})
    results["logprobs"] = {
        "status": [s10],
        "has_logprobs": has_logprobs(b10),
    }

    # seed determinism (same seed twice)
    s11, b11 = post(url, {**base, "temperature": 0.8, "seed": 1234})
    s12, b12 = post(url, {**base, "temperature": 0.8, "seed": 1234})
    results["seed"] = {
        "status": [s11, s12],
        "deterministic": extract_text(b11) == extract_text(b12),
    }

    # max_completion_tokens (if supported)
    s13, b13 = post(url, {**base, "max_completion_tokens": 8})
    results["max_completion_tokens"] = {"status": [s13]}

    return results


def main():
    report = {"timestamp": time.time(), "models": {}}
    for model, url in MODELS.items():
        report["models"][model] = probe_model(model, url)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

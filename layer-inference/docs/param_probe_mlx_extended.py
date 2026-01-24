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

TIMEOUT = 8
BASE_MESSAGES = [{"role": "user", "content": "ping"}]

PARAM_TESTS = {
    "temperature": {"temperature": 0.2},
    "top_p": {"top_p": 0.9},
    "top_k": {"top_k": 64},
    "min_p": {"min_p": 0.05},
    "presence_penalty": {"presence_penalty": 0.4},
    "frequency_penalty": {"frequency_penalty": 0.2},
    "repetition_penalty": {"repetition_penalty": 1.1},
    "max_tokens": {"max_tokens": 2},
    "max_completion_tokens": {"max_completion_tokens": 2},
    "stop": {"stop": ["STOP"]},
    "seed": {"seed": 1234},
    "logprobs": {"logprobs": True},
    "top_logprobs": {"logprobs": True, "top_logprobs": 3},
    "logit_bias": {"logit_bias": {"42": -1}},
    "n": {"n": 2},
    "user": {"user": "probe-user"},
    "metadata": {"metadata": {"probe": "true"}},
    "response_format_json": {"response_format": {"type": "json_object"}},
    "response_format_schema": {"response_format": {"type": "json_schema", "json_schema": {"name": "probe", "schema": {"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": ["ok"]}}}},
    "tools": {
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "probe_fn",
                    "description": "Return ok=true",
                    "parameters": {"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": ["ok"]}
                }
            }
        ],
        "tool_choice": "auto"
    }
}


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


def extract_tool_calls(body):
    try:
        data = json.loads(body)
    except Exception:
        return None
    try:
        return data.get("choices", [])[0].get("message", {}).get("tool_calls")
    except Exception:
        return None


def probe_model(model, url):
    results = {}
    for name, extra in PARAM_TESTS.items():
        payload = {"model": model, "messages": BASE_MESSAGES, "max_tokens": 1}
        payload.update(extra)
        status, body = post(url, payload)
        entry = {"status": status}
        if status == 200:
            entry["text"] = extract_text(body)
            entry["tool_calls"] = extract_tool_calls(body)
        else:
            entry["error"] = body[:500] if isinstance(body, str) else str(body)
        results[name] = entry
        time.sleep(0.05)
    return results


def main():
    report = {"timestamp": time.time(), "models": {}}
    for model, url in MODELS.items():
        report["models"][model] = probe_model(model, url)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
import json
import os
import time

import httpx

PROMPTS = [
    "Summarize the key tradeoffs between A and B.",
    "Write a step-by-step plan to refactor a service safely.",
    "Explain the difference between synchronous and asynchronous IO.",
    "List risks and mitigations for a home lab upgrade.",
    "Write a short, clear error message for a login failure.",
    "Give a high-level outline for a research report.",
    "Compare two caching strategies and when to use each.",
    "Explain how TLS works at a conceptual level.",
    "Draft a checklist for a systemd service migration.",
    "Describe pros/cons of monolith vs microservices.",
]

BASE_URL = os.environ.get("ROUTER_META_PROXY_URL", "http://192.168.1.72:4020/v1")
API_KEY = os.environ.get("OPTILLM_API_KEY", "")
MODEL = os.environ.get("ROUTER_META_MODEL", "mlx-gpt-oss-120b-mxfp4-q4")
def main() -> None:
    headers = {"Content-Type": "application/json"}
    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"

    with httpx.Client(timeout=60.0) as client:
        for idx, prompt in enumerate(PROMPTS, 1):
            payload = {
                "model": MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 16,
                "optillm_approach": "router_meta",
            }
            start = time.perf_counter()
            resp = client.post(f"{BASE_URL}/chat/completions", headers=headers, json=payload)
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            data = resp.json()
            meta = data.get("optillm_meta", {})
            print(json.dumps({
                "id": idx,
                "http": resp.status_code,
                "approach": meta.get("approach"),
                "destination": meta.get("destination"),
                "latency_ms": meta.get("latency_ms"),
                "roundtrip_ms": elapsed_ms,
            }))


if __name__ == "__main__":
    main()

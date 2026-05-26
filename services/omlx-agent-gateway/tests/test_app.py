from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest import mock

from fastapi.testclient import TestClient

from omlx_agent_gateway.app import app
from omlx_agent_gateway.settings import Settings


class UpstreamHandler(BaseHTTPRequestHandler):
    status = 200
    body = {"id": "chatcmpl-upstream", "model": "omlx-qwen36-27b-optiq-4bit", "choices": []}
    captured_body = None
    captured_headers = None
    stream_body = None

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers["Content-Length"])
        UpstreamHandler.captured_body = self.rfile.read(length)
        UpstreamHandler.captured_headers = dict(self.headers.items())
        self.send_response(self.status)
        if UpstreamHandler.stream_body is not None:
            self.send_header("Content-Type", "text/event-stream")
        else:
            self.send_header("Content-Type", "application/json")
        self.end_headers()
        if UpstreamHandler.stream_body is not None:
            self.wfile.write(UpstreamHandler.stream_body)
        else:
            self.wfile.write(json.dumps(self.body).encode("utf-8"))

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return


def _settings(**overrides):
    values = {
        "public_model_id": "omlx-qwen36-27b-optiq-4bit",
        "backend_model": "omlx-qwen36-27b-optiq-4bit",
        "backend_base_url": "http://127.0.0.1:1/v1",
        "backend_api_key": "",
        "auth_token": "",
    }
    values.update(overrides)
    return Settings(**values)


def test_health_reports_configured_backend():
    with mock.patch("omlx_agent_gateway.app.load_settings", return_value=_settings()):
        response = TestClient(app).get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["model"] == "omlx-qwen36-27b-optiq-4bit"


def test_models_and_model_info_shape():
    with mock.patch("omlx_agent_gateway.app.load_settings", return_value=_settings()):
        client = TestClient(app)
        models = client.get("/v1/models")
        info = client.get("/v1/model/info")
    assert models.status_code == 200
    assert models.json()["data"][0]["id"] == "omlx-qwen36-27b-optiq-4bit"
    row = info.json()["data"][0]
    assert row["model_name"] == "omlx-qwen36-27b-optiq-4bit"
    assert row["model_info"]["supports_function_calling"] is True
    assert row["model_info"]["max_input_tokens"] == 32768


def test_auth_is_enforced_when_configured():
    with mock.patch("omlx_agent_gateway.app.load_settings", return_value=_settings(auth_token="secret")):
        client = TestClient(app)
        assert client.get("/v1/models").status_code == 401
        assert client.get("/v1/models", headers={"Authorization": "Bearer secret"}).status_code == 200


def test_chat_passthrough_normalizes_model_and_preserves_tools():
    server = ThreadingHTTPServer(("127.0.0.1", 0), UpstreamHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        settings = _settings(
            public_model_id="public-qwen",
            backend_model="omlx-qwen36-27b-optiq-4bit",
            backend_base_url=f"http://127.0.0.1:{server.server_port}/v1",
            backend_api_key="backend-key",
        )
        payload = {
            "model": "public-qwen",
            "messages": [{"role": "user", "content": "Call noop."}],
            "tools": [{"type": "function", "function": {"name": "noop", "parameters": {"type": "object"}}}],
            "tool_choice": "auto",
            "stream": False,
        }
        with mock.patch("omlx_agent_gateway.app.load_settings", return_value=settings):
            response = TestClient(app).post("/v1/chat/completions", json=payload)
    finally:
        server.shutdown()
        server.server_close()
    assert response.status_code == 200
    assert response.headers["x-request-id"]
    assert response.json()["model"] == "public-qwen"
    sent = json.loads(UpstreamHandler.captured_body.decode("utf-8"))
    assert sent["model"] == "omlx-qwen36-27b-optiq-4bit"
    assert sent["tools"][0]["function"]["name"] == "noop"
    assert UpstreamHandler.captured_headers["Authorization"] == "Bearer backend-key"
    assert any(key.lower() == "traceparent" for key in UpstreamHandler.captured_headers)


def test_chat_rejects_unknown_model():
    with mock.patch("omlx_agent_gateway.app.load_settings", return_value=_settings()):
        client = TestClient(app)
        unknown = client.post(
            "/v1/chat/completions",
            json={"model": "other", "messages": [], "stream": False},
        )
    assert unknown.status_code == 404


def test_streaming_chat_is_passed_through():
    UpstreamHandler.stream_body = b"data: {\"choices\":[]}\n\ndata: [DONE]\n\n"
    server = ThreadingHTTPServer(("127.0.0.1", 0), UpstreamHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        settings = _settings(backend_base_url=f"http://127.0.0.1:{server.server_port}/v1")
        with mock.patch("omlx_agent_gateway.app.load_settings", return_value=settings):
            response = TestClient(app).post(
                "/v1/chat/completions",
                json={"model": "omlx-qwen36-27b-optiq-4bit", "messages": [], "stream": True},
            )
    finally:
        UpstreamHandler.stream_body = None
        server.shutdown()
        server.server_close()
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "data: [DONE]" in response.text


def test_upstream_down_is_clean_502():
    with mock.patch("omlx_agent_gateway.app.load_settings", return_value=_settings()):
        response = TestClient(app).post(
            "/v1/chat/completions",
            json={"model": "omlx-qwen36-27b-optiq-4bit", "messages": [], "stream": False},
        )
    assert response.status_code == 502
    assert response.json()["error"]["type"] == "upstream_transport_error"

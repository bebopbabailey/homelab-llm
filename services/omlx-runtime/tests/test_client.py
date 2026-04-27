from __future__ import annotations

import json
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from omlx_runtime_client import (
    OmlxRuntimeClient,
    OmlxRuntimeContractError,
    OmlxRuntimeParseError,
    OmlxRuntimeTransportError,
    OmlxRuntimeUpstreamHttpError,
    append_jsonl_record,
    build_failure_record,
    build_success_record,
)


VALID_PAYLOAD = {
    "model": "Qwen3-4B-Instruct-2507-4bit",
    "messages": [
        {"role": "system", "content": "You are a coding assistant."},
        {"role": "user", "content": "Summarize this fixture."},
    ],
    "temperature": 0,
    "top_p": 1,
    "max_tokens": 128,
    "stream": False,
}


class RecordingHandler(BaseHTTPRequestHandler):
    response_status = 200
    response_body = b'{"id":"ok","choices":[]}'
    captured_headers = None
    captured_body = None

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers["Content-Length"])
        RecordingHandler.captured_headers = dict(self.headers.items())
        RecordingHandler.captured_body = self.rfile.read(length)
        self.send_response(self.response_status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(self.response_body)

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return


class OmlxRuntimeClientTests(unittest.TestCase):
    def _run_server(self) -> tuple[ThreadingHTTPServer, str]:
        server = ThreadingHTTPServer(("127.0.0.1", 0), RecordingHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        return server, f"http://127.0.0.1:{server.server_port}"

    def test_forwards_valid_payload_without_rewriting(self) -> None:
        server, base_url = self._run_server()
        self.addCleanup(server.shutdown)
        self.addCleanup(server.server_close)
        RecordingHandler.response_status = 200
        RecordingHandler.response_body = b'{"id":"resp-1","choices":[]}'
        client = OmlxRuntimeClient(base_url=base_url, bearer_token="token")
        response = client.chat_completions(VALID_PAYLOAD)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.body["id"], "resp-1")
        self.assertEqual(
            json.loads(RecordingHandler.captured_body.decode("utf-8")),
            VALID_PAYLOAD,
        )
        self.assertEqual(
            RecordingHandler.captured_headers["Authorization"], "Bearer token"
        )
        self.assertEqual(RecordingHandler.captured_headers["Accept"], "application/json")

    def test_rejects_stream_true(self) -> None:
        client = OmlxRuntimeClient(base_url="http://127.0.0.1:1", bearer_token="token")
        bad = dict(VALID_PAYLOAD)
        bad["stream"] = True
        with self.assertRaises(OmlxRuntimeContractError):
            client.chat_completions(bad)

    def test_rejects_tools_shape(self) -> None:
        client = OmlxRuntimeClient(base_url="http://127.0.0.1:1", bearer_token="token")
        bad = dict(VALID_PAYLOAD)
        bad["tools"] = []
        with self.assertRaises(OmlxRuntimeContractError):
            client.chat_completions(bad)

    def test_rejects_non_string_message_content(self) -> None:
        client = OmlxRuntimeClient(base_url="http://127.0.0.1:1", bearer_token="token")
        bad = dict(VALID_PAYLOAD)
        bad["messages"] = [
            {"role": "system", "content": "ok"},
            {"role": "user", "content": [{"type": "text", "text": "bad"}]},
        ]
        with self.assertRaises(OmlxRuntimeContractError):
            client.chat_completions(bad)

    def test_wraps_upstream_http_error(self) -> None:
        server, base_url = self._run_server()
        self.addCleanup(server.shutdown)
        self.addCleanup(server.server_close)
        RecordingHandler.response_status = 503
        RecordingHandler.response_body = b'{"error":"unavailable"}'
        client = OmlxRuntimeClient(base_url=base_url, bearer_token="token")
        with self.assertRaises(OmlxRuntimeUpstreamHttpError) as ctx:
            client.chat_completions(VALID_PAYLOAD)
        self.assertEqual(ctx.exception.status_code, 503)
        self.assertIn("unavailable", ctx.exception.body)

    def test_wraps_invalid_json_response(self) -> None:
        server, base_url = self._run_server()
        self.addCleanup(server.shutdown)
        self.addCleanup(server.server_close)
        RecordingHandler.response_status = 200
        RecordingHandler.response_body = b"not-json"
        client = OmlxRuntimeClient(base_url=base_url, bearer_token="token")
        with self.assertRaises(OmlxRuntimeParseError):
            client.chat_completions(VALID_PAYLOAD)

    def test_wraps_transport_error(self) -> None:
        client = OmlxRuntimeClient(base_url="http://127.0.0.1:9", bearer_token="token", timeout_seconds=0.1)
        with self.assertRaises(OmlxRuntimeTransportError):
            client.chat_completions(VALID_PAYLOAD)


class TelemetryHelpersTests(unittest.TestCase):
    def test_jsonl_writer_appends_records(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            path = Path(tempdir) / "ledger.jsonl"
            success = build_success_record(
                request_id="req-1",
                fixture_id="S02",
                manifest_hash="abc",
                concurrency_class="c2",
                target_model="Qwen3-4B-Instruct-2507-4bit",
                endpoint="http://127.0.0.1:8129",
                status_code=200,
                latency_seconds=1.23,
                request_bytes=100,
                response_bytes=200,
            )
            failure = build_failure_record(
                request_id="req-2",
                fixture_id="S04",
                manifest_hash="def",
                concurrency_class="c2",
                target_model="Qwen3-4B-Instruct-2507-4bit",
                endpoint="http://127.0.0.1:8129",
                failure_class="adapter_transport_error",
                error_message="boom",
            )
            append_jsonl_record(path, success)
            append_jsonl_record(path, failure)
            lines = path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), 2)
            self.assertEqual(json.loads(lines[0])["request_id"], "req-1")
            self.assertEqual(json.loads(lines[1])["failure_class"], "adapter_transport_error")


if __name__ == "__main__":
    unittest.main()

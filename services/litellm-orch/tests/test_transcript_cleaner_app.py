import asyncio
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient


REPO_ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = REPO_ROOT / "services/litellm-orch/transcript_cleaner_app.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("transcript_cleaner_app", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules["transcript_cleaner_app"] = module
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


cleaner = _load_module()


class TranscriptCleanerAppTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        cleaner.set_config_for_tests(
            cleaner.CleanerConfig(
                job_dir=Path(self.tmp.name),
                litellm_base_url="http://litellm.test/v1",
                api_key="test-key",
                chunk_chars=5,
                max_output_tokens=8192,
                max_upload_bytes=128,
            )
        )
        self.original_call = cleaner.call_task_transcribe

    def tearDown(self):
        cleaner.call_task_transcribe = self.original_call
        cleaner.set_config_for_tests(None)
        self.tmp.cleanup()

    def test_chunk_text_preserves_order(self):
        self.assertEqual(cleaner.chunk_text("abcdefghijkl", 5), ["abcde", "fghij", "kl"])

    def test_extract_response_text_uses_output_text(self):
        self.assertEqual(cleaner.extract_response_text({"output_text": " cleaned "}), "cleaned")

    def test_extract_response_text_uses_responses_output(self):
        payload = {
            "output": [
                {
                    "type": "message",
                    "content": [{"type": "output_text", "text": "hello"}],
                }
            ]
        }
        self.assertEqual(cleaner.extract_response_text(payload), "hello")

    def test_create_text_job_runs_and_downloads_output(self):
        async def fake_call(config, text):
            return text.upper()

        cleaner.call_task_transcribe = fake_call
        client = TestClient(cleaner.app)

        created = client.post("/jobs", json={"text": "hello world", "filename": "meeting.txt"})
        self.assertEqual(created.status_code, 202)
        job_id = created.json()["job_id"]

        status = client.get(f"/jobs/{job_id}")
        self.assertEqual(status.json()["state"], "done")
        self.assertEqual(status.json()["processed_chunks"], 3)

        output = client.get(f"/jobs/{job_id}/output")
        self.assertEqual(output.status_code, 200)
        self.assertEqual(output.text, "HELLO\n\nWORL\n\nD\n")
        self.assertIn("meeting.cleaned.txt", output.headers["content-disposition"])

    def test_rejects_non_txt_filename(self):
        client = TestClient(cleaner.app)
        response = client.post("/jobs", json={"text": "hello", "filename": "meeting.pdf"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("only .txt", response.text)

    def test_rejects_oversize_text(self):
        client = TestClient(cleaner.app)
        response = client.post("/jobs", json={"text": "x" * 129, "filename": "meeting.txt"})
        self.assertEqual(response.status_code, 413)

    def test_run_job_skips_existing_cleaned_chunks(self):
        calls = []

        async def fake_call(config, text):
            calls.append(text)
            return f"clean:{text}"

        cleaner.call_task_transcribe = fake_call
        job_id = "a" * 32
        job_path = Path(self.tmp.name) / job_id
        (job_path / "cleaned_chunks").mkdir(parents=True)
        (job_path / "cleaned_chunks/0001.txt").write_text("already", encoding="utf-8")
        (job_path / "input.txt").write_text("helloworld", encoding="utf-8")
        cleaner._write_json(
            job_path / "status.json",
            {
                "job_id": job_id,
                "state": "pending",
                "filename": "transcript.txt",
                "total_chunks": 0,
                "processed_chunks": 0,
                "error": None,
            },
        )

        asyncio.run(cleaner.run_job(job_id))

        self.assertEqual(calls, ["world"])
        self.assertEqual((job_path / "output.txt").read_text(encoding="utf-8"), "already\n\nclean:world\n")

    def test_call_task_transcribe_payload(self):
        seen = {}

        class FakeResponse:
            status_code = 200

            def json(self):
                return {"output_text": "cleaned"}

        class FakeClient:
            def __init__(self, timeout):
                self.timeout = timeout

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return None

            async def post(self, url, headers, json):
                seen["url"] = url
                seen["headers"] = headers
                seen["json"] = json
                return FakeResponse()

        original_client = cleaner.httpx.AsyncClient
        cleaner.httpx.AsyncClient = FakeClient
        try:
            text = asyncio.run(cleaner.call_task_transcribe(cleaner.get_config(), "raw words"))
        finally:
            cleaner.httpx.AsyncClient = original_client

        self.assertEqual(text, "cleaned")
        self.assertEqual(seen["url"], "http://litellm.test/v1/responses")
        self.assertEqual(seen["headers"]["Authorization"], "Bearer test-key")
        self.assertEqual(seen["json"]["model"], "task-transcribe")
        self.assertEqual(seen["json"]["input"], [{"role": "user", "content": "raw words"}])
        self.assertEqual(seen["json"]["max_output_tokens"], 8192)


if __name__ == "__main__":
    unittest.main()

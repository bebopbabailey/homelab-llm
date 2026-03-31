import ipaddress
import os
import unittest
from pathlib import Path
from unittest import mock

import httpx

import web_fetch_mcp as mod

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "extraction"


class FakeSearchResponse:
    def __init__(self, payload=None, exception=None):
        self._payload = payload
        self._exception = exception

    def raise_for_status(self):
        if self._exception is not None:
            raise self._exception

    def json(self):
        return self._payload


class FakeStreamResponse:
    def __init__(self, url, status_code=200, headers=None, chunks=None, encoding="utf-8"):
        self.url = httpx.URL(url)
        self.status_code = status_code
        self.headers = httpx.Headers(headers or {})
        self.encoding = encoding
        self._chunks = list(chunks or [])

    def raise_for_status(self):
        if self.status_code >= 400:
            request = httpx.Request("GET", str(self.url))
            response = httpx.Response(self.status_code, request=request)
            raise httpx.HTTPStatusError(
                f"status={self.status_code}",
                request=request,
                response=response,
            )

    def iter_bytes(self):
        for chunk in self._chunks:
            yield chunk


class FakeStreamContext:
    def __init__(self, response):
        self.response = response

    def __enter__(self):
        return self.response

    def __exit__(self, exc_type, exc, tb):
        return False


class FakeClient:
    def __init__(self, post_response=None, post_exception=None, stream_steps=None):
        self.post_response = post_response
        self.post_exception = post_exception
        self.stream_steps = list(stream_steps or [])
        self.stream_requests = []

    def post(self, *args, **kwargs):
        if self.post_exception is not None:
            raise self.post_exception
        return self.post_response

    def stream(self, method, url, headers=None):
        self.stream_requests.append((method, url, headers))
        if not self.stream_steps:
            raise AssertionError("unexpected stream call")
        step = self.stream_steps.pop(0)
        if isinstance(step, Exception):
            raise step
        return FakeStreamContext(step)


class WebFetchMcpTests(unittest.TestCase):
    def tearDown(self):
        mod._close_client()

    def _fixture_bytes(self, name: str) -> bytes:
        return (FIXTURES_DIR / name).read_bytes()

    def test_build_client_uses_explicit_policy(self):
        with mock.patch.dict(
            os.environ,
            {
                "WEB_FETCH_CONNECT_TIMEOUT": "7",
                "WEB_FETCH_READ_TIMEOUT": "8",
                "WEB_FETCH_WRITE_TIMEOUT": "9",
                "WEB_FETCH_POOL_TIMEOUT": "10",
                "WEB_FETCH_MAX_CONNECTIONS": "11",
                "WEB_FETCH_MAX_KEEPALIVE_CONNECTIONS": "12",
                "WEB_FETCH_KEEPALIVE_EXPIRY": "13",
                "WEB_FETCH_USER_AGENT": "custom-agent",
            },
            clear=False,
        ):
            with mock.patch("web_fetch_mcp.httpx.Client") as mock_client:
                mod._build_client()

        kwargs = mock_client.call_args.kwargs
        self.assertFalse(kwargs["trust_env"])
        self.assertTrue(kwargs["verify"])
        self.assertFalse(kwargs["follow_redirects"])
        self.assertEqual(kwargs["headers"]["User-Agent"], "custom-agent")
        self.assertEqual(kwargs["limits"].max_connections, 11)
        self.assertEqual(kwargs["limits"].max_keepalive_connections, 12)
        self.assertEqual(kwargs["limits"].keepalive_expiry, 13.0)
        self.assertEqual(kwargs["timeout"].connect, 7.0)
        self.assertEqual(kwargs["timeout"].read, 8.0)
        self.assertEqual(kwargs["timeout"].write, 9.0)
        self.assertEqual(kwargs["timeout"].pool, 10.0)

    def test_search_web_normalizes_results_preserves_order_and_clamps(self):
        payload = {
            "results": [
                {"title": "First", "url": "https://one.example/a", "snippet": "A", "date": "2025-01-01"},
                {"title": "Drop", "url": "ftp://bad.example/file", "snippet": "bad"},
                {"url": "https://two.example/b"},
                {"title": "Third", "url": "https://three.example/c", "snippet": "C"},
            ]
        }
        fake_client = FakeClient(post_response=FakeSearchResponse(payload=payload))

        with mock.patch("web_fetch_mcp._get_client", return_value=fake_client):
            result = mod.search_web("  example  ", max_results=2)

        self.assertEqual(
            result,
            {
                "results": [
                    {"title": "First", "url": "https://one.example/a", "snippet": "A", "date": "2025-01-01"},
                    {"title": "", "url": "https://two.example/b", "snippet": "", "date": None},
                ]
            },
        )

    def test_search_web_normalizes_data_shape(self):
        payload = {"data": [{"name": "Doc", "link": "https://docs.example", "description": "ref"}]}
        fake_client = FakeClient(post_response=FakeSearchResponse(payload=payload))

        with mock.patch("web_fetch_mcp._get_client", return_value=fake_client):
            result = mod.search_web("docs", max_results=5)

        self.assertEqual(
            result,
            {"results": [{"title": "Doc", "url": "https://docs.example", "snippet": "ref", "date": None}]},
        )

    def test_search_web_rejects_invalid_inputs(self):
        with self.assertRaisesRegex(mod.ToolContractError, r"^invalid_query:"):
            mod.search_web("   ")
        with self.assertRaisesRegex(mod.ToolContractError, r"^invalid_query:"):
            mod.search_web("ok", max_results=0)

    def test_search_web_maps_upstream_failure(self):
        request = httpx.Request("POST", "http://127.0.0.1:4000/v1/search/searxng-search")
        response = httpx.Response(502, request=request)
        fake_client = FakeClient(
            post_response=FakeSearchResponse(
                exception=httpx.HTTPStatusError("bad gateway", request=request, response=response)
            )
        )
        with mock.patch("web_fetch_mcp._get_client", return_value=fake_client):
            with self.assertRaisesRegex(mod.ToolContractError, r"^upstream_failure: HTTPStatusError status=502$"):
                mod.search_web("example")

    def test_web_fetch_rejects_invalid_url_and_blocked_ip_literal(self):
        with self.assertRaisesRegex(mod.ToolContractError, r"^invalid_url:"):
            mod.web_fetch("notaurl")
        with self.assertRaisesRegex(mod.ToolContractError, r"^url_not_allowed:"):
            mod.web_fetch("http://127.0.0.1/")

    def test_web_fetch_rejects_missing_or_malformed_content_type(self):
        for content_type in (None, "nonsense"):
            fake_client = FakeClient(
                stream_steps=[
                    FakeStreamResponse(
                        "https://public.example/page",
                        headers={} if content_type is None else {"content-type": content_type},
                        chunks=[b"hello"],
                    )
                ]
            )
            with self.subTest(content_type=content_type):
                with mock.patch("web_fetch_mcp._get_client", return_value=fake_client):
                    with mock.patch("web_fetch_mcp._resolve_host_ips", return_value=[ipaddress.ip_address("93.184.216.34")]):
                        with self.assertRaisesRegex(mod.ToolContractError, r"^mime_not_allowed:"):
                            mod.web_fetch("https://public.example/page")

    def test_web_fetch_rejects_pdf(self):
        fake_client = FakeClient(
            stream_steps=[
                FakeStreamResponse(
                    "https://public.example/file.pdf",
                    headers={"content-type": "application/pdf"},
                    chunks=[b"%PDF-1.4"],
                )
            ]
        )
        with mock.patch("web_fetch_mcp._get_client", return_value=fake_client):
            with mock.patch("web_fetch_mcp._resolve_host_ips", return_value=[ipaddress.ip_address("93.184.216.34")]):
                with self.assertRaisesRegex(mod.ToolContractError, r"^mime_not_allowed:"):
                    mod.web_fetch("https://public.example/file.pdf")

    def test_web_fetch_enforces_body_cap_with_header_and_stream(self):
        with mock.patch.dict(os.environ, {"WEB_FETCH_MAX_BYTES": "4"}, clear=False):
            header_client = FakeClient(
                stream_steps=[
                    FakeStreamResponse(
                        "https://public.example/page",
                        headers={"content-type": "text/plain", "content-length": "10"},
                        chunks=[b"tiny"],
                    )
                ]
            )
            with mock.patch("web_fetch_mcp._get_client", return_value=header_client):
                with mock.patch("web_fetch_mcp._resolve_host_ips", return_value=[ipaddress.ip_address("93.184.216.34")]):
                    with self.assertRaisesRegex(mod.ToolContractError, r"^body_too_large:"):
                        mod.web_fetch("https://public.example/page")

            stream_client = FakeClient(
                stream_steps=[
                    FakeStreamResponse(
                        "https://public.example/page",
                        headers={"content-type": "text/plain"},
                        chunks=[b"abc", b"def"],
                    )
                ]
            )
            with mock.patch("web_fetch_mcp._get_client", return_value=stream_client):
                with mock.patch("web_fetch_mcp._resolve_host_ips", return_value=[ipaddress.ip_address("93.184.216.34")]):
                    with self.assertRaisesRegex(mod.ToolContractError, r"^body_too_large:"):
                        mod.web_fetch("https://public.example/page")

    def test_web_fetch_handles_relative_and_scheme_relative_redirects(self):
        fake_client = FakeClient(
            stream_steps=[
                FakeStreamResponse(
                    "https://public.example/start",
                    status_code=302,
                    headers={"location": "//public.example/final#frag"},
                ),
                FakeStreamResponse(
                    "https://public.example/final",
                    headers={"content-type": "text/plain; charset=utf-8"},
                    chunks=[b"hello world"],
                ),
            ]
        )
        with mock.patch("web_fetch_mcp._get_client", return_value=fake_client):
            with mock.patch("web_fetch_mcp._resolve_host_ips", return_value=[ipaddress.ip_address("93.184.216.34")]):
                payload = mod.web_fetch("https://public.example/start#source-frag")
        self.assertEqual(payload["final_url"], "https://public.example/final")
        self.assertEqual(payload["content_type"], "text/plain")
        self.assertEqual(payload["extractor_used"], "plain_text")
        self.assertEqual(payload["clean_text"], "hello world")

    def test_web_fetch_rejects_blocked_redirect_and_redirect_limit(self):
        blocked_client = FakeClient(
            stream_steps=[
                FakeStreamResponse(
                    "https://public.example/start",
                    status_code=302,
                    headers={"location": "http://127.0.0.1/private"},
                )
            ]
        )
        with mock.patch("web_fetch_mcp._get_client", return_value=blocked_client):
            with mock.patch(
                "web_fetch_mcp._resolve_host_ips",
                side_effect=[
                    [ipaddress.ip_address("93.184.216.34")],
                    [ipaddress.ip_address("127.0.0.1")],
                ],
            ):
                with self.assertRaisesRegex(mod.ToolContractError, r"^redirect_not_allowed:"):
                    mod.web_fetch("https://public.example/start")

        loop_client = FakeClient(
            stream_steps=[
                FakeStreamResponse(
                    f"https://public.example/{idx}",
                    status_code=302,
                    headers={"location": f"/{idx + 1}"},
                )
                for idx in range(6)
            ]
        )
        with mock.patch.dict(os.environ, {"WEB_FETCH_MAX_REDIRECTS": "2"}, clear=False):
            with mock.patch("web_fetch_mcp._get_client", return_value=loop_client):
                with mock.patch("web_fetch_mcp._resolve_host_ips", return_value=[ipaddress.ip_address("93.184.216.34")]):
                    with self.assertRaisesRegex(mod.ToolContractError, r"^redirect_limit_exceeded:"):
                        mod.web_fetch("https://public.example/0")

    def test_web_fetch_trafilatura_success_and_truncation(self):
        fake_client = FakeClient(
            stream_steps=[
                FakeStreamResponse(
                    "https://public.example/article",
                    headers={"content-type": "text/html; charset=utf-8"},
                    chunks=[b"<html><body>ignored</body></html>"],
                )
            ]
        )
        with mock.patch.dict(
            os.environ,
            {"WEB_FETCH_MAX_CLEAN_TEXT_CHARS": "5", "WEB_FETCH_MAX_RAW_HTML_CHARS": "10"},
            clear=False,
        ):
            with mock.patch("web_fetch_mcp._get_client", return_value=fake_client):
                with mock.patch("web_fetch_mcp._resolve_host_ips", return_value=[ipaddress.ip_address("93.184.216.34")]):
                    with mock.patch(
                        "web_fetch_mcp._extract_with_trafilatura",
                        return_value={
                            "text": "abcdefg",
                            "title": "Title",
                            "author": "Author",
                            "date": "2025-03-20",
                            "language": "en",
                        },
                    ):
                        payload = mod.web_fetch("https://public.example/article", include_raw_html=True)

        self.assertEqual(payload["clean_text"], "abcde")
        self.assertEqual(payload["extractor_used"], "trafilatura")
        self.assertEqual(payload["title"], "Title")
        self.assertEqual(payload["byline"], "Author")
        self.assertEqual(payload["published_at"], "2025-03-20")
        self.assertEqual(payload["lang"], "en")
        self.assertEqual(payload["raw_html"], "<html><bod")
        self.assertEqual(len(payload["content_sha256"]), 64)

    def test_extract_with_trafilatura_normalizes_document_result(self):
        data = mod._extract_with_trafilatura(
            "<html><body><article><h1>Hello</h1><p>World body.</p></article></body></html>",
            "https://public.example/article",
        )
        self.assertIsNotNone(data)
        self.assertIn("World body.", data["text"])
        self.assertIn("title", data)

    def test_web_fetch_readability_fallback(self):
        fake_client = FakeClient(
            stream_steps=[
                FakeStreamResponse(
                    "https://public.example/article",
                    headers={"content-type": "text/html"},
                    chunks=[b"<html><body>ignored</body></html>"],
                )
            ]
        )
        with mock.patch("web_fetch_mcp._get_client", return_value=fake_client):
            with mock.patch("web_fetch_mcp._resolve_host_ips", return_value=[ipaddress.ip_address("93.184.216.34")]):
                with mock.patch("web_fetch_mcp._extract_with_trafilatura", return_value=None):
                    with mock.patch(
                        "web_fetch_mcp._extract_with_readability",
                        return_value={"text": "readability text", "title": "R", "author": None, "date": None, "language": None},
                    ):
                        payload = mod.web_fetch("https://public.example/article")
        self.assertEqual(payload["extractor_used"], "readability")
        self.assertEqual(payload["clean_text"], "readability text")

    def test_web_fetch_text_plain_and_parse_failure(self):
        plain_client = FakeClient(
            stream_steps=[
                FakeStreamResponse(
                    "https://public.example/plain",
                    headers={"content-type": "text/plain"},
                    chunks=[b"  alpha\nbeta  "],
                )
            ]
        )
        with mock.patch("web_fetch_mcp._get_client", return_value=plain_client):
            with mock.patch("web_fetch_mcp._resolve_host_ips", return_value=[ipaddress.ip_address("93.184.216.34")]):
                payload = mod.web_fetch("https://public.example/plain")
        self.assertEqual(payload["clean_text"], "alpha beta")
        self.assertEqual(payload["extractor_used"], "plain_text")
        self.assertNotIn("raw_html", payload)

        empty_client = FakeClient(
            stream_steps=[
                FakeStreamResponse(
                    "https://public.example/empty",
                    headers={"content-type": "text/html"},
                    chunks=[b"<html><body></body></html>"],
                )
            ]
        )
        with mock.patch("web_fetch_mcp._get_client", return_value=empty_client):
            with mock.patch("web_fetch_mcp._resolve_host_ips", return_value=[ipaddress.ip_address("93.184.216.34")]):
                with mock.patch("web_fetch_mcp._extract_with_trafilatura", return_value=None):
                    with mock.patch("web_fetch_mcp._extract_with_readability", return_value=None):
                        with mock.patch("web_fetch_mcp._text_from_html", return_value="   "):
                            with self.assertRaisesRegex(mod.ToolContractError, r"^parse_failed:"):
                                mod.web_fetch("https://public.example/empty")

    def test_web_fetch_timeout_mapping(self):
        timeouts = [
            httpx.ConnectTimeout("connect timeout"),
            httpx.ReadTimeout("read timeout"),
            httpx.PoolTimeout("pool timeout"),
        ]
        for exc in timeouts:
            fake_client = FakeClient(stream_steps=[exc])
            with self.subTest(exc=exc.__class__.__name__):
                with mock.patch("web_fetch_mcp._get_client", return_value=fake_client):
                    with mock.patch("web_fetch_mcp._resolve_host_ips", return_value=[ipaddress.ip_address("93.184.216.34")]):
                        with self.assertRaisesRegex(mod.ToolContractError, rf"^timeout: {exc.__class__.__name__}:"):
                            mod.web_fetch("https://public.example/page")

    def test_web_fetch_default_text_mode_stays_unchanged(self):
        fake_client = FakeClient(
            stream_steps=[
                FakeStreamResponse(
                    "https://public.example/plain",
                    headers={"content-type": "text/plain"},
                    chunks=[b"alpha beta"],
                )
            ]
        )
        with mock.patch("web_fetch_mcp._get_client", return_value=fake_client):
            with mock.patch("web_fetch_mcp._resolve_host_ips", return_value=[ipaddress.ip_address("93.184.216.34")]):
                payload = mod.web_fetch("https://public.example/plain")

        self.assertEqual(payload["clean_text"], "alpha beta")
        self.assertEqual(payload["extractor_used"], "plain_text")
        self.assertNotIn("markdown", payload)
        self.assertNotIn("links", payload)
        self.assertNotIn("quality_label", payload)

    def test_web_fetch_evidence_mode_article_fixture(self):
        fake_client = FakeClient(
            stream_steps=[
                FakeStreamResponse(
                    "https://public.example/posts/sample-article",
                    headers={"content-type": "text/html; charset=utf-8"},
                    chunks=[self._fixture_bytes("article.html")],
                )
            ]
        )
        with mock.patch("web_fetch_mcp._get_client", return_value=fake_client):
            with mock.patch("web_fetch_mcp._resolve_host_ips", return_value=[ipaddress.ip_address("93.184.216.34")]):
                payload = mod.web_fetch("https://public.example/posts/sample-article", output_mode="evidence")

        self.assertIn("# Sample Article", payload["markdown"])
        self.assertIn("[Reference doc](https://docs.example.com/guide)", payload["markdown"])
        self.assertEqual(payload["canonical_url"], "https://public.example/posts/sample-article")
        self.assertEqual(payload["site_name"], "Example Journal")
        self.assertEqual(payload["description"], "A compact article fixture for evidence-mode extraction.")
        self.assertIn({"text": "Reference doc", "url": "https://docs.example.com/guide"}, payload["links"])
        self.assertEqual(payload["quality_label"], "high")
        self.assertEqual(payload["quality_flags"], [])
        self.assertGreaterEqual(payload["content_stats"]["heading_count"], 1)
        self.assertGreaterEqual(payload["content_stats"]["list_count"], 1)
        self.assertGreaterEqual(payload["content_stats"]["link_count"], 1)

    def test_web_fetch_evidence_mode_docs_fixture_preserves_code_and_links(self):
        fake_client = FakeClient(
            stream_steps=[
                FakeStreamResponse(
                    "https://docs.example.com/start",
                    headers={"content-type": "text/html; charset=utf-8"},
                    chunks=[self._fixture_bytes("docs.html")],
                )
            ]
        )
        with mock.patch("web_fetch_mcp._get_client", return_value=fake_client):
            with mock.patch("web_fetch_mcp._resolve_host_ips", return_value=[ipaddress.ip_address("93.184.216.34")]):
                payload = mod.web_fetch("https://docs.example.com/start", output_mode="evidence")

        self.assertIn("Install", payload["markdown"])
        self.assertIn("uv run python -m demo", payload["markdown"])
        self.assertIn({"text": "API reference", "url": "https://docs.example.com/api"}, payload["links"])
        self.assertIn(payload["quality_label"], {"high", "medium"})
        self.assertNotIn("fallback_used", payload["quality_flags"])

    def test_web_fetch_evidence_mode_repeated_layout_sets_flags(self):
        fake_client = FakeClient(
            stream_steps=[
                FakeStreamResponse(
                    "https://public.example/catalog",
                    headers={"content-type": "text/html; charset=utf-8"},
                    chunks=[self._fixture_bytes("repeated-layout.html")],
                )
            ]
        )
        with mock.patch("web_fetch_mcp._get_client", return_value=fake_client):
            with mock.patch("web_fetch_mcp._resolve_host_ips", return_value=[ipaddress.ip_address("93.184.216.34")]):
                payload = mod.web_fetch("https://public.example/catalog", output_mode="evidence")

        self.assertIn("needs_structured_extraction", payload["quality_flags"])
        self.assertIn(payload["quality_label"], {"medium", "low"})
        self.assertGreaterEqual(payload["content_stats"]["link_count"], 8)

    def test_web_fetch_evidence_mode_uses_readability_only_as_rescue(self):
        fake_client = FakeClient(
            stream_steps=[
                FakeStreamResponse(
                    "https://public.example/article",
                    headers={"content-type": "text/html"},
                    chunks=[b"<html><body>ignored</body></html>"],
                )
            ]
        )
        with mock.patch("web_fetch_mcp._get_client", return_value=fake_client):
            with mock.patch("web_fetch_mcp._resolve_host_ips", return_value=[ipaddress.ip_address("93.184.216.34")]):
                with mock.patch("web_fetch_mcp._extract_markdown_with_trafilatura", return_value=None):
                    with mock.patch("web_fetch_mcp._extract_with_trafilatura", return_value=None):
                        with mock.patch(
                            "web_fetch_mcp._extract_with_readability",
                            return_value={"text": "readability text", "title": "Fallback Title", "author": None, "date": None, "language": None},
                        ):
                            payload = mod.web_fetch("https://public.example/article", output_mode="evidence")

        self.assertEqual(payload["extractor_used"], "readability")
        self.assertTrue(payload["markdown"].startswith("# Fallback Title"))
        self.assertIn("fallback_used", payload["quality_flags"])

    def test_web_fetch_evidence_mode_plain_text(self):
        fake_client = FakeClient(
            stream_steps=[
                FakeStreamResponse(
                    "https://public.example/plain",
                    headers={"content-type": "text/plain"},
                    chunks=[b"Visit https://example.com/path for more details."],
                )
            ]
        )
        with mock.patch("web_fetch_mcp._get_client", return_value=fake_client):
            with mock.patch("web_fetch_mcp._resolve_host_ips", return_value=[ipaddress.ip_address("93.184.216.34")]):
                payload = mod.web_fetch("https://public.example/plain", output_mode="evidence")

        self.assertEqual(payload["markdown"], "Visit https://example.com/path for more details.")
        self.assertEqual(payload["links"], [{"text": "https://example.com/path", "url": "https://example.com/path"}])
        self.assertEqual(payload["extractor_used"], "plain_text")

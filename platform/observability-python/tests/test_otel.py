from __future__ import annotations

from homelab_observability import bounded_json, bounded_text, inject_trace_headers, redact_mapping


def test_bounded_text_caps_utf8_content() -> None:
    value = bounded_text("abcdef", limit_bytes=3)
    assert value.startswith("abc")
    assert "truncated" in value


def test_redact_mapping_redacts_secret_like_keys() -> None:
    assert redact_mapping({"Authorization": "Bearer secret", "model": "qwen"}) == {
        "Authorization": "[redacted]",
        "model": "qwen",
    }


def test_bounded_json_redacts_nested_secret() -> None:
    rendered = bounded_json({"headers": {"api_key": "secret"}, "messages": ["hello"]})
    assert "secret" not in rendered
    assert "[redacted]" in rendered


def test_inject_trace_headers_returns_mapping() -> None:
    headers = inject_trace_headers({"Content-Type": "application/json"})
    assert headers["Content-Type"] == "application/json"

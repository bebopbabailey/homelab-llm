from __future__ import annotations

import json
import os
from contextlib import contextmanager
from typing import Any, Iterator, Mapping, MutableMapping

from opentelemetry import propagate, trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import SpanLimits, TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import Span, SpanKind, Status, StatusCode

DEFAULT_CONTENT_ATTRIBUTE_LIMIT_BYTES = 16 * 1024
CONTENT_ATTRIBUTE_LIMIT_ENV = "HOMELAB_OTEL_CONTENT_ATTRIBUTE_LIMIT_BYTES"
_SETUP_DONE = False
_SENSITIVE_KEY_PARTS = (
    "authorization",
    "bearer",
    "token",
    "api_key",
    "apikey",
    "secret",
    "password",
    "credential",
)


def setup_tracing(
    *,
    service_name: str,
    service_version: str | None = None,
    resource_attributes: Mapping[str, str] | None = None,
) -> None:
    """Configure OTLP/HTTP tracing once; export failures stay non-fatal."""
    global _SETUP_DONE
    if _SETUP_DONE or _sdk_disabled():
        return

    attributes: dict[str, str] = {"service.name": service_name}
    if service_version:
        attributes["service.version"] = service_version
    attributes.update(_parse_resource_attributes(os.getenv("OTEL_RESOURCE_ATTRIBUTES", "")))
    if resource_attributes:
        attributes.update({str(key): str(value) for key, value in resource_attributes.items()})

    provider = TracerProvider(
        resource=Resource.create(attributes),
        span_limits=SpanLimits(max_attribute_length=_content_limit(None)),
    )
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=_otlp_traces_endpoint())))
    trace.set_tracer_provider(provider)
    _SETUP_DONE = True


def instrument_fastapi_app(app: Any, *, excluded_urls: str | None = None) -> None:
    if getattr(app.state, "_homelab_otel_fastapi_instrumented", False):
        return
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

    kwargs: dict[str, str] = {}
    if excluded_urls:
        kwargs["excluded_urls"] = excluded_urls
    FastAPIInstrumentor.instrument_app(app, **kwargs)
    app.state._homelab_otel_fastapi_instrumented = True


def inject_trace_headers(headers: MutableMapping[str, str] | None = None) -> dict[str, str]:
    carrier: dict[str, str] = dict(headers or {})
    propagate.inject(carrier)
    return carrier


def current_trace_id() -> str:
    context = trace.get_current_span().get_span_context()
    if not context.is_valid:
        return ""
    return f"{context.trace_id:032x}"


@contextmanager
def start_as_current_span(
    name: str,
    *,
    attributes: Mapping[str, Any] | None = None,
    kind: SpanKind = SpanKind.INTERNAL,
) -> Iterator[Span]:
    tracer = trace.get_tracer("homelab.observability")
    with tracer.start_as_current_span(name, kind=kind, attributes=dict(attributes or {})) as span:
        try:
            yield span
        except Exception as exc:
            span.record_exception(exc)
            span.set_status(Status(StatusCode.ERROR, str(exc)))
            raise


def set_bounded_attribute(span: Span, key: str, value: Any, *, limit_bytes: int | None = None) -> None:
    span.set_attribute(key, bounded_text(value, limit_bytes=limit_bytes))


def set_llm_content_attributes(
    span: Span,
    *,
    prefix: str,
    messages: Any | None = None,
    prompt: Any | None = None,
    response: Any | None = None,
    limit_bytes: int | None = None,
) -> None:
    if messages is not None:
        set_bounded_attribute(span, f"{prefix}.messages", bounded_json(messages, limit_bytes=limit_bytes), limit_bytes=limit_bytes)
    if prompt is not None:
        set_bounded_attribute(span, f"{prefix}.prompt", prompt, limit_bytes=limit_bytes)
    if response is not None:
        set_bounded_attribute(span, f"{prefix}.response", response, limit_bytes=limit_bytes)


def bounded_json(value: Any, *, limit_bytes: int | None = None) -> str:
    try:
        rendered = json.dumps(redact_value(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    except TypeError:
        rendered = str(redact_value(value))
    return bounded_text(rendered, limit_bytes=limit_bytes)


def bounded_text(value: Any, *, limit_bytes: int | None = None) -> str:
    text = str(value)
    limit = _content_limit(limit_bytes)
    encoded = text.encode("utf-8")
    if len(encoded) <= limit:
        return text
    truncated = encoded[:limit].decode("utf-8", errors="ignore")
    return f"{truncated}...[truncated {len(encoded) - limit} bytes]"


def redact_mapping(mapping: Mapping[str, Any]) -> dict[str, Any]:
    return {str(key): _redacted_pair(str(key), value) for key, value in mapping.items()}


def redact_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return redact_mapping(value)
    if isinstance(value, list):
        return [redact_value(item) for item in value]
    if isinstance(value, tuple):
        return [redact_value(item) for item in value]
    return value


def _redacted_pair(key: str, value: Any) -> Any:
    lowered = key.lower()
    if any(part in lowered for part in _SENSITIVE_KEY_PARTS):
        return "[redacted]"
    return redact_value(value)


def _content_limit(limit_bytes: int | None) -> int:
    if limit_bytes is not None:
        return max(1, int(limit_bytes))
    raw = os.getenv(CONTENT_ATTRIBUTE_LIMIT_ENV, str(DEFAULT_CONTENT_ATTRIBUTE_LIMIT_BYTES))
    try:
        return max(1, int(raw))
    except ValueError:
        return DEFAULT_CONTENT_ATTRIBUTE_LIMIT_BYTES


def _sdk_disabled() -> bool:
    return os.getenv("OTEL_SDK_DISABLED", "").strip().lower() in {"1", "true", "yes", "on"}


def _otlp_traces_endpoint() -> str:
    explicit = os.getenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT", "").strip()
    if explicit:
        return explicit
    base = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://127.0.0.1:4318").strip().rstrip("/")
    if base.endswith("/v1/traces"):
        return base
    return f"{base}/v1/traces"


def _parse_resource_attributes(raw: str) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for item in raw.split(","):
        if not item or "=" not in item:
            continue
        key, value = item.split("=", 1)
        parsed[key.strip()] = value.strip()
    return parsed

from __future__ import annotations

import logging
import os

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
try:
    from opentelemetry.instrumentation.flask import FlaskInstrumentor
except ImportError:  # Optional dependency
    FlaskInstrumentor = None
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


logger = logging.getLogger("orchestrators_v2.observability")


def init_otel(app) -> None:
    if os.getenv("ORCH_OTEL_ENABLED", "0") != "1":
        return

    service_name = os.getenv("ORCH_SERVICE_NAME", "orchestrators-v2")
    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)

    endpoint = os.getenv("ORCH_OTEL_EXPORTER_OTLP_ENDPOINT", "http://127.0.0.1:4318/v1/traces")
    exporter = OTLPSpanExporter(endpoint=endpoint)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    if FlaskInstrumentor is None:
        logger.warning("OpenTelemetry Flask instrumentation not installed; skipping instrumentation")
        return

    FlaskInstrumentor().instrument_app(app)
    logger.info("OpenTelemetry enabled", extra={"extra": {"endpoint": endpoint}})


def get_current_trace_context() -> dict[str, str] | None:
    if os.getenv("ORCH_OTEL_ENABLED", "0") != "1":
        return None

    span = trace.get_current_span()
    if not span:
        return None

    ctx = span.get_span_context()
    if not ctx or not ctx.is_valid:
        return None

    return {
        "trace_id": f"{ctx.trace_id:032x}",
        "span_id": f"{ctx.span_id:016x}",
    }


def get_current_traceparent() -> str | None:
    if os.getenv("ORCH_OTEL_ENABLED", "0") != "1":
        return None

    span = trace.get_current_span()
    if not span:
        return None

    ctx = span.get_span_context()
    if not ctx or not ctx.is_valid:
        return None

    trace_id = f"{ctx.trace_id:032x}"
    span_id = f"{ctx.span_id:016x}"
    flags = f"{int(ctx.trace_flags):02x}"
    return f"00-{trace_id}-{span_id}-{flags}"

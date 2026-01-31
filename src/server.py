import hashlib
import logging
import os
import time
import uuid
import json
from flask import Flask, g, request
from dotenv import load_dotenv
from prometheus_client import Counter, Histogram, CollectorRegistry
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from src.orchestrator import Orchestrator
from src.observability import init_otel, get_current_trace_context, get_current_traceparent
from src.tracer import configure_tracer_metrics
from src.http_routes import register_routes

load_dotenv()

LOG_LEVEL = os.getenv("ORCH_LOG_LEVEL", "INFO").upper()
LOG_JSON = os.getenv("ORCH_LOG_JSON", "1") == "1"


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:  # pragma: no cover - logging
        base = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "timestamp": int(record.created * 1000),
        }
        if hasattr(record, "extra") and isinstance(record.extra, dict):
            base.update(record.extra)
        return json.dumps(base, separators=(",", ":"))


logger = logging.getLogger("orchestrators_v2")
logger.setLevel(LOG_LEVEL)
_handler = logging.StreamHandler()
_handler.setFormatter(JsonFormatter() if LOG_JSON else logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
if not logger.handlers:
    logger.addHandler(_handler)

RATE_LIMIT_ENABLED = os.getenv("ORCH_RATE_LIMIT_ENABLED", "1") == "1"
RATE_LIMIT = os.getenv("ORCH_RATE_LIMIT", "60 per minute")
RATE_LIMIT_STORAGE_URL = os.getenv("ORCH_RATE_LIMIT_STORAGE_URL")
ORCH_ENV = os.getenv("ORCH_ENV", "development").lower()


def _rate_limit_key() -> str:
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return hashlib.sha256(auth_header.encode()).hexdigest()[:16]
    return get_remote_address()


def create_app() -> Flask:
    app = Flask(__name__)
    init_otel(app)

    max_request_bytes = int(os.getenv("ORCH_MAX_REQUEST_BYTES", "1048576"))
    app.config["MAX_CONTENT_LENGTH"] = max_request_bytes

    if ORCH_ENV == "production" and RATE_LIMIT_ENABLED and not RATE_LIMIT_STORAGE_URL:
        raise RuntimeError("ORCH_RATE_LIMIT_STORAGE_URL is required in production when rate limiting is enabled")

    limiter = (
        Limiter(
            app=app,
            key_func=_rate_limit_key,
            default_limits=[RATE_LIMIT],
            storage_uri=RATE_LIMIT_STORAGE_URL,
        )
        if RATE_LIMIT_ENABLED
        else None
    )

    metrics_registry = CollectorRegistry(auto_describe=True)
    request_count = Counter(
        "orch_requests_total",
        "Total requests",
        ["route", "method", "status"],
        registry=metrics_registry,
    )
    request_latency = Histogram(
        "orch_request_latency_seconds",
        "Request latency",
        ["route", "method"],
        registry=metrics_registry,
    )
    error_count = Counter(
        "orch_errors_total",
        "Total errors",
        ["route", "method", "status"],
        registry=metrics_registry,
    )
    shadow_total = Counter(
        "orch_router_shadow_total",
        "Total shadow-mode routing comparisons",
        registry=metrics_registry,
    )
    shadow_mismatch = Counter(
        "orch_router_shadow_mismatch",
        "Total shadow-mode routing mismatches",
        registry=metrics_registry,
    )

    configure_tracer_metrics(metrics_registry)

    app.config["ORCH_LIMITER"] = limiter
    app.config["ORCH_RATE_LIMIT"] = RATE_LIMIT
    app.config["ORCH_METRICS_REGISTRY"] = metrics_registry
    app.config["ORCH_REQUEST_COUNT"] = request_count
    app.config["ORCH_REQUEST_LATENCY"] = request_latency
    app.config["ORCH_ERROR_COUNT"] = error_count
    app.config["ORCH_ORCHESTRATOR"] = Orchestrator(
        shadow_total_counter=shadow_total,
        shadow_mismatch_counter=shadow_mismatch,
    )

    @app.before_request
    def start_request():
        g.request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        g.request_start = time.time()
        otel_context = get_current_trace_context()
        if otel_context:
            g.otel_trace_id = otel_context.get("trace_id")
            g.otel_span_id = otel_context.get("span_id")
        g.otel_traceparent = request.headers.get("traceparent")

    @app.after_request
    def finalize_request(response):
        request_id = getattr(g, "request_id", None)
        if request_id:
            response.headers["X-Request-ID"] = request_id
        traceparent = get_current_traceparent()
        if traceparent:
            response.headers["traceparent"] = traceparent
            response.headers.setdefault("X-Trace-Id", traceparent.split("-")[1])
        route = request.path
        method = request.method
        status = str(response.status_code)
        duration = time.time() - getattr(g, "request_start", time.time())
        request_count.labels(route, method, status).inc()
        request_latency.labels(route, method).observe(duration)
        if response.status_code >= 500:
            error_count.labels(route, method, status).inc()

        logger.info(
            "request",
            extra={
                "extra": {
                    "request_id": request_id,
                    "route": route,
                    "method": method,
                    "status": response.status_code,
                    "latency_ms": int(duration * 1000),
                }
            },
        )
        return response

    register_routes(app)
    return app


app = create_app()


if __name__ == "__main__":
    port = int(os.getenv("ORCH_PORT", "8088"))
    host = os.getenv("ORCH_HOST", "127.0.0.1")
    app.run(host=host, port=port, debug=False)

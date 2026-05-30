import logging
import os
import sys

from fastapi import FastAPI
from google.cloud.logging_v2.handlers import StructuredLogHandler
from opentelemetry import propagate
from opentelemetry import trace as otel_trace
from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.propagators.cloud_trace_propagator import CloudTraceFormatPropagator
from opentelemetry.propagators.composite import CompositePropagator
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

from .models import ConsoleFormatter, LogContextFilter


def configure_observability(
    app: FastAPI,
    service_name: str,
    project_id: str | None = None,
) -> None:
    """Wire Cloud Trace + Cloud Logging + per-request log context onto ``app``.

    Uses official packages end-to-end:

    * :class:`FastAPIInstrumentor` — one SERVER span per request.
    * :class:`CompositePropagator` of ``CloudTraceFormatPropagator`` (Cloud
      Run inbound) + ``TraceContextTextMapPropagator`` (W3C ``traceparent``
      from our Cloud Tasks fan-out).
    * :class:`CloudTraceSpanExporter` — pushes spans to GCP Cloud Trace.
    * :class:`StructuredLogHandler` — formats logs in GCP's JSON shape and
      stamps ``logging.googleapis.com/trace`` from the active span.

    The only custom piece is :class:`LogContextFilter`, which attaches the
    per-request :class:`LogContext` bag to every record so business fields
    (e.g. ``market_id``) ride along automatically.

    Idempotent — re-running (uvicorn ``--reload``) is a no-op.
    """
    if getattr(app.state, "observability_installed", False):
        return

    provider = TracerProvider(
        resource=Resource.create({"service.name": service_name}),
    )
    exporter_kwargs: dict[str, str] = {"project_id": project_id} if project_id else {}
    provider.add_span_processor(
        BatchSpanProcessor(CloudTraceSpanExporter(**exporter_kwargs))
    )
    otel_trace.set_tracer_provider(provider)

    propagate.set_global_textmap(
        CompositePropagator(
            [
                CloudTraceFormatPropagator(),
                TraceContextTextMapPropagator(),
            ]
        )
    )

    FastAPIInstrumentor.instrument_app(app)

    is_remote = bool(os.environ.get("K_SERVICE") or os.environ.get("CLOUD_RUN_JOB"))
    root = logging.getLogger()
    for existing in list(root.handlers):
        root.removeHandler(existing)

    if is_remote:
        handler: logging.Handler = StructuredLogHandler(project_id=project_id)
    else:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(ConsoleFormatter())

    handler.addFilter(LogContextFilter())
    root.addHandler(handler)
    root.setLevel(logging.INFO)

    for noisy in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uv_logger = logging.getLogger(noisy)
        uv_logger.handlers = []
        uv_logger.propagate = True

    app.state.observability_installed = True

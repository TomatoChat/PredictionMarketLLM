from opentelemetry import propagate


def inject_trace_headers(headers: dict[str, str] | None = None) -> dict[str, str]:
    """Inject the active trace context into outbound HTTP headers.

    Respects the globally-configured propagator (set up in
    :func:`configure_observability` as a composite of ``x-cloud-trace-context``
    + W3C ``traceparent``), so the receiver — whether another Cloud Run
    service or a Cloud Task we enqueue — joins the same trace.
    """
    carrier: dict[str, str] = dict(headers) if headers else {}
    propagate.inject(carrier)
    return carrier

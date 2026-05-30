import asyncio
import functools
from collections.abc import Callable
from typing import Any

from opentelemetry import trace as otel_trace
from opentelemetry.trace import Status, StatusCode


def trace(
    func: Callable | None = None,
    *,
    name: str | None = None,
) -> Callable:
    """Wrap a function in an OTel span.

    Usable with or without arguments:

        @trace
        def f(): ...

        @trace(name="custom-span")
        async def g(): ...
    """

    def decorator(fn: Callable) -> Callable:
        span_name = name or fn.__name__

        if asyncio.iscoroutinefunction(fn):

            @functools.wraps(fn)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                tracer = otel_trace.get_tracer(fn.__module__)
                with tracer.start_as_current_span(span_name) as span:
                    try:
                        return await fn(*args, **kwargs)
                    except Exception as e:
                        span.record_exception(e)
                        span.set_status(Status(StatusCode.ERROR))
                        raise

            return async_wrapper

        @functools.wraps(fn)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            tracer = otel_trace.get_tracer(fn.__module__)
            with tracer.start_as_current_span(span_name) as span:
                try:
                    return fn(*args, **kwargs)
                except Exception as e:
                    span.record_exception(e)
                    span.set_status(Status(StatusCode.ERROR))
                    raise

        return sync_wrapper

    if func is not None:
        return decorator(func)

    return decorator

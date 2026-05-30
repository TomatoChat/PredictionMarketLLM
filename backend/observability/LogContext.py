from contextvars import ContextVar


class LogContext:
    """Per-request bag of structured log fields propagated via ``contextvars``.

    Handlers call :func:`bind_log_context` to attach business fields (e.g.
    ``market_id``, ``config_name``) once. The log filter then merges those
    fields onto every ``LogRecord`` emitted within the request, so callers
    don't need to pass them to each ``logger.info`` call.
    """

    _var: ContextVar[dict[str, object]] = ContextVar("observability_log_context")

    @classmethod
    def get(cls) -> dict[str, object]:
        return cls._var.get({})

    @classmethod
    def bind(cls, **fields: object) -> None:
        current = dict(cls._var.get({}))
        current.update(fields)
        cls._var.set(current)

    @classmethod
    def clear(cls) -> None:
        cls._var.set({})

from ..models.LogContext import LogContext


def bind_log_context(**fields: object) -> None:
    """Attach structured fields to every subsequent log line in this request.

    Example::

        bind_log_context(market_id=market_id, config_name=cfg)
        logger.info("starting predict")  # JSON payload includes both fields

    Scope is the active ``contextvars`` context — typically the request
    handler, which means fields don't leak across requests.
    """
    LogContext.bind(**fields)

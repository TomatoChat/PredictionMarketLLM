import logging

from .LogContext import LogContext


class LogContextFilter(logging.Filter):
    """Attach :class:`LogContext` fields to every ``LogRecord``.

    Runs before the handler's formatter so structured handlers
    (``StructuredLogHandler`` in Cloud Run; pretty in local dev) surface
    the fields in their respective output shapes.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        for key, value in LogContext.get().items():
            if not hasattr(record, key):
                setattr(record, key, value)
        return True

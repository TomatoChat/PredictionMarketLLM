import logging
from datetime import UTC, datetime

_RESERVED = frozenset(
    {
        "args",
        "asctime",
        "created",
        "exc_info",
        "exc_text",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "message",
        "module",
        "msecs",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "thread",
        "threadName",
        "taskName",
    }
)


class ConsoleFormatter(logging.Formatter):
    """Human-readable formatter for local dev (when ``K_SERVICE`` is unset).

    Appends ``LogContext`` fields inline so the same metadata visible in
    Cloud Logging shows up locally without the JSON noise.
    """

    def format(self, record: logging.LogRecord) -> str:
        ts = datetime.fromtimestamp(record.created, tz=UTC).strftime("%H:%M:%S")
        extras = {
            k: v
            for k, v in record.__dict__.items()
            if k not in _RESERVED and not k.startswith("_")
        }
        suffix = ""
        if extras:
            suffix = " " + " ".join(f"{k}={v}" for k, v in extras.items())

        line = (
            f"{ts} {record.levelname:<7} {record.name}: {record.getMessage()}{suffix}"
        )
        if record.exc_info:
            line += "\n" + self.formatException(record.exc_info)
        return line

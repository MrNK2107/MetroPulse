"""Logging set-up run once at import of app.main.

* The ``app`` logger (and so ``app.main``'s per-request lines from
  RequestLoggingMiddleware) gets a stderr handler with a JSON formatter at
  ``settings.log_level``. Uvicorn only configures its own loggers, so without
  this the request logs never reached the console.
* ``uvicorn.error`` and ``uvicorn.access`` get a filter that redacts the agent
  token (``/ws/agent?token=...``) and, on the access log, the free-text ``q=``
  search parameter, before any handler formats the record.
"""
from __future__ import annotations

import json
import logging
import re
import sys
from datetime import datetime, timezone
from typing import IO

_HANDLER_MARK = "_metropulse_json_handler"
REDACTED = "[REDACTED]"


class JsonFormatter(logging.Formatter):
    """One JSON object per line. A message that is itself a JSON object is merged in."""

    def format(self, record: logging.LogRecord) -> str:
        message = record.getMessage()
        payload: dict[str, object] = {
            "ts": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
        }
        parsed = None
        if message.startswith("{"):
            try:
                parsed = json.loads(message)
            except ValueError:
                parsed = None
        if isinstance(parsed, dict):
            payload.update(parsed)
        else:
            payload["message"] = message
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_app_logging(level: str = "INFO", stream: IO[str] | None = None) -> logging.Logger:
    """Attach (or replace) the JSON handler on the ``app`` logger and set its level."""
    log = logging.getLogger("app")
    log.setLevel(logging.getLevelName(str(level).upper()) if isinstance(level, str) else level)
    for handler in list(log.handlers):
        if getattr(handler, _HANDLER_MARK, False):
            log.removeHandler(handler)
    handler = logging.StreamHandler(stream if stream is not None else sys.stderr)
    handler.setFormatter(JsonFormatter())
    setattr(handler, _HANDLER_MARK, True)
    log.addHandler(handler)
    return log


class RedactingFilter(logging.Filter):
    """Rewrite secrets in a record's message and string args, keeping the args tuple's shape
    (uvicorn's AccessFormatter unpacks exactly five args)."""

    def __init__(self, params: tuple[str, ...]):
        super().__init__()
        self.params = params
        names = "|".join(re.escape(p) for p in params)
        # a param at the start of a query string or after ?, & or ;, up to the next separator
        self._pattern = re.compile(rf"(?<![A-Za-z0-9_])({names})=[^&\s\"';]*")

    def redact(self, text: str) -> str:
        return self._pattern.sub(lambda m: f"{m.group(1)}={REDACTED}", text)

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = self.redact(record.msg)
        if isinstance(record.args, tuple):
            record.args = tuple(self.redact(a) if isinstance(a, str) else a for a in record.args)
        elif isinstance(record.args, dict):
            record.args = {k: self.redact(v) if isinstance(v, str) else v for k, v in record.args.items()}
        return True


_REDACTION = {
    "uvicorn.error": ("token",),
    "uvicorn.access": ("token", "q"),
}


def install_uvicorn_redaction() -> None:
    """Idempotently add a RedactingFilter to uvicorn's error and access loggers."""
    for name, params in _REDACTION.items():
        log = logging.getLogger(name)
        for existing in list(log.filters):
            if isinstance(existing, RedactingFilter):
                log.removeFilter(existing)
        log.addFilter(RedactingFilter(params))


def setup_logging(level: str) -> None:
    configure_app_logging(level)
    install_uvicorn_redaction()

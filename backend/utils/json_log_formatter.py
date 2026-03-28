"""JSON formatter for production log aggregation systems."""

from __future__ import annotations

import json
import time
from logging import Formatter, LogRecord


class JsonLogFormatter(Formatter):
    """Render logs as compact JSON lines for observability pipelines."""

    def format(self, record: LogRecord) -> str:
        payload = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created)),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=True)

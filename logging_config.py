# c:\Mood_Market\logging_config.py
import json
import logging
import logging.handlers
import os
import re
from datetime import datetime, timezone
from utils.request_context import get_request_id, get_user_id


class JSONFormatter(logging.Formatter):
    """
    Log formatter structuring records to single-line JSON formats
    and sanitizing credentials, API keys, and passwords.
    """
    SENSITIVE_KEYS = re.compile(
        r'\b(api_key|password|token|secret|authorization)\b\s*[:=]\s*["\']?[a-zA-Z0-9_\-\.]+["\']?',
        re.IGNORECASE
    )

    def format(self, record: logging.LogRecord) -> str:
        req_id = get_request_id()
        usr_id = get_user_id()

        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger_name": record.name,
            "message": self.sanitize(record.getMessage()),
            "request_id": req_id,
            "user_id": usr_id
        }

        # Handle contextual extra dictionary
        if hasattr(record, "context") and isinstance(record.context, dict):
            log_data["context"] = self.sanitize_dict(record.context)
        else:
            log_data["context"] = {}

        if hasattr(record, "endpoint"):
            log_data["endpoint"] = record.endpoint

        if record.exc_info:
            log_data["exc_info"] = self.formatException(record.exc_info)

        return json.dumps(log_data)

    def sanitize(self, text: str) -> str:
        """Masks sensitive fields matching pattern inside log strings."""
        try:
            return self.SENSITIVE_KEYS.sub(r'\1: "[MASKED]"', text)
        except Exception:
            return text

    def sanitize_dict(self, d: dict) -> dict:
        """Recursively checks and masks fields containing credential keywords."""
        sanitized = {}
        mask_words = {"api_key", "password", "token", "secret", "authorization", "credentials", "bearer"}
        for k, v in d.items():
            if any(w in k.lower() for w in mask_words):
                sanitized[k] = "[MASKED]"
            elif isinstance(v, dict):
                sanitized[k] = self.sanitize_dict(v)
            else:
                sanitized[k] = v
        return sanitized


def setup_logging():
    """Initializes console and rotating file logging handlers globally."""
    os.makedirs("logs", exist_ok=True)

    root_logger = logging.getLogger()
    # Ensure root logger passes INFO levels to specific handlers
    root_logger.setLevel(logging.INFO)

    # Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(JSONFormatter())

    # File Handler (10MB rotating files)
    file_handler = logging.handlers.RotatingFileHandler(
        "logs/moodmarket.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=5
    )
    file_handler.setFormatter(JSONFormatter())

    # Replace default handlers with JSON configurations
    root_logger.handlers = [console_handler, file_handler]

    # Explicitly configure distinct logger layers
    loggers = ["api.logger", "ml.logger", "db.logger", "celery.logger", "cache.logger", "websocket.logger"]
    for logger_name in loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.INFO)
        logger.propagate = True

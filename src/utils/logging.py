"""Structured logging for Gulama — NEVER logs secrets."""

import re
import sys
from typing import Any

import structlog

from src.constants import SENSITIVE_PATTERNS


def _redact_secrets(_, __, event_dict: dict[str, Any]) -> dict[str, Any]:
    """Processor that redacts sensitive data from all log fields."""
    for key, value in list(event_dict.items()):
        if isinstance(value, str):
            event_dict[key] = _redact_string(value)
        elif isinstance(value, dict):
            event_dict[key] = {
                k: _redact_string(v) if isinstance(v, str) else v
                for k, v in value.items()
            }
    return event_dict


def _redact_string(text: str) -> str:
    """Replace any sensitive patterns found in text with [REDACTED]."""
    for pattern in SENSITIVE_PATTERNS:
        text = re.sub(pattern, "[REDACTED]", text)
    return text


def _add_project_info(_, __, event_dict: dict[str, Any]) -> dict[str, Any]:
    """Add project metadata to every log entry."""
    event_dict["service"] = "gulama"
    return event_dict


def setup_logging(level: str = "INFO", json_format: bool = True) -> None:
    """
    Configure structured logging for Gulama.

    All log output:
    - Is structured JSON (for machine parsing)
    - Has sensitive data redacted (API keys, tokens, credentials)
    - Includes timestamps, log levels, and service name
    - Never contains plaintext secrets
    """
    processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        _add_project_info,
        _redact_secrets,  # CRITICAL: Always redact before output
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if json_format:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer(colors=True))

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            _level_to_int(level)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = "") -> structlog.BoundLogger:
    """Get a logger instance. Secrets are automatically redacted."""
    logger = structlog.get_logger()
    if name:
        logger = logger.bind(component=name)
    return logger


def _level_to_int(level: str) -> int:
    """Convert string log level to integer."""
    levels = {
        "DEBUG": 10,
        "INFO": 20,
        "WARNING": 30,
        "ERROR": 40,
        "CRITICAL": 50,
    }
    return levels.get(level.upper(), 20)

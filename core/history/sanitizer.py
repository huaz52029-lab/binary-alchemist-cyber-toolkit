"""Unified sensitive-data redaction for history and reports."""

from __future__ import annotations

import re
from typing import Any

REDACTED = "[REDACTED]"

_SENSITIVE_KEY = re.compile(
    r"(authorization|proxy[-_]?authorization|cookie|set[-_]?cookie|password|passwd|"
    r"secret|token|api[_-]?key|private[_-]?key)",
    re.IGNORECASE,
)

_ASSIGNMENT = re.compile(
    r"(?i)\b(authorization|proxy-authorization|cookie|set-cookie|password|passwd|"
    r"secret|token|api_key|private_key)\b\s*[:=]\s*([^\s,;\"'&]+)",
)

_BEARER = re.compile(r"(?i)\b(bearer)\s+[A-Za-z0-9._~+/=-]+")


def sanitize_text(text: str) -> str:
    """Redact credential-style assignments and bearer tokens in plain text."""
    value = _BEARER.sub(r"\1 [REDACTED]", text)
    return _ASSIGNMENT.sub(r"\1=[REDACTED]", value)


def sanitize_json(value: Any) -> Any:
    """Recursively redact sensitive keys and credential strings in JSON data."""
    if isinstance(value, dict):
        return {
            key: REDACTED if _SENSITIVE_KEY.search(str(key)) else sanitize_json(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [sanitize_json(item) for item in value]
    if isinstance(value, str):
        return sanitize_text(value)
    return value


class SensitiveDataSanitizer:
    """Stateless facade over the sanitization helpers."""

    @staticmethod
    def text(text: str) -> str:
        return sanitize_text(text)

    @staticmethod
    def json(value: Any) -> Any:
        return sanitize_json(value)

    @staticmethod
    def summary(text: str, limit: int = 500) -> str:
        return sanitize_text(text)[:limit]

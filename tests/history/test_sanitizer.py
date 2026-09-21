"""Sensitive data sanitization."""

from __future__ import annotations

from core.history.sanitizer import sanitize_json, sanitize_text


def test_sanitize_text_credentials() -> None:
    text = "Authorization: Bearer secret123 Cookie: session=abc password=hunter2 token=xyz"
    sanitized = sanitize_text(text)
    assert "secret123" not in sanitized
    assert "session=abc" not in sanitized
    assert "hunter2" not in sanitized
    assert "xyz" not in sanitized
    assert sanitized.count("[REDACTED]") >= 4


def test_sanitize_json_keys_and_values() -> None:
    payload = {
        "headers": {"Authorization": "Bearer abc", "Cookie": "sid=1"},
        "password": "topsecret",
        "api_key": "key123",
        "nested": [{"token": "tok"}, {"safe": "ok"}],
    }
    sanitized = sanitize_json(payload)
    assert sanitized["password"] == "[REDACTED]"
    assert sanitized["api_key"] == "[REDACTED]"
    assert sanitized["headers"]["Authorization"] == "[REDACTED]"
    assert sanitized["headers"]["Cookie"] == "[REDACTED]"
    assert sanitized["nested"][0]["token"] == "[REDACTED]"
    assert sanitized["nested"][1]["safe"] == "ok"

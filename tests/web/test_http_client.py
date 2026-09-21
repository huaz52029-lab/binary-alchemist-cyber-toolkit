"""Unified HTTP client: local server, redirects, bounds and cancellation."""

from __future__ import annotations

import pytest

from core.exceptions import NetworkError, TaskCancelledError, ToolInputError
from infrastructure.network import HttpClient, normalize_web_url, redact_header_value


def test_get_status_and_headers(web_server: str) -> None:
    response = HttpClient().request(f"{web_server}/headers")
    assert response.status_code == 200
    assert response.first_header("Content-Security-Policy") == "default-src 'self'"
    assert len(response.header_values("Set-Cookie")) == 2


def test_head_request_no_body(web_server: str) -> None:
    response = HttpClient().request(f"{web_server}/ok", method="HEAD")
    assert response.status_code == 200
    assert response.body == b""


def test_redirect_chain_recorded(web_server: str) -> None:
    response = HttpClient().request(f"{web_server}/chain")
    assert response.status_code == 200
    assert [hop.status_code for hop in response.redirects] == [301, 302]
    assert response.final_url.endswith("/ok")


def test_not_found_and_server_error(web_server: str) -> None:
    assert HttpClient().request(f"{web_server}/missing").status_code == 404
    assert HttpClient().request(f"{web_server}/error").status_code == 500


def test_body_truncation(web_server: str) -> None:
    client = HttpClient(max_response_body=1024)
    response = client.request(f"{web_server}/big")
    assert response.body_truncated is True
    assert len(response.body or b"") == 1024


def test_timeout_raises_network_error(web_server: str) -> None:
    client = HttpClient(timeout=0.4)
    with pytest.raises(NetworkError) as exc_info:
        client.request(f"{web_server}/slow")
    assert exc_info.value.user_message == "请求超时，目标服务器未在时限内响应。"


def test_cancellation_propagates(web_server: str) -> None:
    with pytest.raises(TaskCancelledError):
        HttpClient().request(f"{web_server}/slow", is_cancelled=lambda: True)


def test_normalize_and_reject() -> None:
    assert normalize_web_url("example.com") == ("https://example.com", True)
    assert normalize_web_url("http://example.com") == ("http://example.com", False)
    with pytest.raises(ToolInputError):
        normalize_web_url("javascript:alert(1)")
    with pytest.raises(ToolInputError):
        normalize_web_url("")


def test_redaction() -> None:
    assert redact_header_value("Authorization", "Bearer secret") == "[REDACTED]"
    assert redact_header_value("Cookie", "session=x") == "[REDACTED]"
    assert redact_header_value("Server", "nginx") == "nginx"

"""JWT parser: structure, claims, errors and base64url handling."""

from __future__ import annotations

import json
import logging
import threading
import time

import pytest

from core.result import ResultStatus
from core.task import ExecutionContext
from infrastructure.crypto.base64url import base64url_decode, base64url_encode
from modules.crypto.jwt import JwtTool


def _context() -> ExecutionContext:
    return ExecutionContext(
        task_id="t-jwt",
        tool_id="crypto.jwt",
        logger=logging.getLogger("tests.jwt"),
        cancel_event=threading.Event(),
    )


def _token(header: dict[str, object], payload: dict[str, object], signature: str = "sig") -> str:
    def segment(value: dict[str, object]) -> str:
        return base64url_encode(json.dumps(value).encode("utf-8"))

    return f"{segment(header)}.{segment(payload)}.{signature}"


def test_base64url_helpers() -> None:
    assert base64url_decode("aGVsbG8") == b"hello"
    assert base64url_encode(b"hello") == "aGVsbG8"


def test_parse_header_and_payload() -> None:
    now = int(time.time())
    token = _token(
        {"alg": "HS256", "typ": "JWT"},
        {"sub": "1234567890", "name": "John", "iat": now, "exp": now + 3600},
    )
    result = JwtTool().run({"token": token}, _context())
    assert result.status is ResultStatus.SUCCESS
    assert result.data[0]["algorithm"] == "HS256"
    assert result.data[0]["type"] == "JWT"
    assert result.data[0]["subject"] == "1234567890"
    assert result.data[0]["signature_present"] == "是"
    assert any(finding.title == "exp 未过期" for finding in result.findings)


def test_expired_token_warns() -> None:
    now = int(time.time())
    token = _token({"alg": "HS256"}, {"sub": "1", "exp": now - 10})
    result = JwtTool().run({"token": token}, _context())
    assert any(finding.title == "Token 已过期" for finding in result.findings)


def test_missing_exp_warns() -> None:
    token = _token({"alg": "HS256"}, {"sub": "1"})
    result = JwtTool().run({"token": token}, _context())
    assert any(finding.title == "未发现 exp 字段" for finding in result.findings)


def test_missing_alg_warns() -> None:
    token = _token({"typ": "JWT"}, {"sub": "1"})
    result = JwtTool().run({"token": token}, _context())
    assert any(finding.title == "未发现 alg 字段" for finding in result.findings)


def test_empty_signature_warns() -> None:
    token = _token({"alg": "none"}, {"sub": "1"}, signature="")
    result = JwtTool().run({"token": token}, _context())
    assert any(finding.title == "没有签名内容" for finding in result.findings)


@pytest.mark.parametrize(
    "token",
    [
        "a.b",
        "a.b.c.d",
        "",
        "....",
    ],
)
def test_malformed_token_fails(token: str) -> None:
    result = JwtTool().run({"token": token}, _context())
    assert result.status is ResultStatus.FAILED
    assert "JWT 格式错误" in result.summary


def test_invalid_header_fails() -> None:
    token = _token({"alg": "HS256"}, {"sub": "1"})
    broken = f"not-base64.{token.split('.')[1]}.sig"
    result = JwtTool().run({"token": broken}, _context())
    assert result.status is ResultStatus.FAILED
    assert result.summary == "无法解析JWT Header。"


def test_invalid_payload_fails() -> None:
    token = _token({"alg": "HS256"}, {"sub": "1"})
    broken = f"{token.split('.')[0]}.not-base64.sig"
    result = JwtTool().run({"token": broken}, _context())
    assert result.status is ResultStatus.FAILED
    assert result.summary == "无法解析JWT Payload。"

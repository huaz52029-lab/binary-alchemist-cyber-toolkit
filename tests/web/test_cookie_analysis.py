"""Cookie parsing and attribute findings."""

from __future__ import annotations

import logging
import threading

from core.result import ResultStatus
from core.task import ExecutionContext
from modules.web.cookie_analysis import (
    CookieAnalysisTool,
    mask_set_cookie,
    parse_set_cookie,
)


def _context() -> ExecutionContext:
    return ExecutionContext(
        task_id="t-cookie",
        tool_id="web.cookie_analysis",
        logger=logging.getLogger("tests.cookie"),
        cancel_event=threading.Event(),
    )


def test_parse_set_cookie_attributes() -> None:
    cookie = parse_set_cookie(
        "session=abc123; Secure; HttpOnly; SameSite=Lax; Path=/; Max-Age=3600"
    )
    assert cookie.name == "session"
    assert cookie.value_masked == "abc***"
    assert cookie.secure is True
    assert cookie.http_only is True
    assert cookie.same_site == "Lax"
    assert cookie.path == "/"
    assert cookie.max_age == "3600"


def test_parse_minimal_cookie() -> None:
    cookie = parse_set_cookie("theme=dark")
    assert cookie.secure is False
    assert cookie.http_only is False
    assert cookie.same_site is None
    assert cookie.value_masked == "dar***"


def test_mask_set_cookie() -> None:
    masked = mask_set_cookie("session=supersecret; Secure; HttpOnly")
    assert "supersecret" not in masked
    assert masked.startswith("session=sup***;")
    assert "Secure" in masked


def test_tool_analyzes_cookies(web_server: str) -> None:
    result = CookieAnalysisTool().run({"url": f"{web_server}/headers"}, _context())
    assert result.status is ResultStatus.SUCCESS
    assert len(result.data) == 2
    secure_cookie = next(row for row in result.data if row["name"] == "session")
    assert secure_cookie["secure"] == "是"
    assert secure_cookie["http_only"] == "是"
    assert secure_cookie["same_site"] == "Lax"
    theme_cookie = next(row for row in result.data if row["name"] == "theme")
    assert theme_cookie["secure"] == "否"
    assert any("未设置 Secure" in finding.title for finding in result.findings)


def test_tool_no_cookies(web_server: str) -> None:
    result = CookieAnalysisTool().run({"url": f"{web_server}/ok"}, _context())
    assert result.status is ResultStatus.SUCCESS
    assert result.data == []
    assert result.summary == "响应中没有 Set-Cookie。"

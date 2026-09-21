"""URL parser: structure, query params, rejections and findings."""

from __future__ import annotations

import logging
import threading

import pytest

from core.result import ResultStatus
from core.task import ExecutionContext
from modules.web.url_parser import UrlParserTool


def _context() -> ExecutionContext:
    return ExecutionContext(
        task_id="t-url",
        tool_id="web.url_parser",
        logger=logging.getLogger("tests.url"),
        cancel_event=threading.Event(),
    )


def test_parse_full_url() -> None:
    result = UrlParserTool().run(
        {"url": "https://example.com:8443/path?a=1&b=hello#top"},
        _context(),
    )
    assert result.status is ResultStatus.SUCCESS
    row = result.data[0]
    assert row["scheme"] == "https"
    assert row["hostname"] == "example.com"
    assert row["port"] == 8443
    assert row["path"] == "/path"
    assert row["query"] == "a=1&b=hello"
    assert row["fragment"] == "top"
    assert row["query_params"] == "a=1; b=hello"


def test_parse_credentials_and_ipv6() -> None:
    tool = UrlParserTool()
    credentials = tool.run(
        {"url": "http://user:pass@example.com/path"},
        _context(),
    )
    assert credentials.data[0]["username"] == "user"
    assert credentials.data[0]["password_present"] is True
    assert any(f.title == "URL 包含密码字段" for f in credentials.findings)
    ipv6 = tool.run({"url": "https://[2001:db8::1]/test"}, _context())
    assert ipv6.data[0]["hostname"] == "2001:db8::1"


def test_bare_host_assumes_https() -> None:
    result = UrlParserTool().run({"url": "example.com"}, _context())
    assert result.data[0]["scheme"] == "https"
    assert any(f.title == "已按 HTTPS 解释" for f in result.findings)


def test_http_scheme_warns() -> None:
    result = UrlParserTool().run({"url": "http://example.com"}, _context())
    assert any(f.title == "URL 使用明文 HTTP" for f in result.findings)


@pytest.mark.parametrize(
    "url",
    ["javascript:alert(1)", "file:///test", "data:text/plain,test", "ftp://example.com"],
)
def test_invalid_schemes_rejected(url: str) -> None:
    result = UrlParserTool().run({"url": url}, _context())
    assert result.status is ResultStatus.FAILED
    assert "只支持HTTP/HTTPS" in result.summary


def test_malformed_colons_rejected() -> None:
    result = UrlParserTool().run({"url": "::::"}, _context())
    assert result.status is ResultStatus.FAILED


def test_empty_url_rejected() -> None:
    result = UrlParserTool().run({"url": "  "}, _context())
    assert result.status is ResultStatus.FAILED
    assert result.summary == "请输入要分析的 URL。"

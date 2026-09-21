"""HTTP analysis composite tool and page metadata extraction."""

from __future__ import annotations

import logging
import threading

from core.result import ResultStatus
from core.task import ExecutionContext
from modules.web.http_analysis import HttpAnalysisTool, parse_page_metadata


def _context() -> ExecutionContext:
    return ExecutionContext(
        task_id="t-http",
        tool_id="web.http_analysis",
        logger=logging.getLogger("tests.http"),
        cancel_event=threading.Event(),
    )


def test_metadata_parser() -> None:
    html = (
        '<html lang="en"><head><title>Example</title>'
        '<meta name="description" content="A description">'
        '<meta name="robots" content="noindex,nofollow">'
        '<meta property="og:title" content="OG Title">'
        '<link rel="canonical" href="https://example.com/canonical">'
        "</head><body></body></html>"
    )
    metadata = parse_page_metadata(html)
    assert metadata.title == "Example"
    assert metadata.description == "A description"
    assert metadata.robots == "noindex,nofollow"
    assert metadata.canonical == "https://example.com/canonical"
    assert metadata.language == "en"
    assert metadata.open_graph == {"og:title": "OG Title"}


def test_metadata_missing_fields() -> None:
    metadata = parse_page_metadata("<html><body>x</body></html>")
    assert metadata.title is None
    assert metadata.description is None


def test_composite_analysis(web_server: str) -> None:
    result = HttpAnalysisTool().run({"url": f"{web_server}/headers"}, _context())
    assert result.status is ResultStatus.SUCCESS
    rows = {(row["section"], row["item"]): row["value"] for row in result.data}
    assert rows[("请求", "Method")] == "GET"
    assert rows[("响应", "Status")] == "200"
    assert ("安全Header", "已配置") in rows
    assert any(section == "Cookie" for section, _item in rows)
    assert any(finding.title.startswith("缺少") for finding in result.findings)


def test_composite_analysis_metadata_and_redirect(web_server: str) -> None:
    result = HttpAnalysisTool().run({"url": f"{web_server}/chain"}, _context())
    assert result.status is ResultStatus.SUCCESS
    assert any(finding.title == "发生重定向" for finding in result.findings)
    result_html = HttpAnalysisTool().run({"url": f"{web_server}/html"}, _context())
    rows = {(row["section"], row["item"]): row["value"] for row in result_html.data}
    assert rows[("页面", "Title")] == "测试页面"
    assert rows[("OpenGraph", "og:title")] == "OG 标题"


def test_redacted_sensitive_headers_in_rows(web_server: str) -> None:
    result = HttpAnalysisTool().run({"url": f"{web_server}/ok"}, _context())
    values = {row["item"]: row["value"] for row in result.data if row["section"] == "Header"}
    assert all("secret" not in value for value in values.values())
